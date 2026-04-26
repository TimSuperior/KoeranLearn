from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings as get_app_settings
from app.core.db import get_db
from app.core.security import get_current_user, get_current_user_or_internal, require_same_user_or_internal
from app.models.schema import Reminder, User, UserPreference, UserProfile
from app.schemas import UserSettingsDTO, UserSettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _build_settings_dto(user: User, db: Session) -> UserSettingsDTO:
    profile = user.profile or UserProfile(user_id=user.id)
    preferences = user.preferences or UserPreference(user_id=user.id)
    reminder = db.query(Reminder).filter(Reminder.user_id == user.id, Reminder.reminder_type == "daily").first()
    return UserSettingsDTO(
        interface_language=user.interface_language,
        explanation_language=preferences.explanation_language,
        reminders_enabled=reminder.enabled if reminder else preferences.reminders_enabled,
        reminder_time=reminder.preferred_time if reminder else preferences.reminder_time,
        timezone=profile.timezone,
        learning_style=profile.learning_style,
        difficulty=preferences.difficulty,
    )


def _apply_settings_update(payload: UserSettingsUpdate, user: User, db: Session) -> UserSettingsDTO:
    if not user.profile:
        user.profile = UserProfile(user_id=user.id)
    if not user.preferences:
        user.preferences = UserPreference(user_id=user.id)

    if payload.interface_language:
        user.interface_language = payload.interface_language
    if payload.explanation_language:
        user.preferences.explanation_language = payload.explanation_language
    if payload.learning_style:
        user.profile.learning_style = payload.learning_style
    if payload.difficulty:
        user.preferences.difficulty = payload.difficulty
    if payload.timezone:
        user.profile.timezone = payload.timezone
    if payload.reminder_time:
        user.preferences.reminder_time = payload.reminder_time
    if payload.reminders_enabled is not None:
        user.preferences.reminders_enabled = payload.reminders_enabled

    reminder = db.query(Reminder).filter(Reminder.user_id == user.id, Reminder.reminder_type == "daily").first()
    if not reminder:
        reminder = Reminder(user_id=user.id, reminder_type="daily")
        db.add(reminder)
    if payload.reminders_enabled is not None:
        reminder.enabled = payload.reminders_enabled
    if payload.reminder_time:
        reminder.preferred_time = payload.reminder_time
    if payload.timezone:
        reminder.timezone = payload.timezone

    db.commit()
    db.refresh(user)
    return _build_settings_dto(user, db)


@router.get("", response_model=UserSettingsDTO)
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserSettingsDTO:
    return _build_settings_dto(user, db)


@router.put("", response_model=UserSettingsDTO)
def update_settings(payload: UserSettingsUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserSettingsDTO:
    return _apply_settings_update(payload, user, db)


@router.get("/{telegram_id}", response_model=UserSettingsDTO)
def get_settings_for_telegram(
    telegram_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_app_settings),
    x_internal_token: str | None = Header(default=None),
) -> UserSettingsDTO:
    require_same_user_or_internal(user, telegram_id, x_internal_token, settings)
    return _build_settings_dto(user, db)


@router.put("/{telegram_id}", response_model=UserSettingsDTO)
def update_settings_for_telegram(
    telegram_id: str,
    payload: UserSettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_app_settings),
    x_internal_token: str | None = Header(default=None),
) -> UserSettingsDTO:
    require_same_user_or_internal(user, telegram_id, x_internal_token, settings)
    return _apply_settings_update(payload, user, db)
