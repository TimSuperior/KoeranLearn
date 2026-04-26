from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.schema import Dialogue, DialogueLine, Scenario, User, UserBookmark, UserScenarioProgress, Vocabulary, utcnow
from app.services.analytics import track_event
from app.services.learner_serializers import serialize_dialogue, serialize_scenario
from app.services.premium import has_active_subscription, require_content_access


def _scenario_loader_options():
    return (
        selectinload(Scenario.audio_assets),
        selectinload(Scenario.dialogues).selectinload(Dialogue.dialogue_lines).selectinload(DialogueLine.audio_assets),
        selectinload(Scenario.related_vocabulary).selectinload(Vocabulary.audio_assets),
        selectinload(Scenario.related_grammar),
    )


def list_scenarios(
    db: Session,
    user: User,
    *,
    topic: str | None = None,
    level: str | None = None,
    language: str = "en",
    audience: str | None = None,
    include_premium: bool = False,
    query: str | None = None,
) -> list[dict[str, Any]]:
    scenarios = _scenario_query(db, include_premium=include_premium or has_active_subscription(db, user))
    if topic:
        scenarios = scenarios.filter(Scenario.topic == topic)
    if level:
        scenarios = scenarios.filter(Scenario.difficulty == level)
    if query:
        lowered = f"%{query.lower()}%"
        scenarios = scenarios.filter(or_(Scenario.slug.ilike(lowered), Scenario.topic.ilike(lowered)))
    rows = scenarios.order_by(Scenario.order_index, Scenario.id).all()
    if audience:
        rows = [row for row in rows if audience in (row.audience_languages or [])]
    progress_by_id = {
        row.scenario_id: row
        for row in db.query(UserScenarioProgress).filter(UserScenarioProgress.user_id == user.id).all()
    }
    favorites = {
        row.item_id
        for row in db.query(UserBookmark)
        .filter(UserBookmark.user_id == user.id, UserBookmark.item_type == "scenario")
        .all()
    }
    settings = get_settings()
    return [
        serialize_scenario(
            db,
            user,
            settings,
            row,
            progress=_serialize_progress(progress_by_id.get(row.id)) if progress_by_id.get(row.id) else None,
            favorite=row.id in favorites,
            detail=False,
        )
        for row in rows
    ]


def get_scenario_detail(db: Session, user: User, scenario_id_or_slug: str) -> dict[str, Any]:
    scenario = _get_scenario(db, scenario_id_or_slug)
    require_content_access(db, user, scenario.is_premium)
    progress = db.query(UserScenarioProgress).filter(UserScenarioProgress.user_id == user.id, UserScenarioProgress.scenario_id == scenario.id).first()
    favorite = (
        db.query(UserBookmark)
        .filter(UserBookmark.user_id == user.id, UserBookmark.item_type == "scenario", UserBookmark.item_id == scenario.id)
        .first()
        is not None
    )
    return serialize_scenario(
        db,
        user,
        get_settings(),
        scenario,
        progress=_serialize_progress(progress) if progress else None,
        favorite=favorite,
        detail=True,
    )


