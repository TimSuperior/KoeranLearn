from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.schema import Exercise, Lesson, LessonBlock, LessonProgress, ReviewItem, Scenario, User, Vocabulary, utcnow
from app.services.learner_serializers import serialize_lesson, serialize_lesson_reference
from app.services.analytics import track_event
from app.services.curriculum_service import (
    current_module_for_lesson,
    first_guided_lesson,
    guided_path_progress,
    lesson_belongs_to_guided_path,
    next_guided_lesson,
    next_lesson_after,
    sync_guided_progress,
)
from app.services.audio_service import listening_exercise
from app.services.exercise_evaluator import evaluate_exercise_submission
from app.services.premium import require_content_access
from app.services.review_service import build_review_overview, get_or_create_review_item
from app.services.user_service import update_study_activity


def _lesson_loader_options():
    return (
        selectinload(Lesson.blocks).selectinload(LessonBlock.audio_assets),
        selectinload(Lesson.assets),
        selectinload(Lesson.audio_assets),
        selectinload(Lesson.exercises).selectinload(Exercise.options),
        selectinload(Lesson.exercises).selectinload(Exercise.audio_assets),
        selectinload(Lesson.related_vocabulary).selectinload(Vocabulary.audio_assets),
        selectinload(Lesson.related_grammar),
        selectinload(Lesson.related_scenarios).selectinload(Scenario.audio_assets),
    )


def get_continue_lesson(db: Session, user: User) -> dict | None:
    _, progress, lessons, _ = sync_guided_progress(db, user, create=True)
    lesson = next((row for row in lessons if progress and row.id == progress.current_lesson_id), None)
    if not lesson:
        lesson = next_guided_lesson(db, user, create_progress=True) or first_guided_lesson(db)
    if not lesson:
        return None
    full_lesson = (
        db.query(Lesson)
        .options(*_lesson_loader_options())
        .filter(Lesson.id == lesson.id, Lesson.is_deleted.is_(False), Lesson.status == "published")
        .filter(Lesson.resolved_access_state.notin_(["hidden", "internal"]))
        .first()
    )
    if not full_lesson:
        return None
    return serialize_lesson(db, user, get_settings(), full_lesson)


