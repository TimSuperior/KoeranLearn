from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import mimetypes
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4
import wave

import httpx
from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.schema import AnalyticsEvent, AudioAsset, Exercise, Lesson, LessonBlock, Scenario, User, Vocabulary
from app.services.premium import has_active_subscription


LISTENING_EXERCISE_TYPES = {"listen_and_choose", "listen_and_order", "listen_and_match"}
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".oga", ".webm"}
ALLOWED_AUDIO_MIME_PREFIXES = ("audio/",)


def create_audio_access_token(
    *,
    public_id: str,
    subject_id: int,
    subject_type: str,
    cache_version: int,
    settings: Settings,
    ttl_seconds: int | None = None,
) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds or settings.audio_signed_url_ttl_seconds)
    payload = {
        "asset": public_id,
        "sub": f"{subject_type}:{subject_id}",
        "ver": cache_version,
        "exp": int(expires_at.timestamp()),
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _sign(body, settings.secret_key)
    return f"{body}.{signature}"


def decode_audio_access_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        body, signature = token.rsplit(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid audio token.") from exc
    if not hmac.compare_digest(_sign(body, settings.secret_key), signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid audio token.")
    try:
        payload = json.loads(_b64decode(body))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid audio token.") from exc
    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Audio token expired.")
    return payload


def learner_audio_url(asset: AudioAsset, user: User, settings: Settings) -> str:
    token = create_audio_access_token(
        public_id=asset.public_id,
        subject_id=user.id,
        subject_type="user",
        cache_version=asset.cache_version,
        settings=settings,
    )
    return f"/api/audio/{quote(asset.public_id)}/stream?token={quote(token)}"


def admin_preview_url(asset: AudioAsset, admin_id: int, settings: Settings) -> str:
    token = create_audio_access_token(
        public_id=asset.public_id,
        subject_id=admin_id,
        subject_type="admin",
        cache_version=asset.cache_version,
        settings=settings,
    )
    return f"/api/audio/{quote(asset.public_id)}/stream?token={quote(token)}"


def audio_assets_for_content(content: Any, *, role: str | None = None) -> list[AudioAsset]:
    rows = [
        asset
        for asset in sorted(getattr(content, "audio_assets", []) or [], key=lambda item: (item.order_index, item.id))
        if not asset.is_deleted
    ]
    if role:
        rows = [asset for asset in rows if asset.attachment_role == role]
    return rows


def learner_audio_bundle(db: Session, user: User, settings: Settings, assets: list[AudioAsset]) -> dict[str, Any]:
    published_assets = [asset for asset in assets if asset.status == "published" and not asset.is_deleted]
    locked = bool(published_assets) and not has_active_subscription(db, user)
    if locked:
        return {"items": [], "locked": True, "missing": False}
    items = []
    missing = False
    for asset in published_assets:
        if asset.compliance_state != "active":
            missing = True
            continue
        items.append(
            {
                "id": asset.id,
                "public_id": asset.public_id,
                "label": asset.label,
                "attachment_role": asset.attachment_role,
                "variant": asset.variant,
                "duration_seconds": asset.duration_seconds,
                "playback_url": learner_audio_url(asset, user, settings),
                "transcript": asset.transcript or {},
                "transcript_mode": asset.transcript_mode,
                "source_language": asset.source_language,
                "target_language": asset.target_language,
                "metadata_json": asset.metadata_json,
            }
        )
    return {"items": items, "locked": False, "missing": missing}


def listening_exercise(exercise: Exercise) -> bool:
    return exercise.exercise_type in LISTENING_EXERCISE_TYPES


def exercise_has_audio_prompt(exercise: Exercise) -> bool:
    if any(asset.status == "published" and not asset.is_deleted for asset in getattr(exercise, "audio_assets", []) or []):
        return True
    payload = exercise.payload or {}
    return bool(payload.get("audio_url") or payload.get("audio_asset_url"))


def lesson_has_premium_audio(lesson: Lesson) -> bool:
    if any(asset.status == "published" and not asset.is_deleted for asset in lesson.audio_assets):
        return True
    if any(asset.url for asset in lesson.assets if "audio" in (asset.asset_type or "").lower()):
        return True
    if any((block.payload or {}).get(key) for block in lesson.blocks for key in ("audio_url", "audio_asset_url")):
        return True
    return any((exercise.payload or {}).get(key) for exercise in lesson.exercises for key in ("audio_url", "audio_asset_url"))


def content_audio_lock(db: Session, user: User, assets: list[AudioAsset]) -> bool:
    return bool([asset for asset in assets if asset.status == "published" and not asset.is_deleted]) and not has_active_subscription(db, user)


def create_audio_asset_from_upload(
    *,
    db: Session,
    admin_id: int,
    file: UploadFile,
    settings: Settings,
    attachment_role: str = "general",
) -> AudioAsset:
    payload = file.file.read()
    validate_audio_upload(file, payload, settings)
    storage = _store_audio_upload(file=file, payload=payload, settings=settings)
    asset = AudioAsset(
        label={"en": Path(storage["original_filename"]).stem},
        attachment_role=attachment_role,
        storage_backend=storage["storage_backend"],
        storage_key=storage["storage_key"],
        original_filename=storage["original_filename"],
        mime_type=storage["mime_type"],
        size_bytes=storage["size_bytes"],
        duration_seconds=storage["duration_seconds"],
        metadata_json={"uploaded_at": datetime.now(timezone.utc).isoformat()},
        created_by_admin_id=admin_id,
        updated_by_admin_id=admin_id,
    )
    db.add(asset)
    db.flush()
    return asset


def replace_audio_asset_file(
    *,
    db: Session,
    asset: AudioAsset,
    admin_id: int,
    file: UploadFile,
    settings: Settings,
) -> AudioAsset:
    payload = file.file.read()
    validate_audio_upload(file, payload, settings)
    previous_storage_backend = asset.storage_backend
    previous_storage_key = asset.storage_key
    storage = _store_audio_upload(file=file, payload=payload, settings=settings)
    asset.storage_backend = storage["storage_backend"]
    asset.storage_key = storage["storage_key"]
    asset.original_filename = storage["original_filename"]
    asset.mime_type = storage["mime_type"]
    asset.size_bytes = storage["size_bytes"]
    asset.duration_seconds = storage["duration_seconds"]
    asset.compliance_state = "active"
    asset.last_error = None
    asset.last_verified_at = datetime.now(timezone.utc)
    asset.updated_by_admin_id = admin_id
    asset.cache_version += 1
    asset.metadata_json = {**(asset.metadata_json or {}), "uploaded_at": datetime.now(timezone.utc).isoformat()}
    if previous_storage_backend == "local" and previous_storage_key and previous_storage_key != asset.storage_key:
        _delete_local_audio(previous_storage_key, settings)
    db.add(asset)
    db.flush()
    return asset


def validate_audio_upload(file: UploadFile, payload: bytes, settings: Settings) -> None:
    suffix = Path(file.filename or "audio.bin").suffix.lower()
    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported audio file type.")
    content_type = file.content_type or _guess_audio_mime(suffix)
    if not any(content_type.startswith(prefix) for prefix in ALLOWED_AUDIO_MIME_PREFIXES):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported audio MIME type.")
    if len(payload) > settings.audio_max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio file exceeds the upload size limit.")


def audio_asset_stream_response(db: Session, asset: AudioAsset, settings: Settings, *, token_payload: dict[str, Any]):
    subject = str(token_payload.get("sub", ""))
    subject_type, _, subject_id = subject.partition(":")
    user_id = int(subject_id) if subject_type == "user" and subject_id.isdigit() else None
    if asset.storage_backend == "s3":
        response = _stream_s3_audio(asset, settings)
        _track_audio_stream(db, asset, user_id=user_id, subject_type=subject_type)
        return response
    path = _local_audio_path(asset.storage_key, settings)
    if not path.exists():
        mark_audio_asset_broken(db, asset, "Local audio file is missing.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file missing.")
    _track_audio_stream(db, asset, user_id=user_id, subject_type=subject_type)
    return FileResponse(path, media_type=asset.mime_type, filename=asset.original_filename)


def validate_audio_stream_access(db: Session, asset: AudioAsset, token_payload: dict[str, Any]) -> None:
    subject = str(token_payload.get("sub", ""))
    subject_type, _, subject_id = subject.partition(":")
    if token_payload.get("asset") != asset.public_id or int(token_payload.get("ver", -1)) != asset.cache_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Audio token no longer matches the current asset version.")
    if asset.is_deleted or asset.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio asset is unavailable.")
    if asset.compliance_state != "active":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Audio asset is disabled.")
    if not _attached_content_published(asset):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio content is not published.")
    if subject_type == "admin":
        return
    if subject_type != "user" or not subject_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Audio token subject is invalid.")
    user = db.get(User, int(subject_id))
    if not user or not has_active_subscription(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Premium access is required for audio playback.")


def mark_audio_asset_broken(db: Session, asset: AudioAsset, message: str) -> None:
    asset.compliance_state = "broken"
    asset.last_error = message[:500]
    asset.last_verified_at = datetime.now(timezone.utc)
    db.add(asset)
    db.add(
        AnalyticsEvent(
            event_name="premium_audio_delivery_failed",
            user_id=None,
            telegram_id=None,
            properties={"audio_asset_id": asset.id, "public_id": asset.public_id, "message": message[:250]},
        )
    )
    db.commit()


def audio_asset_admin_health(asset: AudioAsset, settings: Settings) -> dict[str, Any]:
    state = "active"
    if asset.status != "published":
        state = "unpublished"
    elif asset.compliance_state == "disabled":
        state = "disabled"
    elif asset.compliance_state == "broken":
        state = "broken"
    elif asset.storage_backend == "local" and not _local_audio_path(asset.storage_key, settings).exists():
        state = "missing"
    expiring_soon = bool(asset.expires_at and asset.expires_at <= datetime.now(timezone.utc) + timedelta(days=7))
    return {
        "state": state,
        "expiring_soon": expiring_soon,
        "missing_file": state == "missing",
        "preview_url": None,
    }


def _attached_content_published(asset: AudioAsset) -> bool:
    parents = [
        asset.lesson,
        asset.lesson_block,
        asset.exercise,
        asset.vocabulary,
        asset.example_sentence,
        asset.dialogue_line,
        asset.scenario,
    ]
    for parent in parents:
        if parent is None:
            continue
        if getattr(parent, "is_deleted", False):
            return False
        if getattr(parent, "status", "published") != "published":
            return False
        if hasattr(parent, "resolved_access_state") and getattr(parent, "resolved_access_state") in {"hidden", "internal"}:
            return False
    return True


def _extract_duration_seconds(payload: bytes, suffix: str) -> float | None:
    if suffix != ".wav":
        return None
    try:
        with wave.open(io.BytesIO(payload), "rb") as audio_file:
            frames = audio_file.getnframes()
            rate = audio_file.getframerate()
        if not rate:
            return None
        return round(frames / rate, 2)
    except Exception:  # noqa: BLE001
        return None


def _store_audio_upload(*, file: UploadFile, payload: bytes, settings: Settings) -> dict[str, Any]:
    suffix = Path(file.filename or "audio.bin").suffix.lower() or ".bin"
    storage_key = f"{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{uuid4().hex}{suffix}"
    mime_type = file.content_type or _guess_audio_mime(suffix)
    duration = _extract_duration_seconds(payload, suffix)
    storage_backend = settings.audio_storage_backend.strip().lower() or "local"
    if storage_backend == "s3":
        _upload_to_s3(storage_key, payload, mime_type, settings)
    else:
        _write_local_audio(storage_key, payload, settings)
        storage_backend = "local"
    return {
        "storage_backend": storage_backend,
        "storage_key": storage_key,
        "original_filename": file.filename or Path(storage_key).name,
        "mime_type": mime_type,
        "size_bytes": len(payload),
        "duration_seconds": duration,
    }


def _write_local_audio(storage_key: str, payload: bytes, settings: Settings) -> None:
    path = _local_audio_path(storage_key, settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _delete_local_audio(storage_key: str, settings: Settings) -> None:
    path = _local_audio_path(storage_key, settings)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        return


def _track_audio_stream(db: Session, asset: AudioAsset, *, user_id: int | None, subject_type: str) -> None:
    db.add(
        AnalyticsEvent(
            event_name="premium_audio_streamed",
            user_id=user_id,
            telegram_id=None,
            properties={
                "audio_asset_id": asset.id,
                "public_id": asset.public_id,
                "role": asset.attachment_role,
                "variant": asset.variant,
                "subject_type": subject_type or None,
            },
        )
    )
    db.commit()


def _local_audio_path(storage_key: str, settings: Settings) -> Path:
    return Path(settings.private_audio_dir).resolve() / Path(storage_key)


def _guess_audio_mime(suffix: str) -> str:
    mime, _ = mimetypes.guess_type(f"audio{suffix}")
    return mime or "audio/mpeg"


def _upload_to_s3(storage_key: str, payload: bytes, content_type: str, settings: Settings) -> None:
    endpoint = settings.audio_s3_endpoint.rstrip("/")
    bucket = settings.audio_s3_bucket.strip()
    if not endpoint or not bucket or not settings.audio_s3_access_key or not settings.audio_s3_secret_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 audio storage is not configured.")
    object_key = f"{settings.audio_s3_prefix.strip('/')}/{storage_key}".strip("/")
    canonical_uri = f"/{bucket}/{object_key}"
    headers = _signed_s3_headers(
        method="PUT",
        canonical_uri=canonical_uri,
        payload_hash=hashlib.sha256(payload).hexdigest(),
        settings=settings,
        content_type=content_type,
    )
    response = httpx.put(f"{endpoint}{canonical_uri}", headers=headers, content=payload, timeout=30)
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Uploading audio to object storage failed.")


def _stream_s3_audio(asset: AudioAsset, settings: Settings):
    endpoint = settings.audio_s3_endpoint.rstrip("/")
    bucket = settings.audio_s3_bucket.strip()
    object_key = f"{settings.audio_s3_prefix.strip('/')}/{asset.storage_key}".strip("/")
    canonical_uri = f"/{bucket}/{object_key}"
    headers = _signed_s3_headers(
        method="GET",
        canonical_uri=canonical_uri,
        payload_hash=hashlib.sha256(b"").hexdigest(),
        settings=settings,
        content_type=asset.mime_type,
    )
    client = httpx.Client(timeout=30)
    stream = client.stream("GET", f"{endpoint}{canonical_uri}", headers=headers)
    response = stream.__enter__()
    if response.status_code >= 400:
        stream.__exit__(None, None, None)
        client.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file missing.")

    def iterator():
        try:
            for chunk in response.iter_bytes():
                yield chunk
        finally:
            stream.__exit__(None, None, None)
            client.close()

    return StreamingResponse(iterator(), media_type=asset.mime_type)


def _signed_s3_headers(
    *,
    method: str,
    canonical_uri: str,
    payload_hash: str,
    settings: Settings,
    content_type: str,
) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    short_date = now.strftime("%Y%m%d")
    endpoint = settings.audio_s3_endpoint.replace("https://", "").replace("http://", "").split("/", 1)[0]
    host = endpoint
    headers = {
        "content-type": content_type,
        "host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    signed_header_names = ";".join(sorted(headers))
    canonical_headers = "".join(f"{key}:{headers[key]}\n" for key in sorted(headers))
    canonical_request = "\n".join(
        [
            method,
            canonical_uri,
            "",
            canonical_headers,
            signed_header_names,
            payload_hash,
        ]
    )
    scope = f"{short_date}/{settings.audio_s3_region}/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ]
    )
    signing_key = _s3_signing_key(settings.audio_s3_secret_key, short_date, settings.audio_s3_region, "s3")
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    auth = (
        f"AWS4-HMAC-SHA256 Credential={settings.audio_s3_access_key}/{scope}, "
        f"SignedHeaders={signed_header_names}, Signature={signature}"
    )
    return {
        "Authorization": auth,
        "Content-Type": content_type,
        "Host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }


def _s3_signing_key(secret_key: str, date_stamp: str, region: str, service: str) -> bytes:
    k_date = hmac.new(f"AWS4{secret_key}".encode(), date_stamp.encode(), hashlib.sha256).digest()
    k_region = hmac.new(k_date, region.encode(), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service.encode(), hashlib.sha256).digest()
    return hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(value: str, secret_key: str) -> str:
    return hmac.new(secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()
