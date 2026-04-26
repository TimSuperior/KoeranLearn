from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas import AnalyticsEventCreate
from app.services.analytics import track_event

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/events")
def create_event(payload: AnalyticsEventCreate, db: Session = Depends(get_db)):
    event = track_event(db, payload.event_name, payload.telegram_id, payload.audience_language, payload.properties)
    return {"id": event.id, "event_name": event.event_name}