def get_lesson(db: Session, user: User, lesson_id: int) -> dict[str, object]:
    lesson = (
        db.query(Lesson)
        .options(*_lesson_loader_options())
        .filter(Lesson.id == lesson_id, Lesson.is_deleted.is_(False), Lesson.status == "published")
        .filter(Lesson.resolved_access_state.notin_(["hidden", "internal"]))
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    require_content_access(db, user, lesson.is_premium)
    return serialize_lesson(db, user, get_settings(), lesson)


def start_lesson(db: Session, user: User, lesson_id: int) -> dict[str, object]:
    lesson_row = (
        db.query(Lesson)
        .options(*_lesson_loader_options())
        .filter(Lesson.id == lesson_id, Lesson.is_deleted.is_(False), Lesson.status == "published")
        .filter(Lesson.resolved_access_state.notin_(["hidden", "internal"]))
        .first()
    )
    if not lesson_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    require_content_access(db, user, lesson_row.is_premium)
    progress = db.query(LessonProgress).filter(LessonProgress.user_id == user.id, LessonProgress.lesson_id == lesson_row.id).first()
    if not progress:
        progress = LessonProgress(user_id=user.id, lesson_id=lesson_row.id)
        db.add(progress)
    progress.status = "in_progress"
    progress.started_at = progress.started_at or utcnow()
    if lesson_belongs_to_guided_path(db, lesson_row.id):
        _, path_progress = guided_path_progress(db, user, create=True)
        if path_progress:
            path_progress.current_lesson_id = lesson_row.id
            path_progress.current_module_id = lesson_row.module_id
    update_study_activity(user)
    db.commit()
    track_event(db, "lesson_started", user.telegram_id, user.interface_language, {"lesson_id": lesson_row.id, "lesson_slug": lesson_row.slug})
    return serialize_lesson(db, user, get_settings(), lesson_row)


def submit_exercise(db: Session, user: User, exercise_id: int, answer: Any, lesson_id: int | None = None) -> dict[str, Any]:
    exercise = db.get(Exercise, exercise_id)
    if not exercise or exercise.is_deleted or exercise.status != "published" or exercise.resolved_access_state in {"hidden", "internal"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    require_content_access(db, user, exercise.is_premium or listening_exercise(exercise))

    evaluation = evaluate_exercise_submission(exercise, answer)
    is_correct = evaluation.is_correct
    lesson_completed = False
    xp_awarded = 2 if is_correct else 0

    if is_correct:
        get_or_create_review_item(db, user, "exercise", exercise.id, exercise.lesson_id)
    else:
        get_or_create_review_item(db, user, "exercise", exercise.id, exercise.lesson_id, wrong=True)
    if exercise.vocabulary_id:
        get_or_create_review_item(db, user, "vocabulary", exercise.vocabulary_id, exercise.lesson_id, wrong=not is_correct)
    if exercise.grammar_point_id:
        get_or_create_review_item(db, user, "grammar", exercise.grammar_point_id, exercise.lesson_id, wrong=not is_correct)

    if is_correct and lesson_id:
        last_exercise = (
            db.query(Exercise)
            .filter(Exercise.lesson_id == lesson_id)
            .order_by(Exercise.order_index.desc())
            .first()
        )
        if last_exercise and last_exercise.id == exercise.id:
            lesson_completed = _complete_lesson(db, user, lesson_id)
            xp_awarded += 10

    user.xp += xp_awarded
    update_study_activity(user)
    db.commit()
    track_event(
        db,
        "exercise_completed",
        user.telegram_id,
        user.interface_language,
        {
            "exercise_id": exercise.id,
            "exercise_type": exercise.exercise_type,
            "lesson_id": exercise.lesson_id,
            "is_correct": is_correct,
            "validator": evaluation.validator,
        },
    )
    return {
        "is_correct": is_correct,
        "expected": exercise.answer_key.get("value"),
        "explanation": exercise.explanation,
        "validator": evaluation.validator,
        "lesson_completed": lesson_completed,
        "xp_awarded": xp_awarded,
    }


def _complete_lesson(db: Session, user: User, lesson_id: int) -> bool:
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        return False

    progress = db.query(LessonProgress).filter(LessonProgress.user_id == user.id, LessonProgress.lesson_id == lesson.id).first()
    if not progress:
        progress = LessonProgress(user_id=user.id, lesson_id=lesson.id)
        db.add(progress)
    progress.status = "completed"
    progress.score = 1.0
    progress.completed_at = utcnow()

    get_or_create_review_item(db, user, "lesson", lesson.id, lesson.id)

    next_lesson = next_lesson_after(db, user, lesson.id)
    _, path_progress, lessons, completed_ids = sync_guided_progress(db, user, create=True)
    if path_progress and lesson_belongs_to_guided_path(db, lesson.id):
        completed_total = len(completed_ids | {lesson.id})
        total_lessons = len(lessons)
        path_progress.completed_lessons = completed_total
        path_progress.percent_complete = round((completed_total / max(total_lessons, 1)) * 100, 2) if total_lessons else 0.0
        path_progress.current_lesson_id = next_lesson.id if next_lesson else None
        path_progress.current_module_id = next_lesson.module_id if next_lesson else None

    track_event(db, "lesson_completed", user.telegram_id, user.interface_language, {"lesson_id": lesson.id, "lesson_slug": lesson.slug})
    return True


def progress_summary(db: Session, user: User) -> dict[str, Any]:
    path, path_progress, lessons, _ = sync_guided_progress(db, user, create=True)
    current_lesson = db.get(Lesson, path_progress.current_lesson_id) if path_progress and path_progress.current_lesson_id else None
    current_module = current_module_for_lesson(current_lesson)
    due_reviews = db.query(ReviewItem).filter(ReviewItem.user_id == user.id, ReviewItem.next_review_at <= utcnow()).count()
    mistake_reviews = db.query(ReviewItem).filter(ReviewItem.user_id == user.id, ReviewItem.mistake_count > 0).count()
    completed_lessons = path_progress.completed_lessons if path_progress else 0
    difficult_topics = (
        db.query(Exercise.topic)
        .join(ReviewItem, ReviewItem.item_id == Exercise.id)
        .filter(ReviewItem.user_id == user.id, ReviewItem.item_type == "exercise", ReviewItem.mistake_count > 0)
        .limit(5)
        .all()
    )
    review_overview = build_review_overview(db, user)
    last_completed_progress = (
        db.query(LessonProgress)
        .filter(LessonProgress.user_id == user.id, LessonProgress.status == "completed", LessonProgress.completed_at.is_not(None))
        .filter(LessonProgress.lesson_id.in_([lesson.id for lesson in lessons]) if lessons else False)
        .order_by(LessonProgress.completed_at.desc())
        .first()
    )
    last_completed_lesson = db.get(Lesson, last_completed_progress.lesson_id) if last_completed_progress else None
    return {
        "telegram_id": user.telegram_id,
        "xp": user.xp,
        "streak_count": user.streak_count,
        "completed_lessons": completed_lessons,
        "due_reviews": due_reviews,
        "mistake_reviews": mistake_reviews,
        "current_path": {
            "id": path.id,
            "slug": path.slug,
            "title": path.title,
            "percent_complete": path_progress.percent_complete if path_progress else 0.0,
            "completed_lessons": path_progress.completed_lessons if path_progress else 0,
            "total_lessons": len(lessons),
        }
        if path
        else None,
        "current_module": {"id": current_module.id, "title": current_module.title, "slug": current_module.slug} if current_module else None,
        "current_lesson": serialize_lesson_reference(db, user, get_settings(), current_lesson) if current_lesson else None,
        "last_completed_lesson": {"id": last_completed_lesson.id, "title": last_completed_lesson.title, "slug": last_completed_lesson.slug} if last_completed_lesson else None,
        "difficult_topics": [{"topic": row[0]} for row in difficult_topics],
        "review_overview": review_overview,
    }
