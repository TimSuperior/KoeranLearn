import logging
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import inspect

from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.core.logging import configure_logging
from app.models.schema import AnalyticsEvent, Reminder, User

configure_logging(get_settings().log_level)
logger = logging.getLogger("reminder-worker")


def run_once() -> int:
    settings = get_settings()
    db = SessionLocal()
    sent = 0
    try:
        now = datetime.now(timezone.utc)
        due = (
            db.query(Reminder)
            .filter(Reminder.enabled.is_(True))
            .filter((Reminder.next_send_at.is_(None)) | (Reminder.next_send_at <= now))
            .limit(50)
            .all()
        )
        for reminder in due:
            user = db.get(User, reminder.user_id)
            if not user:
                continue
            message = _message(user.interface_language)
            if settings.telegram_bot_token:
                url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
                try:
                    httpx.post(url, json={"chat_id": user.telegram_id, "text": message}, timeout=10)
                    sent += 1
                except Exception as exc:
                    logger.warning(
                        "failed to send reminder",
                        extra={"user_id": user.id, "event": "reminder_failed"},
                        exc_info=(type(exc), exc, exc.__traceback__),
                    )
            reminder.last_sent_at = now
            reminder.next_send_at = now + timedelta(days=1)
            db.add(
                AnalyticsEvent(
                    event_name="reminder_sent",
                    user_id=user.id,
                    telegram_id=user.telegram_id,
                    audience_language=user.interface_language,
                    properties={"reminder_type": reminder.reminder_type},
                )
            )
        db.commit()
        return sent
    finally:
        db.close()


def _message(language: str) -> str:
    messages = {
        "ru": "Сегодняшний корейский: 5 минут урока или повторения?",
        "uz": "Bugungi koreys tili: 5 daqiqa dars yoki takrorlash?",
        "en": "Today's Korean: 5 minutes for a lesson or review?",
    }
    return messages.get(language, messages["en"])


def main() -> None:
    wait_for_schema()
    logger.info("Reminder worker started")
    while True:
        sent = run_once()
        if sent:
            logger.info("Sent %s reminders", sent)
        time.sleep(60)


def wait_for_schema(timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            inspector = inspect(engine)
            if inspector.has_table("reminders") and inspector.has_table("users"):
                return
        except Exception as exc:
            logger.info("Waiting for database schema: %s", exc)
        time.sleep(2)
    raise RuntimeError("Database schema was not created before reminder worker timeout")


if __name__ == "__main__":
    main()
