import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.security import get_current_user
from app.schemas import OnboardingCompleteRequest, OnboardingStartRequest, UserSummary
from app.services.curriculum_service import guided_path_progress
from app.services.user_service import complete_onboarding, get_user_by_telegram_id, start_onboarding

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.post("/start", response_model=UserSummary)
def start(
    payload: OnboardingStartRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
) -> UserSummary:
    _authorize_payload_user(payload.telegram_id, authorization, x_internal_token, db, settings)
    user = start_onboarding(db, payload)
    return _summary(db, user.telegram_id)


@router.post("/complete", response_model=UserSummary)
def complete(
    payload: OnboardingCompleteRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
) -> UserSummary:
    _authorize_payload_user(payload.telegram_id, authorization, x_internal_token, db, settings)
    user = complete_onboarding(db, payload)
    return _summary(db, user.telegram_id)


@router.get("/me/{telegram_id}", response_model=UserSummary)
def me(
    telegram_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
) -> UserSummary:
    _authorize_payload_user(telegram_id, authorization, x_internal_token, db, settings)
    return _summary(db, telegram_id)


def _authorize_payload_user(
    telegram_id: str,
    authorization: str | None,
    x_internal_token: str | None,
    db: Session,
    settings: Settings,
) -> None:
    if x_internal_token and hmac.compare_digest(x_internal_token, settings.internal_service_token):
        return
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_current_user(authorization, db, settings)
    if user.telegram_id != str(telegram_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update another user")


def _summary(db: Session, telegram_id: str) -> UserSummary:
    user = get_user_by_telegram_id(db, telegram_id)
    _, progress = guided_path_progress(db, user, create=True)
    return UserSummary(
        telegram_id=user.telegram_id,
        interface_language=user.interface_language,
        explanation_language=(user.preferences.explanation_language if user.preferences else user.interface_language),
        is_onboarded=user.is_onboarded,
        is_premium=user.is_premium,
        xp=user.xp,
        streak_count=user.streak_count,
        current_lesson_id=progress.current_lesson_id if progress else None,
        current_path_id=progress.path_id if progress else None,
    )
