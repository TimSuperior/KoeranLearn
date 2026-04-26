from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.security import get_current_user_or_internal, require_same_user_or_internal
from app.models.schema import Subscription, User
from app.schemas import PremiumAccessDTO
from app.services.premium import has_active_subscription, premium_catalog

router = APIRouter(prefix="/api/premium", tags=["premium"])


@router.get("/catalog")
def catalog(db: Session = Depends(get_db)):
    return [
        {
            "id": pack.id,
            "slug": pack.slug,
            "title": pack.title,
            "description": pack.description,
            "price_minor": pack.price_minor,
            "currency": pack.currency,
            "content_rules": pack.content_rules,
        }
        for pack in premium_catalog(db)
    ]


@router.get("/access/{telegram_id}", response_model=PremiumAccessDTO)
def access(
    telegram_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_settings),
    x_internal_token: str | None = Header(default=None),
):
    require_same_user_or_internal(user, telegram_id, x_internal_token, settings)
    active = has_active_subscription(db, user)
    subscription = db.query(Subscription).filter(Subscription.user_id == user.id, Subscription.status == "active").first()
    return PremiumAccessDTO(
        telegram_id=user.telegram_id,
        is_premium=active,
        active_subscription={"provider": subscription.provider, "expires_at": subscription.expires_at} if subscription else None,
        limits={
            "writing_daily": settings.premium_writing_daily_limit if active else settings.writing_daily_free_limit,
            "daily_lessons": 999 if active else 3,
            "daily_reviews": 999 if active else 20,
        },
    )
