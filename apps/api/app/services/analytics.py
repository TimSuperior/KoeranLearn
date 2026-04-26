from sqlalchemy.orm import Session

from app.models.schema import AnalyticsEvent, User


def track_event(
    db: Session,
    event_name: str,
    telegram_id: str | None = None,
    audience_language: str | None = None,
    properties: dict | None = None,
) -> AnalyticsEvent:
    user_id = None
    if telegram_id:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        user_id = user.id if user else None
        audience_language = audience_language or (user.interface_language if user else None)

    event = AnalyticsEvent(
        event_name=event_name,
        user_id=user_id,
        telegram_id=telegram_id,
        audience_language=audience_language,
        properties=properties or {},
    )
    db.add(event)
    db.commit()
    return event
