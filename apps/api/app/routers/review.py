from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.security import get_current_user_or_internal, require_same_user_or_internal
from app.models.schema import User
from app.schemas import ReviewItemDTO, ReviewSubmitRequest
from app.services.review_service import due_review_items, submit_review_result

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/queue/{telegram_id}", response_model=list[ReviewItemDTO])
def queue(
    telegram_id: str,
    mistakes_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_settings),
    x_internal_token: str | None = Header(default=None),
):
    require_same_user_or_internal(user, telegram_id, x_internal_token, settings)
    return due_review_items(db, user, limit=limit, mistakes_only=mistakes_only)


@router.post("/{review_item_id}/submit")
def submit(
    review_item_id: int,
    payload: ReviewSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_settings),
    x_internal_token: str | None = Header(default=None),
):
    require_same_user_or_internal(user, payload.telegram_id, x_internal_token, settings)
    item = submit_review_result(db, user, review_item_id, payload.answer, payload.is_correct, payload.quality)
    return {
        "id": item.id,
        "ease_score": item.ease_score,
        "interval_days": item.interval_days,
        "repetitions": item.repetitions,
        "next_review_at": item.next_review_at,
        "mastery_status": item.mastery_status,
        "mistake_count": item.mistake_count,
    }
