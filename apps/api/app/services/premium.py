from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.schema import PremiumPack, Subscription, User


def has_active_subscription(db: Session, user: User) -> bool:
    if user.is_premium:
        return True
    subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.status == "active")
        .filter((Subscription.expires_at.is_(None)) | (Subscription.expires_at > datetime.now(timezone.utc)))
        .first()
    )
    return subscription is not None


def require_content_access(db: Session, user: User, is_premium: bool) -> None:
    if not is_premium:
        return
    if has_active_subscription(db, user):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Premium access required.")


def premium_catalog(db: Session) -> list[PremiumPack]:
    return (
        db.query(PremiumPack)
        .filter(PremiumPack.is_deleted.is_(False), PremiumPack.status == "published", PremiumPack.is_active.is_(True))
        .order_by(PremiumPack.order_index, PremiumPack.id)
        .all()
    )
