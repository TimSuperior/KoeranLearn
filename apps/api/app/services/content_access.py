from typing import Any

from sqlalchemy.orm import Session

from app.models.schema import Course, Dialogue, Exercise, ExampleSentence, GrammarPoint, LearningPath, Lesson, Module, Scenario, Vocabulary


HIDDEN_ACCESS_STATES = {"hidden", "internal"}
PREMIUM_ACCESS_STATE = "premium"


def parent_content(row: Any) -> Any | None:
    if isinstance(row, Course):
        return row.path
    if isinstance(row, Module):
        return row.course
    if isinstance(row, Lesson):
        return row.module
    if isinstance(row, Exercise):
        return row.lesson
    if isinstance(row, Dialogue):
        return row.scenario
    return None


def resolve_access_state(row: Any) -> str:
    access_state = getattr(row, "access_state", "free") or "free"
    if access_state != "inherit":
        return access_state
    parent = parent_content(row)
    if parent is None:
        return "free"
    return resolve_access_state(parent)


def sync_access_state(row: Any) -> str:
    resolved = resolve_access_state(row)
    if hasattr(row, "resolved_access_state"):
        row.resolved_access_state = resolved
    if hasattr(row, "is_premium"):
        row.is_premium = resolved == PREMIUM_ACCESS_STATE
    return resolved


def propagate_access_state(row: Any) -> None:
    sync_access_state(row)
    children: list[Any] = []
    if isinstance(row, LearningPath):
        children = list(row.courses)
    elif isinstance(row, Course):
        children = list(row.modules)
    elif isinstance(row, Module):
        children = list(row.lessons)
    elif isinstance(row, Lesson):
        children = list(row.exercises)
    elif isinstance(row, Scenario):
        children = list(row.dialogues)
    for child in children:
        propagate_access_state(child)


def learner_visible(row: Any) -> bool:
    if getattr(row, "is_deleted", False):
        return False
    if getattr(row, "status", None) != "published":
        return False
    return getattr(row, "resolved_access_state", getattr(row, "access_state", "free")) not in HIDDEN_ACCESS_STATES


def locked_for_viewer(row: Any, *, has_premium: bool) -> bool:
    if not learner_visible(row):
        return True
    return getattr(row, "resolved_access_state", getattr(row, "access_state", "free")) == PREMIUM_ACCESS_STATE and not has_premium


def sync_all_content_access(db: Session) -> None:
    for row in db.query(LearningPath).all():
        _normalize_seed_state(row)
        propagate_access_state(row)
    for row in db.query(Vocabulary).all():
        _normalize_seed_state(row)
        sync_access_state(row)
    for row in db.query(GrammarPoint).all():
        _normalize_seed_state(row)
        sync_access_state(row)
    for row in db.query(ExampleSentence).all():
        _normalize_seed_state(row)
        sync_access_state(row)
    for row in db.query(Scenario).all():
        _normalize_seed_state(row)
        propagate_access_state(row)
    db.commit()


def _normalize_seed_state(row: Any) -> None:
    if hasattr(row, "is_premium") and getattr(row, "is_premium", False) and getattr(row, "access_state", "free") == "free":
        row.access_state = PREMIUM_ACCESS_STATE
