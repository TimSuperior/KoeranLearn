from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.schema import (
    Reminder,
    User,
    UserGoal,
    UserPathProgress,
    UserPreference,
    UserProfile,
)
from app.schemas import OnboardingCompleteRequest, OnboardingStartRequest
from app.services.analytics import track_event
from app.services.curriculum_service import first_guided_lesson, get_guided_path


def normalize_language(language_code: str | None) -> str:
    if not language_code:
        return "en"
    code = language_code.lower()
    if code.startswith("ru"):
        return "ru"
    if code.startswith("uz"):
        return "uz"
    return "en"


def get_user_by_telegram_id(db: Session, telegram_id: str) -> User:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def get_or_create_user(
    db: Session,
    telegram_id: str,
    username: str | None = None,
    first_name: str | None = None,
    telegram_language_code: str | None = None,
) -> User:
    user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
    if user:
        user.username = username or user.username
        user.first_name = first_name or user.first_name
        user.telegram_language_code = telegram_language_code or user.telegram_language_code
        db.commit()
        db.refresh(user)
        return user

    language = normalize_language(telegram_language_code)
    user = User(
        telegram_id=str(telegram_id),
        username=username,
        first_name=first_name,
        telegram_language_code=telegram_language_code,
        interface_language=language,
    )
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.id))
    db.add(UserPreference(user_id=user.id, explanation_language=language))
    db.commit()
    db.refresh(user)
    return user


def start_onboarding(db: Session, payload: OnboardingStartRequest) -> User:
    user = get_or_create_user(
        db,
        payload.telegram_id,
        payload.username,
        payload.first_name,
        payload.telegram_language_code,
    )
    track_event(db, "onboarding_started", user.telegram_id, user.interface_language, {"deep_link": payload.deep_link})
    return user


def complete_onboarding(db: Session, payload: OnboardingCompleteRequest) -> User:
    user = get_or_create_user(
        db,
        payload.telegram_id,
        payload.username,
        payload.first_name,
        payload.telegram_language_code,
    )
    user.interface_language = payload.interface_language
    user.is_onboarded = True

    if not user.profile:
        user.profile = UserProfile(user_id=user.id)
    user.profile.level = payload.level
    user.profile.daily_minutes = payload.daily_minutes
    user.profile.learning_style = payload.learning_style
    user.profile.timezone = payload.timezone

    if not user.preferences:
        user.preferences = UserPreference(user_id=user.id)
    user.preferences.explanation_language = payload.interface_language
    user.preferences.reminder_time = payload.reminder_time

    db.query(UserGoal).filter(UserGoal.user_id == user.id).delete()
    db.add(UserGoal(user_id=user.id, goal=payload.goal))

    path = get_guided_path(db)
    first_lesson = first_guided_lesson(db)
    if path:
        progress = db.query(UserPathProgress).filter(UserPathProgress.user_id == user.id, UserPathProgress.path_id == path.id).first()
        if not progress:
            progress = UserPathProgress(user_id=user.id, path_id=path.id)
            db.add(progress)
        progress.current_lesson_id = first_lesson.id if first_lesson else None
        progress.current_module_id = first_lesson.module_id if first_lesson else None

    reminder = db.query(Reminder).filter(Reminder.user_id == user.id, Reminder.reminder_type == "daily").first()
    if not reminder:
        reminder = Reminder(user_id=user.id, reminder_type="daily")
        db.add(reminder)
    reminder.enabled = True
    reminder.preferred_time = payload.reminder_time
    reminder.timezone = payload.timezone

    db.commit()
    db.refresh(user)
    track_event(
        db,
        "onboarding_completed",
        user.telegram_id,
        user.interface_language,
        {"goal": "guided_curriculum", "level": payload.level, "daily_minutes": payload.daily_minutes, "path_id": path.id if path else None},
    )
    if path:
        track_event(db, "path_selected", user.telegram_id, user.interface_language, {"path_id": path.id, "path_slug": path.slug, "mode": "guided"})
    return user


def update_study_activity(user: User) -> None:
    now = datetime.now(timezone.utc)
    user.last_study_at = now
    user.streak_count = max(user.streak_count, 1)
