from datetime import datetime, timezone

from app.admin_schemas import ValidationResult
from app.core.config import Settings
from app.models.schema import AudioAsset, Lesson, LessonBlock, User
from app.services.admin_content_service import validate_payload_entity
from app.services.learner_serializers import serialize_lesson


def test_serialize_lesson_marks_nested_audio_as_locked(monkeypatch) -> None:
    monkeypatch.setattr("app.services.audio_service.has_active_subscription", lambda db, user: False)
    monkeypatch.setattr("app.services.learner_serializers.has_active_subscription", lambda db, user: False)

    settings = Settings(secret_key="test-secret", audio_signed_url_ttl_seconds=60)
    user = User(id=1, telegram_id="1")
    block_audio = AudioAsset(
        public_id="lesson-block-audio",
        label={"en": "Block prompt"},
        attachment_role="lesson_block",
        variant="default",
        storage_backend="local",
        storage_key="demo/block.mp3",
        original_filename="block.mp3",
        mime_type="audio/mpeg",
        size_bytes=100,
        status="published",
        cache_version=1,
    )
    block = LessonBlock(block_type="explanation", title={"en": "Listen"}, body={"en": "Prompt"}, payload={}, status="published", audio_assets=[block_audio])
    lesson = Lesson(
        slug="premium-listening",
        title={"en": "Premium listening"},
        summary={"en": "Nested audio only"},
        objectives=[],
        explanation={"en": "Explanation"},
        transfer_notes={},
        tags=[],
        difficulty="A0",
        topic="general",
        politeness_level="polite",
        estimated_minutes=5,
        cover_metadata={},
        audience_metadata={},
        prerequisite_lesson_ids=[],
        status="published",
        access_state="free",
        resolved_access_state="free",
        blocks=[block],
        assets=[],
        exercises=[],
        related_vocabulary=[],
        related_grammar=[],
        related_scenarios=[],
    )

    serialized = serialize_lesson(object(), user, settings, lesson)

    assert serialized["has_premium_audio"] is True
    assert serialized["audio_locked"] is True
    assert serialized["has_audio"] is False
    assert serialized["blocks"][0]["payload"]["audio_locked"] is True


def test_validate_payload_entity_rejects_legacy_exercise_audio_urls(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.admin_content_service.ensure_publishable",
        lambda db, entity, data, relation_ids, children: ValidationResult(
            entity=entity,
            valid=True,
            issues=[],
            checked_at=datetime.now(timezone.utc),
        ),
    )

    payload = {
        "data": {
            "slug": "legacy-audio-exercise",
            "exercise_type": "listen_and_choose",
            "prompt": {"en": "Listen"},
            "instructions": {"en": "Choose"},
            "payload": {"audio_asset_url": "https://cdn.example.com/prompt.mp3"},
            "answer_key": {"value": "a"},
            "explanation": {"en": "Explanation"},
            "difficulty": "A0",
            "topic": "general",
        }
    }

    validation = validate_payload_entity(object(), "exercises", payload)

    assert validation.valid is False
    assert any(issue.code == "premium_audio_protected" and issue.field == "payload.audio_asset_url" for issue in validation.issues)


def test_validate_payload_entity_rejects_nested_lesson_block_audio_urls(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.admin_content_service.ensure_publishable",
        lambda db, entity, data, relation_ids, children: ValidationResult(
            entity=entity,
            valid=True,
            issues=[],
            checked_at=datetime.now(timezone.utc),
        ),
    )

    payload = {
        "data": {
            "slug": "lesson-with-legacy-audio",
            "title": {"en": "Lesson"},
            "summary": {"en": "Summary"},
            "explanation": {"en": "Explanation"},
            "difficulty": "A0",
            "topic": "general",
            "politeness_level": "polite",
            "estimated_minutes": 5,
        },
        "children": {
            "blocks": [
                {
                    "block_type": "explanation",
                    "title": {"en": "Listen"},
                    "body": {"en": "Body"},
                    "payload": {"audio_url": "https://cdn.example.com/prompt.mp3"},
                    "status": "draft",
                }
            ]
        },
    }

    validation = validate_payload_entity(object(), "lessons", payload)

    assert validation.valid is False
    assert any(issue.field == "children.blocks[0].payload.audio_asset_url" for issue in validation.issues)
