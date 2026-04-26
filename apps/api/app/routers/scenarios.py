from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user_or_internal
from app.models.schema import User
from app.schemas import DialogueDTO, ScenarioCompleteRequest, ScenarioDetailDTO, ScenarioDTO, ScenarioFavoriteRequest, ScenarioProgressDTO
from app.services.scenario_service import (
    complete_scenario,
    get_dialogue,
    get_scenario_detail,
    list_scenarios,
    set_scenario_favorite,
    start_or_continue_scenario,
)

router = APIRouter(prefix="/api", tags=["scenarios"])


@router.get("/scenarios", response_model=list[ScenarioDTO])
def scenarios(
    topic: str | None = None,
    level: str | None = None,
    language: str = Query(default="en"),
    audience: str | None = None,
    include_premium: bool = False,
    q: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
):
    return list_scenarios(db, user, topic=topic, level=level, language=language, audience=audience, include_premium=include_premium, query=q)


@router.get("/scenarios/{scenario_id_or_slug}", response_model=ScenarioDetailDTO)
def scenario_detail(scenario_id_or_slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user_or_internal)):
    return get_scenario_detail(db, user, scenario_id_or_slug)


@router.post("/scenarios/{scenario_id_or_slug}/start")
def scenario_start(scenario_id_or_slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user_or_internal)):
    return start_or_continue_scenario(db, user, scenario_id_or_slug)


@router.post("/scenarios/{scenario_id_or_slug}/complete", response_model=ScenarioProgressDTO)
def scenario_complete(
    scenario_id_or_slug: str,
    payload: ScenarioCompleteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
):
    return complete_scenario(db, user, scenario_id_or_slug, payload.comprehension_score)


@router.post("/scenarios/{scenario_id_or_slug}/favorite")
def scenario_favorite(
    scenario_id_or_slug: str,
    payload: ScenarioFavoriteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
):
    return set_scenario_favorite(db, user, scenario_id_or_slug, payload.favorite)


@router.get("/dialogues/{dialogue_id}", response_model=DialogueDTO)
def dialogue_detail(dialogue_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user_or_internal)):
    return get_dialogue(db, user, dialogue_id)