def get_dialogue(db: Session, user: User, dialogue_id: int) -> dict[str, Any]:
    dialogue = db.query(Dialogue).options(selectinload(Dialogue.dialogue_lines).selectinload(DialogueLine.audio_assets)).filter(Dialogue.id == dialogue_id).first()
    if not dialogue or dialogue.is_deleted or dialogue.status != "published" or dialogue.resolved_access_state in {"hidden", "internal"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialogue not found")
    require_content_access(db, user, dialogue.is_premium)
    return serialize_dialogue(db, user, get_settings(), dialogue)


def start_or_continue_scenario(db: Session, user: User, scenario_id_or_slug: str) -> dict[str, Any]:
    scenario = _get_scenario(db, scenario_id_or_slug)
    require_content_access(db, user, scenario.is_premium)
    dialogue = _first_dialogue(scenario)
    progress = (
        db.query(UserScenarioProgress)
        .filter(UserScenarioProgress.user_id == user.id, UserScenarioProgress.scenario_id == scenario.id)
        .first()
    )
    if not progress:
        progress = UserScenarioProgress(
            user_id=user.id,
            scenario_id=scenario.id,
            dialogue_id=dialogue.id if dialogue else None,
            status="in_progress",
            started_at=utcnow(),
        )
        db.add(progress)
    elif progress.status == "completed":
        progress.status = "in_progress"
        progress.current_line_index = 0
        progress.started_at = utcnow()
        progress.completed_at = None
    db.commit()
    track_event(db, "scenario_started", user.telegram_id, user.interface_language, {"scenario_id": scenario.id, "scenario_slug": scenario.slug})
    return {"scenario": get_scenario_detail(db, user, str(scenario.id)), "progress": _serialize_progress(progress)}


def complete_scenario(db: Session, user: User, scenario_id_or_slug: str, comprehension_score: float) -> dict[str, Any]:
    scenario = _get_scenario(db, scenario_id_or_slug)
    require_content_access(db, user, scenario.is_premium)
    progress = (
        db.query(UserScenarioProgress)
        .filter(UserScenarioProgress.user_id == user.id, UserScenarioProgress.scenario_id == scenario.id)
        .first()
    )
    if not progress:
        progress = UserScenarioProgress(user_id=user.id, scenario_id=scenario.id, started_at=utcnow())
        db.add(progress)
    progress.status = "completed"
    progress.comprehension_score = comprehension_score
    progress.completed_at = utcnow()
    user.xp += 5
    db.commit()
    track_event(db, "scenario_completed", user.telegram_id, user.interface_language, {"scenario_id": scenario.id, "score": comprehension_score})
    return _serialize_progress(progress)


def set_scenario_favorite(db: Session, user: User, scenario_id_or_slug: str, favorite: bool) -> dict[str, bool]:
    scenario = _get_scenario(db, scenario_id_or_slug)
    bookmark = (
        db.query(UserBookmark)
        .filter(UserBookmark.user_id == user.id, UserBookmark.item_type == "scenario", UserBookmark.item_id == scenario.id)
        .first()
    )
    if favorite and not bookmark:
        db.add(UserBookmark(user_id=user.id, item_type="scenario", item_id=scenario.id))
    if not favorite and bookmark:
        db.delete(bookmark)
    db.commit()
    return {"favorite": favorite}


def _scenario_query(db: Session, *, include_premium: bool):
    query = (
        db.query(Scenario)
        .options(*_scenario_loader_options())
        .filter(Scenario.is_deleted.is_(False), Scenario.status == "published")
        .filter(Scenario.resolved_access_state.notin_(["hidden", "internal"]))
    )
    if not include_premium:
        query = query.filter(Scenario.is_premium.is_(False))
    return query


def _get_scenario(db: Session, scenario_id_or_slug: str) -> Scenario:
    query = (
        db.query(Scenario)
        .options(*_scenario_loader_options())
        .filter(Scenario.is_deleted.is_(False), Scenario.status == "published")
        .filter(Scenario.resolved_access_state.notin_(["hidden", "internal"]))
    )
    if scenario_id_or_slug.isdigit():
        scenario = query.filter(Scenario.id == int(scenario_id_or_slug)).first()
    else:
        scenario = query.filter(Scenario.slug == scenario_id_or_slug).first()
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return scenario


def _first_dialogue(scenario: Scenario) -> Dialogue | None:
    dialogues = [
        dialogue
        for dialogue in scenario.dialogues
        if not dialogue.is_deleted and dialogue.status == "published" and dialogue.resolved_access_state not in {"hidden", "internal"}
    ]
    return sorted(dialogues, key=lambda item: item.order_index)[0] if dialogues else None
def _serialize_progress(progress: UserScenarioProgress | None) -> dict[str, Any] | None:
    if not progress:
        return None
    return {
        "scenario_id": progress.scenario_id,
        "dialogue_id": progress.dialogue_id,
        "status": progress.status,
        "current_line_index": progress.current_line_index,
        "comprehension_score": progress.comprehension_score,
    }
