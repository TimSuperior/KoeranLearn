from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.models.schema import AudioAsset
from app.services.audio_service import audio_asset_stream_response, decode_audio_access_token, validate_audio_stream_access

router = APIRouter(prefix="/api/audio", tags=["audio"])


@router.get("/{public_id}/stream")
def stream_audio(
    public_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    asset = (
        db.query(AudioAsset)
        .options(
            selectinload(AudioAsset.lesson),
            selectinload(AudioAsset.lesson_block),
            selectinload(AudioAsset.exercise),
            selectinload(AudioAsset.vocabulary),
            selectinload(AudioAsset.example_sentence),
            selectinload(AudioAsset.dialogue_line),
            selectinload(AudioAsset.scenario),
        )
        .filter(AudioAsset.public_id == public_id, AudioAsset.is_deleted.is_(False))
        .first()
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio asset not found.")
    payload = decode_audio_access_token(token, settings)
    validate_audio_stream_access(db, asset, payload)
    return audio_asset_stream_response(db, asset, settings, token_payload=payload)
