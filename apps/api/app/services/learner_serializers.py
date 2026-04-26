from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.schema import Dialogue, ExampleSentence, Exercise, GrammarPoint, Lesson, LessonAsset, LessonBlock, Scenario, User, Vocabulary
from app.services.audio_service import audio_assets_for_content, learner_audio_bundle, listening_exercise
from app.services.premium import has_active_subscription


def serialize_lesson(db: Session, user: User, settings: Settings, lesson: Lesson) -> dict[str, Any]:
    lesson_bundle = learner_audio_bundle(db, user, settings, audio_assets_for_content(lesson, role="lesson_attachment") or audio_assets_for_content(lesson))
    blocks = [serialize_lesson_block(db, user, settings, block) for block in sorted((item for item in lesson.blocks if not item.is_deleted and item.status != "archived"), key=lambda item: item.order_index)]
    exercises = []
    for exercise in sorted((item for item in lesson.exercises if not item.is_deleted and item.status == "published"), key=lambda item: item.order_index):
        item = serialize_exercise(db, user, settings, exercise)
        if item is not None:
            exercises.append(item)
    nested_audio_available = any(_payload_has_audio(block["payload"]) for block in blocks) or any(_payload_has_audio(exercise["payload"]) for exercise in exercises)
    nested_audio_locked = any((block["payload"] or {}).get("audio_locked") for block in blocks) or any((exercise["payload"] or {}).get("audio_locked") for exercise in exercises)
    nested_audio_missing = any((block["payload"] or {}).get("audio_missing") for block in blocks) or any((exercise["payload"] or {}).get("audio_missing") for exercise in exercises)
    audio_available = bool(lesson_bundle["items"]) or nested_audio_available
    lesson_assets = [serialize_legacy_lesson_asset(asset) for asset in lesson.assets if not asset.url or "audio" not in (asset.asset_type or "").lower()]
    for item in lesson_bundle["items"]:
        lesson_assets.append(
            {
                "id": item["id"],
                "asset_type": f"audio_{item['attachment_role']}",
                "url": item["playback_url"],
                "metadata_json": {
                    "label": item["label"],
                    "variant": item["variant"],
                    "duration_seconds": item["duration_seconds"],
                    "transcript": item["transcript"],
                    "transcript_mode": item["transcript_mode"],
                },
            }
        )
    return {
        "id": lesson.id,
        "slug": lesson.slug,
        "title": lesson.title,
        "summary": lesson.summary,
        "objectives": list(lesson.objectives or []),
        "korean_text": lesson.korean_text,
        "explanation": lesson.explanation,
        "transfer_notes": lesson.transfer_notes,
        "tags": list(lesson.tags or []),
        "difficulty": lesson.difficulty,
        "topic": lesson.topic,
        "grammar_category": lesson.grammar_category,
        "politeness_level": lesson.politeness_level,
        "estimated_minutes": lesson.estimated_minutes,
        "order_index": lesson.order_index,
        "cover_metadata": lesson.cover_metadata,
        "audience_metadata": lesson.audience_metadata,
        "prerequisite_lesson_ids": list(lesson.prerequisite_lesson_ids or []),
        "is_premium": lesson.is_premium,
        "status": lesson.status,
        "access_state": lesson.access_state,
        "resolved_access_state": lesson.resolved_access_state,
        "has_audio": audio_available,
        "has_premium_audio": bool(lesson_bundle["items"]) or lesson_bundle["locked"] or lesson_bundle["missing"] or nested_audio_available or nested_audio_locked or nested_audio_missing,
        "audio_locked": lesson_bundle["locked"] or nested_audio_locked,
        "audio_missing": lesson_bundle["missing"] or nested_audio_missing,
        "assets": lesson_assets,
        "blocks": blocks,
        "exercises": exercises,
        "related_vocabulary": [serialize_vocabulary_reference(db, user, settings, row) for row in sorted(lesson.related_vocabulary, key=lambda item: item.korean)],
        "related_grammar": [serialize_grammar_reference(row) for row in sorted(lesson.related_grammar, key=lambda item: item.korean_pattern)],
        "related_scenarios": [serialize_scenario_reference(db, user, settings, row) for row in sorted(lesson.related_scenarios, key=lambda item: item.order_index)],
    }


