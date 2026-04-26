import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.models.schema import AudioAsset, User
from app.services.audio_service import create_audio_access_token, decode_audio_access_token, learner_audio_bundle


def test_audio_token_roundtrip() -> None:
    settings = Settings(secret_key="test-secret", audio_signed_url_ttl_seconds=60)
    token = create_audio_access_token(
        public_id="audio-1",
        subject_id=42,
        subject_type="user",
        cache_version=3,
        settings=settings,
    )

    payload = decode_audio_access_token(token, settings)

    assert payload["asset"] == "audio-1"
    assert payload["sub"] == "user:42"
    assert payload["ver"] == 3


def test_audio_token_expiry_is_enforced() -> None:
    settings = Settings(secret_key="test-secret", audio_signed_url_ttl_seconds=60)
    token = create_audio_access_token(
        public_id="audio-1",
        subject_id=42,
        subject_type="user",
        cache_version=3,
        settings=settings,
        ttl_seconds=-1,
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_audio_access_token(token, settings)

    assert exc_info.value.status_code == 401


def test_learner_audio_bundle_includes_transcript_for_entitled_users(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.audio_service.has_active_subscription", lambda db, user: True)
    settings = Settings(secret_key="test-secret", audio_signed_url_ttl_seconds=60)
    user = User(id=1, telegram_id="1")
    asset = AudioAsset(
        public_id="audio-1",
        label={"en": "Prompt"},
        attachment_role="general",
        variant="default",
        storage_backend="local",
        storage_key="demo/audio.mp3",
        original_filename="audio.mp3",
        mime_type="audio/mpeg",
        size_bytes=100,
        status="published",
        transcript={"en": "Transcript"},
        transcript_mode="toggle",
        cache_version=1,
    )

    bundle = learner_audio_bundle(object(), user, settings, [asset])

    assert bundle["locked"] is False
    assert bundle["items"][0]["transcript"] == {"en": "Transcript"}
    assert bundle["items"][0]["transcript_mode"] == "toggle"


def test_learner_audio_bundle_hides_audio_for_free_users(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.audio_service.has_active_subscription", lambda db, user: False)
    settings = Settings(secret_key="test-secret", audio_signed_url_ttl_seconds=60)
    user = User(id=1, telegram_id="1")
    asset = AudioAsset(
        public_id="audio-1",
        label={"en": "Prompt"},
        attachment_role="general",
        variant="default",
        storage_backend="local",
        storage_key="demo/audio.mp3",
        original_filename="audio.mp3",
        mime_type="audio/mpeg",
        size_bytes=100,
        status="published",
        cache_version=1,
    )

    bundle = learner_audio_bundle(object(), user, settings, [asset])

    assert bundle == {"items": [], "locked": True, "missing": False}
