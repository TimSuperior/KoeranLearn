from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.security import get_current_user_or_internal, require_same_user_or_internal
from app.models.schema import User
from app.schemas import WritingCorrectionRequest, WritingCorrectionResponse
from app.services.analytics import track_event
from app.services.writing_service import correct_writing

router = APIRouter(prefix="/api/writing", tags=["writing"])


@router.post("/correct", response_model=WritingCorrectionResponse)
def correct(
    payload: WritingCorrectionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
    settings: Settings = Depends(get_settings),
    x_internal_token: str | None = Header(default=None),
):
    require_same_user_or_internal(user, payload.telegram_id, x_internal_token, settings)
    track_event(db, "writing_correction_requested", user.telegram_id, user.interface_language, {"target_register": payload.target_register})
    return correct_writing(db, user, payload.text, payload.target_register, payload.include_translation)