def serialize_lesson_reference(db: Session, user: User, settings: Settings, lesson: Lesson) -> dict[str, Any]:
    bundle = learner_audio_bundle(db, user, settings, audio_assets_for_content(lesson))
    has_audio_access = has_active_subscription(db, user)
    has_block_audio = any(audio_assets_for_content(block) for block in lesson.blocks if not block.is_deleted and block.status != "archived")
    has_exercise_audio = any(audio_assets_for_content(exercise) for exercise in lesson.exercises if not exercise.is_deleted and exercise.status == "published")
    has_premium_audio = bool(audio_assets_for_content(lesson)) or has_block_audio or has_exercise_audio
    return {
        "id": lesson.id,
        "slug": lesson.slug,
        "title": lesson.title,
        "summary": lesson.summary,
        "has_audio": has_premium_audio and has_audio_access,
        "has_premium_audio": has_premium_audio,
        "audio_locked": has_premium_audio and not has_audio_access,
        "estimated_minutes": lesson.estimated_minutes,
    }


def serialize_scenario_reference(db: Session, user: User, settings: Settings, scenario: Scenario) -> dict[str, Any]:
    bundle = learner_audio_bundle(db, user, settings, audio_assets_for_content(scenario))
    has_line_audio = any(audio_assets_for_content(line) for dialogue in scenario.dialogues for line in dialogue.dialogue_lines)
    has_audio_access = has_active_subscription(db, user)
    return {
        "id": scenario.id,
        "slug": scenario.slug,
        "title": scenario.title,
        "description": scenario.description,
        "topic": scenario.topic,
        "difficulty": scenario.difficulty,
        "context_labels": list(scenario.context_labels or []),
        "is_premium": scenario.is_premium,
        "has_premium_audio": bool(audio_assets_for_content(scenario)) or has_line_audio,
        "audio_locked": bundle["locked"] or (has_line_audio and not has_audio_access),
    }


def serialize_vocabulary_reference(db: Session, user: User, settings: Settings, vocab: Vocabulary) -> dict[str, Any]:
    bundle = learner_audio_bundle(db, user, settings, audio_assets_for_content(vocab))
    first = _first_audio_url(bundle["items"])
    return {
        "id": vocab.id,
        "slug": vocab.slug,
        "korean": vocab.korean,
        "reading": vocab.reading,
        "translations": vocab.translations,
        "topic": vocab.topic,
        "difficulty": vocab.difficulty,
        "audio_asset_url": first,
        "audio_items": bundle["items"],
        "audio_locked": bundle["locked"],
        "is_premium": vocab.is_premium,
    }


def serialize_grammar_reference(grammar: GrammarPoint) -> dict[str, Any]:
    return {
        "id": grammar.id,
        "slug": grammar.slug,
        "korean_pattern": grammar.korean_pattern,
        "title": grammar.title,
        "category": grammar.category,
        "difficulty": grammar.difficulty,
        "is_premium": grammar.is_premium,
    }


def serialize_example_sentence(db: Session, user: User, settings: Settings, row: ExampleSentence) -> dict[str, Any]:
    bundle = learner_audio_bundle(db, user, settings, audio_assets_for_content(row))
    return {
        "id": row.id,
        "korean": row.korean,
        "translations": row.translations,
        "explanation": row.explanation,
        "context_labels": list(row.context_labels or []),
        "politeness_level": row.politeness_level,
        "register": row.register,
        "audio_items": bundle["items"],
        "audio_locked": bundle["locked"],
        "audio_missing": bundle["missing"],
        "is_premium": row.is_premium,
    }


