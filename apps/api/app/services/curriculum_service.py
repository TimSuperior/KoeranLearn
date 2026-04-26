from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.schema import Course, LearningPath, Lesson, LessonProgress, Module, User, UserPathProgress


def get_guided_path(db: Session) -> LearningPath | None:
    preferred = (
        db.query(LearningPath)
        .filter(
            LearningPath.target_goal == "korean_from_zero",
            LearningPath.is_deleted.is_(False),
            LearningPath.status == "published",
            LearningPath.resolved_access_state.notin_(["hidden", "internal"]),
        )
        .order_by(LearningPath.order_index, LearningPath.id)
        .all()
    )
    for path in preferred:
        if _path_has_visible_lessons(db, path.id):
            return path

    fallback = (
        db.query(LearningPath)
        .filter(
            LearningPath.is_deleted.is_(False),
            LearningPath.status == "published",
            LearningPath.resolved_access_state.notin_(["hidden", "internal"]),
        )
        .order_by(LearningPath.order_index, LearningPath.id)
        .all()
    )
    for path in fallback:
        if _path_has_visible_lessons(db, path.id):
            return path
    return None


def ordered_lessons_for_path(db: Session, path_id: int) -> list[Lesson]:
    return (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(
            Course.path_id == path_id,
            Course.is_deleted.is_(False),
            Course.status == "published",
            Module.is_deleted.is_(False),
            Module.status == "published",
            Lesson.is_deleted.is_(False),
            Lesson.status == "published",
            Lesson.resolved_access_state.notin_(["hidden", "internal"]),
        )
        .order_by(Course.order_index, Course.id, Module.order_index, Module.id, Lesson.order_index, Lesson.id)
        .all()
    )


def guided_path_progress(db: Session, user: User, *, create: bool = False) -> tuple[LearningPath | None, UserPathProgress | None]:
    path = get_guided_path(db)
    if not path:
        return None, None

    progress = db.query(UserPathProgress).filter(UserPathProgress.user_id == user.id, UserPathProgress.path_id == path.id).first()
    if not progress and create:
        progress = UserPathProgress(user_id=user.id, path_id=path.id)
        db.add(progress)
        db.flush()

    return path, progress


def sync_guided_progress(db: Session, user: User, *, create: bool = False) -> tuple[LearningPath | None, UserPathProgress | None, list[Lesson], set[int]]:
    path, progress = guided_path_progress(db, user, create=create)
    if not path:
        return None, progress, [], set()

    lessons = ordered_lessons_for_path(db, path.id)
    lesson_ids = [lesson.id for lesson in lessons]
    completed_ids = {
        lesson_id
        for (lesson_id,) in db.query(LessonProgress.lesson_id)
        .filter(LessonProgress.user_id == user.id, LessonProgress.status == "completed")
        .filter(LessonProgress.lesson_id.in_(lesson_ids) if lesson_ids else False)
        .all()
    }

    if progress:
        current = next((lesson for lesson in lessons if lesson.id == progress.current_lesson_id), None)
        if current and current.id in completed_ids:
            current = None
        if current is None:
            current = next((lesson for lesson in lessons if lesson.id not in completed_ids), None)
            progress.current_lesson_id = current.id if current else None
            progress.current_module_id = current.module_id if current else None
        progress.completed_lessons = len(completed_ids)
        progress.percent_complete = round((len(completed_ids) / max(len(lessons), 1)) * 100, 2) if lessons else 0.0

    return path, progress, lessons, completed_ids


def first_guided_lesson(db: Session) -> Lesson | None:
    path = get_guided_path(db)
    if not path:
        return None
    lessons = ordered_lessons_for_path(db, path.id)
    return lessons[0] if lessons else None


def next_guided_lesson(db: Session, user: User, *, create_progress: bool = False) -> Lesson | None:
    _, progress, lessons, completed_ids = sync_guided_progress(db, user, create=create_progress)
    if progress and progress.current_lesson_id:
        current = next((lesson for lesson in lessons if lesson.id == progress.current_lesson_id), None)
        if current and current.id not in completed_ids:
            return current
    return next((lesson for lesson in lessons if lesson.id not in completed_ids), None)


def next_lesson_after(db: Session, user: User, lesson_id: int) -> Lesson | None:
    path = get_guided_path(db)
    if not path:
        return None

    lessons = ordered_lessons_for_path(db, path.id)
    completed_ids = {
        lesson_id
        for (lesson_id,) in db.query(LessonProgress.lesson_id)
        .filter(LessonProgress.user_id == user.id, LessonProgress.status == "completed")
        .filter(LessonProgress.lesson_id.in_([lesson.id for lesson in lessons]) if lessons else False)
        .all()
    }
    lesson_ids = [lesson.id for lesson in lessons]
    try:
        start_index = lesson_ids.index(lesson_id) + 1
    except ValueError:
        start_index = 0

    for lesson in lessons[start_index:]:
        if lesson.id not in completed_ids:
            return lesson
    return None


def lesson_belongs_to_guided_path(db: Session, lesson_id: int) -> bool:
    path = get_guided_path(db)
    if not path:
        return False
    return any(lesson.id == lesson_id for lesson in ordered_lessons_for_path(db, path.id))


def current_module_for_lesson(lesson: Lesson | None) -> Module | None:
    return lesson.module if lesson else None


def total_guided_lessons(db: Session) -> int:
    path = get_guided_path(db)
    if not path:
        return 0
    return len(ordered_lessons_for_path(db, path.id))


def _path_has_visible_lessons(db: Session, path_id: int) -> bool:
    return bool(ordered_lessons_for_path(db, path_id))
