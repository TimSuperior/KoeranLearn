from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.security import get_current_user_or_internal, require_same_user_or_internal
from app.models.schema import Reminder, User
from app.schemas import ReminderSettingsDTO

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.get("/{telegram_id}", response_model=ReminderSettingsDTO)
def get_reminders(
    telegram_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_settings),
    x_internal_token: str | None = Header(default=None),
):
    require_same_user_or_internal(user, telegram_id, x_internal_token, settings)
    reminder = db.query(Reminder).filter(Reminder.user_id == user.id, Reminder.reminder_type == "daily").first()
    if not reminder:
        return ReminderSettingsDTO()
    return ReminderSettingsDTO(
        enabled=reminder.enabled,
        reminder_time=reminder.preferred_time,
        timezone=reminder.timezone,
        quiet_hours=reminder.quiet_hours,
    )


@router.put("/{telegram_id}", response_model=ReminderSettingsDTO)
def update_reminders(
    telegram_id: str,
    payload: ReminderSettingsDTO,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_settings),
    x_internal_token: str | None = Header(default=None),
):
    require_same_user_or_internal(user, telegram_id, x_internal_token, settings)
    reminder = db.query(Reminder).filter(Reminder.user_id == user.id, Reminder.reminder_type == "daily").first()
    if not reminder:
        reminder = Reminder(user_id=user.id, reminder_type="daily")
        db.add(reminder)
    reminder.enabled = payload.enabled
    reminder.preferred_time = payload.reminder_time
    reminder.timezone = payload.timezone
    reminder.quiet_hours = payload.quiet_hours
    reminder.next_send_at = datetime.now(timezone.utc) + timedelta(hours=24)
    db.commit()
    return payload