def serialize_vocabulary(db: Session, user: User, settings: Settings, row: Vocabulary, *, detail: bool = False) -> dict[str, Any]:
    bundle = learner_audio_bundle(db, user, settings, audio_assets_for_content(row))
    first = _first_audio_url(bundle["items"])
    example_rows = [
        serialize_example_sentence(db, user, settings, sentence)
        for sentence in sorted((item for item in row.example_sentence_records if not item.is_deleted and item.status == "published"), key=lambda item: item.id)
    ]
    if not example_rows:
        example_rows = list(row.example_sentences or [])
    example_audio_present = any(
        isinstance(sentence, dict) and (sentence.get("audio_items") or sentence.get("audio_locked") or sentence.get("audio_missing"))
        for sentence in example_rows
    )
    example_audio_locked = any(isinstance(sentence, dict) and sentence.get("audio_locked") for sentence in example_rows)
    payload = {
        "id": row.id,
        "slug": row.slug,
        "korean": row.korean,
        "reading": row.reading,
        "translations": row.translations,
        "usage_notes": row.usage_notes,
        "notes": row.notes,
        "variants": list(row.variants or []),
        "topic": row.topic,
        "tags": list(row.tags or []),
        "difficulty": row.difficulty,
        "politeness_level": row.politeness_level,
        "example_sentences": example_rows,
        "audio_asset_url": first,
        "audio_items": bundle["items"],
        "audio_locked": bundle["locked"] or example_audio_locked,
        "has_premium_audio": bool(audio_assets_for_content(row)) or example_audio_present,
        "is_premium": row.is_premium,
    }
    if detail:
        payload["related_lessons"] = [serialize_lesson_reference(db, user, settings, lesson) for lesson in sorted(row.related_lessons, key=lambda item: item.order_index)]
        payload["related_scenarios"] = [serialize_scenario_reference(db, user, settings, scenario) for scenario in sorted(row.related_scenarios, key=lambda item: item.order_index)]
    return payload


def serialize_grammar(db: Session, user: User, settings: Settings, row: GrammarPoint, *, detail: bool = False) -> dict[str, Any]:
    payload = {
        "id": row.id,
        "slug": row.slug,
        "korean_pattern": row.korean_pattern,
        "title": row.title,
        "explanation": row.explanation,
        "usage_notes": row.usage_notes,
        "transfer_notes": row.transfer_notes,
        "common_errors": row.common_errors,
        "natural_alternatives": list(row.natural_alternatives or []),
        "category": row.category,
        "difficulty": row.difficulty,
        "politeness_level": row.politeness_level,
        "tags": list(row.tags or []),
        "is_premium": row.is_premium,
    }
    if detail:
        payload["example_sentences"] = [
            serialize_example_sentence(db, user, settings, sentence)
            for sentence in sorted((item for item in row.example_sentence_records if not item.is_deleted and item.status == "published"), key=lambda item: item.id)
        ]
        payload["related_lessons"] = [serialize_lesson_reference(db, user, settings, lesson) for lesson in sorted(row.related_lessons, key=lambda item: item.order_index)]
        payload["related_scenarios"] = [serialize_scenario_reference(db, user, settings, scenario) for scenario in sorted(row.related_scenarios, key=lambda item: item.order_index)]
    return payload


def serialize_scenario(db: Session, user: User, settings: Settings, scenario: Scenario, *, progress: dict[str, Any] | None = None, favorite: bool = False, detail: bool = False) -> dict[str, Any]:
    scenario_bundle = learner_audio_bundle(db, user, settings, audio_assets_for_content(scenario))
    dialogues = [serialize_dialogue(db, user, settings, dialogue) for dialogue in sorted((item for item in scenario.dialogues if not item.is_deleted and item.status == "published"), key=lambda item: item.order_index)]
    has_line_audio = any(line.get("audio_locked") or line.get("audio_asset_url") or line.get("audio_missing") for dialogue in dialogues for line in dialogue.get("lines", []))
    has_line_audio_missing = any(line.get("audio_missing") for dialogue in dialogues for line in dialogue.get("lines", []))
    has_audio_access = has_active_subscription(db, user)
    payload = {
        "id": scenario.id,
        "slug": scenario.slug,
        "title": scenario.title,
        "description": scenario.description,
        "context_labels": list(scenario.context_labels or []),
        "roles": list(scenario.roles or []),
        "target_grammar_ids": list(scenario.target_grammar_ids or []),
        "target_vocabulary_ids": list(scenario.target_vocabulary_ids or []),
        "tags": list(scenario.tags or []),
        "audience_languages": list(scenario.audience_languages or []),
        "topic": scenario.topic,
        "difficulty": scenario.difficulty,
        "order_index": scenario.order_index,
        "is_premium": scenario.is_premium,
        "has_premium_audio": bool(audio_assets_for_content(scenario)) or has_line_audio,
        "audio_locked": scenario_bundle["locked"] or (has_line_audio and not has_audio_access),
        "status": scenario.status,
        "progress": progress,
        "is_favorited": favorite,
    }
    if detail:
        payload["dialogues"] = dialogues
        payload["audio_items"] = scenario_bundle["items"]
        payload["audio_missing"] = scenario_bundle["missing"] or has_line_audio_missing
        payload["related_vocab"] = [serialize_vocabulary(db, user, settings, row, detail=False) for row in sorted(scenario.related_vocabulary, key=lambda item: item.korean)]
        payload["related_grammar"] = [serialize_grammar(db, user, settings, row, detail=False) for row in sorted(scenario.related_grammar, key=lambda item: item.korean_pattern)]
    return payload


