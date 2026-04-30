from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.security import get_current_user_or_internal
from app.models.schema import Exercise, ReviewItem, User, utcnow
from app.schemas import QuizSessionDTO, QuizStartRequest
from app.services.audio_service import exercise_has_audio_prompt, listening_exercise
from app.services.curriculum_service import get_guided_path, next_guided_lesson, sync_guided_progress
from app.services.exercise_evaluator import GRAMMAR_EXERCISE_TYPES, LISTENING_REVIEW_EXERCISE_TYPES, canonical_exercise_type
from app.services.premium import has_active_subscription

router = APIRouter(prefix="/api", tags=["learning"])


@router.get("/plan/current")
def current_plan(db: Session = Depends(get_db), user: User = Depends(get_current_user_or_internal)):
    path, progress, lessons, _ = sync_guided_progress(db, user, create=True)
    lesson = next_guided_lesson(db, user, create_progress=True)
    module = lesson.module if lesson else None
    completed = progress.completed_lessons if progress else 0
    total = len(lessons)
    return {
        "path": {"id": path.id, "slug": path.slug, "title": path.title, "level": path.level} if path else None,
        "module": {"id": module.id, "slug": module.slug, "title": module.title} if module else None,
        "next_lesson": {"id": lesson.id, "slug": lesson.slug, "title": lesson.title} if lesson else None,
        "completed_lessons": completed,
        "total_lessons": total,
        "percent_complete": progress.percent_complete if progress else 0,
    }


@router.post("/paths/{path_id}/switch")
def switch_path(path_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user_or_internal)):
    path = get_guided_path(db)
    if not path or path.id != path_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guided curriculum path not found")
    _, progress, _, _ = sync_guided_progress(db, user, create=True)
    db.commit()
    return {"ok": True, "path_id": path.id, "current_lesson_id": progress.current_lesson_id if progress else None}


@router.get("/streak")
def streak_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user_or_internal)):
    due_reviews = db.query(ReviewItem).filter(ReviewItem.user_id == user.id, ReviewItem.next_review_at <= utcnow()).count()
    milestone = next((value for value in [3, 7, 14, 30, 60, 100] if value > user.streak_count), user.streak_count + 50)
    last = user.last_study_at
    weekly_activity = [
        {
            "day_offset": index,
            "active": bool(last and last >= utcnow() - timedelta(days=index + 1)),
        }
        for index in range(6, -1, -1)
    ]
    return {
        "streak_count": user.streak_count,
        "xp": user.xp,
        "due_reviews": due_reviews,
        "next_milestone": milestone,
        "weekly_activity": weekly_activity,
    }


@router.post("/quiz/start", response_model=QuizSessionDTO)
def start_quiz(payload: QuizStartRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user_or_internal)):
    query = db.query(Exercise).options(selectinload(Exercise.options)).filter(Exercise.is_deleted.is_(False), Exercise.status == "published")
    is_premium_user = has_active_subscription(db, user)
    if not is_premium_user:
        query = query.filter(Exercise.is_premium.is_(False))
    if payload.topic:
        query = query.filter(Exercise.topic == payload.topic)
    prioritized_ids: list[int] = []
    if payload.mistakes_only:
        mistake_rows = (
            db.query(ReviewItem)
            .filter(ReviewItem.user_id == user.id, ReviewItem.item_type == "exercise", ReviewItem.mistake_count > 0)
            .order_by(ReviewItem.mistake_count.desc(), ReviewItem.next_review_at.asc())
            .limit(100)
            .all()
        )
        prioritized_ids = [row.item_id for row in mistake_rows]
        if not prioritized_ids:
            return {"exercises": [], "source": "mistakes"}
        query = query.filter(Exercise.id.in_(prioritized_ids))
    elif payload.due_only:
        due_rows = (
            db.query(ReviewItem)
            .filter(ReviewItem.user_id == user.id, ReviewItem.item_type == "exercise", ReviewItem.next_review_at <= utcnow())
            .order_by(ReviewItem.next_review_at.asc(), ReviewItem.mistake_count.desc())
            .limit(100)
            .all()
        )
        prioritized_ids = [row.item_id for row in due_rows]
        if not prioritized_ids:
            return {"exercises": [], "source": "due"}
        query = query.filter(Exercise.id.in_(prioritized_ids))
    exercises = []
    for row in query.order_by(Exercise.topic, Exercise.order_index).all():
        if not is_premium_user and listening_exercise(row):
            continue
        canonical_type = canonical_exercise_type(row.exercise_type)
        if payload.focus == "grammar" and canonical_type not in GRAMMAR_EXERCISE_TYPES:
            continue
        if payload.focus == "listening" and canonical_type not in LISTENING_REVIEW_EXERCISE_TYPES:
            continue
        if payload.require_audio and not exercise_has_audio_prompt(row):
            continue
        if payload.focus == "listening" and not exercise_has_audio_prompt(row):
            continue
        exercises.append(row)

    if prioritized_ids:
        priority_index = {exercise_id: index for index, exercise_id in enumerate(prioritized_ids)}
        exercises.sort(key=lambda row: (priority_index.get(row.id, len(priority_index)), row.order_index))

    exercises = exercises[: payload.limit]
    if payload.mistakes_only:
        source = "mistakes"
    elif payload.due_only:
        source = "due"
    elif payload.focus == "grammar":
        source = "grammar"
    elif payload.focus == "listening":
        source = "listening"
    else:
        source = "mixed"
    return {"exercises": exercises, "source": source}
