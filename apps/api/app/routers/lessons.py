from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.security import get_current_user_or_internal, require_same_user_or_internal
from app.models.schema import User
from app.schemas import ExerciseSubmitRequest, ExerciseSubmitResponse, LessonDTO, LessonStartRequest, ProgressDTO
from app.services.lesson_service import get_continue_lesson, get_lesson, progress_summary, start_lesson, submit_exercise

router = APIRouter(prefix="/api", tags=["lessons"])


@router.get("/lessons/continue/{telegram_id}", response_model=LessonDTO | None)
def continue_lesson(
    telegram_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_settings),
    x_internal_token: str | None = Header(default=None),
):
    require_same_user_or_internal(user, telegram_id, x_internal_token, settings)
    return get_continue_lesson(db, user)


@router.get("/lessons/{lesson_id}", response_model=LessonDTO)
def lesson_detail(
    lesson_id: int,
    telegram_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_settings),
    x_internal_token: str | None = Header(default=None),
):
    require_same_user_or_internal(user, telegram_id, x_internal_token, settings)
    return get_lesson(db, user, lesson_id)


@router.post("/lessons/{lesson_id}/start", response_model=LessonDTO)
def start(
    lesson_id: int,
    payload: LessonStartRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_settings),
    x_internal_token: str | None = Header(default=None),
):
    require_same_user_or_internal(user, payload.telegram_id, x_internal_token, settings)
    return start_lesson(db, user, lesson_id)


@router.post("/exercises/{exercise_id}/submit", response_model=ExerciseSubmitResponse)
def submit(
    exercise_id: int,
    payload: ExerciseSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_settings),
    x_internal_token: str | None = Header(default=None),
):
    require_same_user_or_internal(user, payload.telegram_id, x_internal_token, settings)
    return submit_exercise(db, user, exercise_id, payload.answer, payload.lesson_id)


@router.get("/progress/{telegram_id}", response_model=ProgressDTO)
def progress(
    telegram_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_settings),
    x_internal_token: str | None = Header(default=None),
):
    require_same_user_or_internal(user, telegram_id, x_internal_token, settings)
    return progress_summary(db, user)