def serialize_dialogue(db: Session, user: User, settings: Settings, dialogue: Dialogue) -> dict[str, Any]:
    lines = []
    for line in sorted((item for item in dialogue.dialogue_lines), key=lambda item: item.order_index):
        bundle = learner_audio_bundle(db, user, settings, audio_assets_for_content(line))
        payload = {
            "id": line.id,
            "speaker": line.speaker,
            "korean": line.korean,
            "translations": line.translations,
            "notes": line.notes,
            "audio_asset_url": _first_audio_url(bundle["items"]),
            "audio_items": bundle["items"],
            "audio_locked": bundle["locked"],
            "audio_missing": bundle["missing"],
            "reveal_mode": line.reveal_mode,
            "highlighted_expressions": list(line.highlighted_expressions or []),
            "is_useful_expression": line.is_useful_expression,
            "order_index": line.order_index,
        }
        lines.append(payload)
    return {
        "id": dialogue.id,
        "scenario_id": dialogue.scenario_id,
        "title": dialogue.title,
        "context": dialogue.context,
        "lines": lines,
        "checks": list(dialogue.checks or []),
        "useful_expressions": list(dialogue.useful_expressions or []),
        "explanation": dialogue.explanation,
        "politeness_level": dialogue.politeness_level,
        "order_index": dialogue.order_index,
        "is_premium": dialogue.is_premium,
        "status": dialogue.status,
    }


def serialize_exercise(db: Session, user: User, settings: Settings, exercise: Exercise) -> dict[str, Any] | None:
    bundle = learner_audio_bundle(db, user, settings, audio_assets_for_content(exercise))
    if listening_exercise(exercise) and bundle["locked"]:
        return None
    payload = dict(exercise.payload or {})
    payload.pop("audio_url", None)
    payload.pop("audio_asset_url", None)
    payload["audio_items"] = bundle["items"]
    payload["audio_asset_url"] = _first_audio_url(bundle["items"])
    payload["audio_locked"] = bundle["locked"]
    payload["audio_missing"] = bundle["missing"]
    payload["is_listening_exercise"] = listening_exercise(exercise)
    return {
        "id": exercise.id,
        "slug": exercise.slug,
        "exercise_type": exercise.exercise_type,
        "prompt": exercise.prompt,
        "instructions": exercise.instructions,
        "payload": payload,
        "answer_key": exercise.answer_key,
        "explanation": exercise.explanation,
        "difficulty": exercise.difficulty,
        "topic": exercise.topic,
        "tags": list(exercise.tags or []),
        "politeness_level": exercise.politeness_level,
        "order_index": exercise.order_index,
        "is_premium": exercise.is_premium,
        "options": [
            {
                "id": option.id,
                "value": option.value,
                "label": option.label,
                "order_index": option.order_index,
            }
            for option in sorted(exercise.options, key=lambda item: item.order_index)
        ],
    }


def serialize_lesson_block(db: Session, user: User, settings: Settings, block: LessonBlock) -> dict[str, Any]:
    bundle = learner_audio_bundle(db, user, settings, audio_assets_for_content(block))
    payload = dict(block.payload or {})
    payload.pop("audio_url", None)
    payload.pop("audio_asset_url", None)
    payload["audio_items"] = bundle["items"]
    payload["audio_asset_url"] = _first_audio_url(bundle["items"])
    payload["audio_locked"] = bundle["locked"]
    payload["audio_missing"] = bundle["missing"]
    return {
        "id": block.id,
        "block_type": block.block_type,
        "title": block.title,
        "body": block.body,
        "payload": payload,
        "order_index": block.order_index,
        "status": block.status,
    }


def serialize_legacy_lesson_asset(asset: LessonAsset) -> dict[str, Any]:
    return {
        "id": asset.id,
        "asset_type": asset.asset_type,
        "url": asset.url,
        "metadata_json": asset.metadata_json,
    }


def _first_audio_url(items: list[dict[str, Any]]) -> str | None:
    if not items:
        return None
    return str(items[0]["playback_url"])


def _payload_has_audio(payload: Any) -> bool:
    return isinstance(payload, dict) and bool(payload.get("audio_asset_url"))
