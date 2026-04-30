from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.admin_schemas import ValidationIssue, ValidationResult
from app.models.schema import (
    Course,
    Dialogue,
    DialogueLine,
    ExampleSentence,
    Exercise,
    ExerciseOption,
    GrammarPoint,
    LearningPath,
    Lesson,
    LessonBlock,
    LocalizationEntry,
    Module,
    PremiumPack,
    Scenario,
    Vocabulary,
)


LOCALIZED_LANGUAGES = ("ru", "uz", "en")
LESSON_BLOCK_TYPES = {
    "explanation",
    "vocabulary",
    "grammar",
    "example_sentence",
    "exercise",
    "recap",
    "quiz",
    "scenario_link",
}
EXERCISE_TYPES = {
    "multiple_choice",
    "fill_in_blank",
    "sentence_reorder",
    "match_pairs",
    "choose_particle",
    "choose_verb_ending",
    "translation_selection",
    "dialogue_continuation",
    "listen_and_choose",
    "listen_and_order",
    "listen_and_match",
    "true_false",
    "flashcard_review",
}

ENTITY_MODELS = {
    "paths": LearningPath,
    "courses": Course,
    "modules": Module,
    "lessons": Lesson,
    "lesson-blocks": LessonBlock,
    "exercises": Exercise,
    "exercise-options": ExerciseOption,
    "vocabulary": Vocabulary,
    "grammar": GrammarPoint,
    "example-sentences": ExampleSentence,
    "scenarios": Scenario,
    "dialogues": Dialogue,
    "dialogue-lines": DialogueLine,
    "localization": LocalizationEntry,
    "premium-packs": PremiumPack,
}


def validate_entity_payload(
    db: Session,
    entity: str,
    data: dict[str, Any],
    *,
    relation_ids: dict[str, list[int]] | None = None,
    children: dict[str, list[dict[str, Any]]] | None = None,
) -> ValidationResult:
    relation_ids = relation_ids or {}
    children = children or {}
    issues: list[ValidationIssue] = []

    _require_slug(data, issues)
    _require_valid_status(data, issues)
    _require_valid_access_state(data, issues)

    if entity == "lessons":
        _validate_lesson(db, data, relation_ids, children, issues)
    elif entity == "vocabulary":
        _validate_vocabulary(data, issues)
    elif entity == "grammar":
        _validate_grammar(data, issues)
    elif entity == "scenarios":
        _validate_scenario(data, children, issues)
    elif entity == "dialogues":
        _validate_dialogue(db, data, children, issues)
    elif entity == "exercises":
        _validate_exercise(data, children, issues)
    elif entity == "lesson-blocks":
        _validate_lesson_block(data, issues)
    elif entity == "dialogue-lines":
        _validate_dialogue_line(data, issues)
    elif entity == "localization":
        _validate_localization(data, issues)
    elif entity == "example-sentences":
        _validate_example_sentence(data, issues)
    elif entity == "paths":
        _require_localized(data, "title", issues, required_all=True)
    elif entity == "courses":
        _require_localized(data, "title", issues, required_all=True)
    elif entity == "modules":
        _require_localized(data, "title", issues, required_all=True)
    elif entity == "premium-packs":
        _require_localized(data, "title", issues, required_all=True)

    _validate_relation_ids(db, relation_ids, issues)
    _validate_link_statuses(db, entity, data, relation_ids, children, issues)
    return ValidationResult(entity=entity, valid=not any(item.level == "error" for item in issues), issues=issues, checked_at=datetime.now(timezone.utc))


def ensure_publishable(
    db: Session,
    entity: str,
    data: dict[str, Any],
    *,
    relation_ids: dict[str, list[int]] | None = None,
    children: dict[str, list[dict[str, Any]]] | None = None,
) -> ValidationResult:
    result = validate_entity_payload(db, entity, data, relation_ids=relation_ids, children=children)
    if data.get("status") == "published" and any(item.level == "error" for item in result.issues):
        return result
    return result


def _require_slug(data: dict[str, Any], issues: list[ValidationIssue]) -> None:
    if "slug" in data and not str(data.get("slug") or "").strip():
        issues.append(ValidationIssue(level="error", code="missing_slug", field="slug", message="Slug is required."))


def _require_valid_status(data: dict[str, Any], issues: list[ValidationIssue]) -> None:
    status = data.get("status")
    if status and status not in {"draft", "published", "archived"}:
        issues.append(ValidationIssue(level="error", code="invalid_status", field="status", message=f"Unsupported status: {status}"))


def _require_valid_access_state(data: dict[str, Any], issues: list[ValidationIssue]) -> None:
    access_state = data.get("access_state")
    if access_state and access_state not in {"free", "premium", "hidden", "internal", "inherit"}:
        issues.append(
            ValidationIssue(level="error", code="invalid_access_state", field="access_state", message=f"Unsupported access state: {access_state}")
        )


def _require_localized(data: dict[str, Any], field: str, issues: list[ValidationIssue], *, required_all: bool = False, at_least_one: bool = False) -> None:
    value = data.get(field)
    if not isinstance(value, dict):
        issues.append(ValidationIssue(level="error", code="missing_localized_field", field=field, message=f"{field} must be a localized object."))
        return
    available = [language for language in LOCALIZED_LANGUAGES if str(value.get(language) or "").strip()]
    if required_all:
        for language in LOCALIZED_LANGUAGES:
            if language not in available:
                issues.append(
                    ValidationIssue(
                        level="error",
                        code="missing_locale",
                        field=f"{field}.{language}",
                        message=f"{field} requires {language.upper()} content before publish.",
                    )
                )
    elif at_least_one and not available:
        issues.append(
            ValidationIssue(level="error", code="missing_locale", field=field, message=f"{field} needs at least one RU/UZ/EN value."))


def _validate_lesson(
    db: Session,
    data: dict[str, Any],
    relation_ids: dict[str, list[int]],
    children: dict[str, list[dict[str, Any]]],
    issues: list[ValidationIssue],
) -> None:
    _require_localized(data, "title", issues, required_all=True)
    if not data.get("objectives"):
        issues.append(ValidationIssue(level="error", code="missing_objectives", field="objectives", message="Lesson objectives are required."))
    if not data.get("module_id"):
        issues.append(ValidationIssue(level="error", code="missing_module", field="module_id", message="Lesson must belong to a module."))
    elif not db.get(Module, data["module_id"]):
        issues.append(ValidationIssue(level="error", code="missing_module", field="module_id", message="Selected module does not exist."))

    blocks = children.get("blocks") or []
    if not blocks:
        issues.append(ValidationIssue(level="error", code="missing_blocks", field="blocks", message="Lesson needs at least one block before publish."))
    for index, block in enumerate(blocks, start=1):
        if block.get("status", "draft") == "archived":
            continue
        _validate_lesson_block(block, issues, prefix=f"blocks[{index}]")
    _warn_if_localized_lists_identical(data, "transfer_notes", issues)
    if not relation_ids.get("related_vocabulary"):
        issues.append(ValidationIssue(level="warning", code="no_related_vocab", field="related_vocabulary", message="Lesson has no related vocabulary attached."))
    if not relation_ids.get("related_grammar"):
        issues.append(ValidationIssue(level="warning", code="no_related_grammar", field="related_grammar", message="Lesson has no related grammar attached."))


def _validate_vocabulary(data: dict[str, Any], issues: list[ValidationIssue]) -> None:
    if not str(data.get("korean") or "").strip():
        issues.append(ValidationIssue(level="error", code="missing_korean", field="korean", message="Korean word or phrase is required."))
    _require_localized(data, "translations", issues, at_least_one=True)
    missing = [language for language in LOCALIZED_LANGUAGES if not str((data.get("translations") or {}).get(language) or "").strip()]
    if missing:
        issues.append(
            ValidationIssue(level="warning", code="partial_localization", field="translations", message=f"Missing translations for: {', '.join(language.upper() for language in missing)}.")
        )


def _validate_grammar(data: dict[str, Any], issues: list[ValidationIssue]) -> None:
    if not str(data.get("korean_pattern") or "").strip():
        issues.append(ValidationIssue(level="error", code="missing_pattern", field="korean_pattern", message="Grammar pattern is required."))
    _require_localized(data, "title", issues, required_all=True)
    _require_localized(data, "explanation", issues, required_all=True)
    _warn_if_localized_lists_identical(data, "transfer_notes", issues)
    _warn_if_localized_lists_identical(data, "common_errors", issues)


def _validate_scenario(data: dict[str, Any], children: dict[str, list[dict[str, Any]]], issues: list[ValidationIssue]) -> None:
    _require_localized(data, "title", issues, required_all=True)
    dialogues = children.get("dialogues") or []
    if not dialogues and not data.get("dialogue_ids"):
        issues.append(ValidationIssue(level="error", code="missing_dialogues", field="dialogues", message="Scenario requires at least one dialogue."))
    for index, dialogue in enumerate(dialogues, start=1):
        _validate_dialogue(None, dialogue, {"dialogue_lines": dialogue.get("dialogue_lines") or []}, issues, prefix=f"dialogues[{index}]")


def _validate_dialogue(
    db: Session | None,
    data: dict[str, Any],
    children: dict[str, list[dict[str, Any]]],
    issues: list[ValidationIssue],
    *,
    prefix: str = "",
) -> None:
    if not data.get("scenario_id") and not prefix:
        issues.append(ValidationIssue(level="error", code="missing_scenario", field=_field(prefix, "scenario_id"), message="Dialogue must belong to a scenario."))
    lines = children.get("dialogue_lines") or data.get("dialogue_lines") or data.get("lines") or []
    if not lines:
        issues.append(ValidationIssue(level="error", code="missing_lines", field=_field(prefix, "dialogue_lines"), message="Dialogue requires at least one line."))
        return
    for index, line in enumerate(lines, start=1):
        _validate_dialogue_line(line, issues, prefix=_field(prefix, f"dialogue_lines[{index}]"))


def _validate_dialogue_line(data: dict[str, Any], issues: list[ValidationIssue], *, prefix: str = "") -> None:
    if not str(data.get("speaker") or "").strip():
        issues.append(ValidationIssue(level="error", code="missing_speaker", field=_field(prefix, "speaker"), message="Dialogue line speaker is required."))
    if not str(data.get("korean") or "").strip():
        issues.append(ValidationIssue(level="error", code="missing_korean", field=_field(prefix, "korean"), message="Dialogue line Korean text is required."))
    translations = data.get("translations") or {}
    if not any(str(translations.get(language) or "").strip() for language in LOCALIZED_LANGUAGES):
        issues.append(
            ValidationIssue(
                level="warning",
                code="missing_line_translation",
                field=_field(prefix, "translations"),
                message="Dialogue line should include at least one learner-language translation.",
            )
        )


def _validate_exercise(data: dict[str, Any], children: dict[str, list[dict[str, Any]]], issues: list[ValidationIssue]) -> None:
    exercise_type = data.get("exercise_type")
    if exercise_type not in EXERCISE_TYPES:
        issues.append(ValidationIssue(level="error", code="invalid_type", field="exercise_type", message="Unsupported exercise type."))
    _require_localized(data, "prompt", issues, required_all=True)
    if "answer_key" not in data or "value" not in (data.get("answer_key") or {}):
        issues.append(ValidationIssue(level="error", code="missing_answer_key", field="answer_key", message="Exercise answer definition is required."))

    options = children.get("options") or data.get("options") or []
    if exercise_type in {"multiple_choice", "choose_particle", "choose_verb_ending", "translation_selection", "dialogue_continuation", "listen_and_choose", "true_false"}:
        if len(options) < 2:
            issues.append(ValidationIssue(level="error", code="missing_options", field="options", message="Option-based exercises need at least two options."))
        elif not any(option.get("is_correct") for option in options):
            issues.append(ValidationIssue(level="error", code="missing_correct_option", field="options", message="At least one option must be marked correct."))
    if exercise_type in {"sentence_reorder", "listen_and_order"} and not isinstance((data.get("payload") or {}).get("tokens"), list):
        issues.append(ValidationIssue(level="error", code="missing_tokens", field="payload.tokens", message="Sentence reorder exercises need token payload."))
    if exercise_type in {"match_pairs", "listen_and_match"} and not isinstance((data.get("answer_key") or {}).get("value"), (dict, list)):
        issues.append(ValidationIssue(level="error", code="missing_pairs", field="answer_key.value", message="Match pairs exercises need pair answers."))


def _validate_lesson_block(data: dict[str, Any], issues: list[ValidationIssue], *, prefix: str = "") -> None:
    block_type = data.get("block_type")
    if block_type not in LESSON_BLOCK_TYPES:
        issues.append(ValidationIssue(level="error", code="invalid_block_type", field=_field(prefix, "block_type"), message="Unsupported lesson block type."))
    if block_type in {"explanation", "recap", "grammar", "vocabulary", "quiz"}:
        _require_localized(data, "body", issues, at_least_one=True)
    if block_type == "exercise" and not ((data.get("payload") or {}).get("exercise_id") or (data.get("payload") or {}).get("exercise_ids")):
        issues.append(
            ValidationIssue(
                level="error",
                code="missing_block_exercise",
                field=_field(prefix, "payload.exercise_id"),
                message="Exercise blocks must reference one or more exercises.",
            )
        )
    if block_type == "scenario_link" and not (data.get("payload") or {}).get("scenario_id"):
        issues.append(
            ValidationIssue(
                level="error",
                code="missing_block_scenario",
                field=_field(prefix, "payload.scenario_id"),
                message="Scenario link blocks must reference a scenario.",
            )
        )


def _validate_localization(data: dict[str, Any], issues: list[ValidationIssue]) -> None:
    for field in ("namespace", "key", "language", "value"):
        if not str(data.get(field) or "").strip():
            issues.append(ValidationIssue(level="error", code=f"missing_{field}", field=field, message=f"{field} is required."))


def _validate_example_sentence(data: dict[str, Any], issues: list[ValidationIssue]) -> None:
    if not str(data.get("korean") or "").strip():
        issues.append(ValidationIssue(level="error", code="missing_korean", field="korean", message="Example sentence Korean text is required."))
    _require_localized(data, "translations", issues, at_least_one=True)


def _warn_if_localized_lists_identical(data: dict[str, Any], field: str, issues: list[ValidationIssue]) -> None:
    value = data.get(field)
    if not isinstance(value, dict):
        return
    normalized: dict[str, tuple[str, ...]] = {}
    for language in LOCALIZED_LANGUAGES:
        raw_items = value.get(language)
        if not isinstance(raw_items, list):
            return
        cleaned = tuple(str(item).strip() for item in raw_items if str(item).strip())
        if not cleaned:
            return
        normalized[language] = cleaned
    unique_sets = {items for items in normalized.values()}
    if len(unique_sets) == 1:
        issues.append(
            ValidationIssue(
                level="warning",
                code="localized_transfer_needs_adaptation",
                field=field,
                message=f"{field} should reflect learner-specific transfer issues instead of reusing the same RU/UZ/EN copy.",
            )
        )


def _validate_relation_ids(db: Session, relation_ids: dict[str, list[int]], issues: list[ValidationIssue]) -> None:
    relation_models = {
        "related_vocabulary": Vocabulary,
        "related_grammar": GrammarPoint,
        "related_scenarios": Scenario,
        "related_lessons": Lesson,
        "related_exercises": Exercise,
        "related_modules": Module,
    }
    for field, ids in relation_ids.items():
        model = relation_models.get(field)
        if not model:
            continue
        for item_id in ids:
            if not db.get(model, item_id):
                issues.append(
                    ValidationIssue(level="error", code="missing_relation", field=field, message=f"{field} item {item_id} does not exist."))


def _validate_link_statuses(
    db: Session,
    entity: str,
    data: dict[str, Any],
    relation_ids: dict[str, list[int]],
    children: dict[str, list[dict[str, Any]]],
    issues: list[ValidationIssue],
) -> None:
    if entity == "courses":
        _validate_parent_status(db, LearningPath, data.get("path_id"), "path_id", issues, "Course belongs to an unpublished path.")
    elif entity == "modules":
        _validate_parent_status(db, Course, data.get("course_id"), "course_id", issues, "Module belongs to an unpublished course.")
    elif entity == "lessons":
        _validate_parent_status(db, Module, data.get("module_id"), "module_id", issues, "Lesson belongs to an unpublished module.")
        _validate_optional_statuses(db, Lesson, data.get("prerequisite_lesson_ids") or [], "prerequisite_lesson_ids", issues, "warning")
        _validate_optional_statuses(db, Vocabulary, relation_ids.get("related_vocabulary") or [], "related_vocabulary", issues, "warning")
        _validate_optional_statuses(db, GrammarPoint, relation_ids.get("related_grammar") or [], "related_grammar", issues, "warning")
        _validate_optional_statuses(db, Scenario, relation_ids.get("related_scenarios") or [], "related_scenarios", issues, "warning")
        for index, block in enumerate(children.get("blocks") or [], start=1):
            _validate_block_links(db, block, issues, prefix=f"blocks[{index}]")
    elif entity == "lesson-blocks":
        _validate_parent_status(db, Lesson, data.get("lesson_id"), "lesson_id", issues, "Lesson block belongs to an unpublished lesson.")
        _validate_block_links(db, data, issues)
    elif entity == "exercises":
        _validate_optional_parent_status(db, Lesson, data.get("lesson_id"), "lesson_id", issues)
        _validate_optional_parent_status(db, GrammarPoint, data.get("grammar_point_id"), "grammar_point_id", issues)
        _validate_optional_parent_status(db, Vocabulary, data.get("vocabulary_id"), "vocabulary_id", issues)
    elif entity == "example-sentences":
        _validate_optional_parent_status(db, GrammarPoint, data.get("grammar_point_id"), "grammar_point_id", issues)
        _validate_optional_parent_status(db, Vocabulary, data.get("vocabulary_id"), "vocabulary_id", issues)
    elif entity == "vocabulary":
        _validate_optional_statuses(db, Lesson, relation_ids.get("related_lessons") or [], "related_lessons", issues, "warning")
        _validate_optional_statuses(db, Scenario, relation_ids.get("related_scenarios") or [], "related_scenarios", issues, "warning")
    elif entity == "grammar":
        _validate_optional_statuses(db, Lesson, relation_ids.get("related_lessons") or [], "related_lessons", issues, "warning")
        _validate_optional_statuses(db, Scenario, relation_ids.get("related_scenarios") or [], "related_scenarios", issues, "warning")
    elif entity == "scenarios":
        _validate_optional_statuses(db, Lesson, relation_ids.get("related_lessons") or [], "related_lessons", issues, "warning")
        _validate_optional_statuses(db, Vocabulary, relation_ids.get("related_vocabulary") or [], "related_vocabulary", issues, "warning")
        _validate_optional_statuses(db, GrammarPoint, relation_ids.get("related_grammar") or [], "related_grammar", issues, "warning")
        _validate_optional_statuses(db, Vocabulary, data.get("target_vocabulary_ids") or [], "target_vocabulary_ids", issues, "warning")
        _validate_optional_statuses(db, GrammarPoint, data.get("target_grammar_ids") or [], "target_grammar_ids", issues, "warning")
    elif entity == "dialogues":
        _validate_parent_status(db, Scenario, data.get("scenario_id"), "scenario_id", issues, "Dialogue belongs to an unpublished scenario.")
    elif entity == "dialogue-lines":
        _validate_parent_status(db, Dialogue, data.get("dialogue_id"), "dialogue_id", issues, "Dialogue line belongs to an unpublished dialogue.")


def _validate_parent_status(
    db: Session,
    model: type,
    item_id: int | None,
    field: str,
    issues: list[ValidationIssue],
    message: str,
) -> None:
    if not item_id:
        return
    row = db.get(model, item_id)
    if row is None:
        return
    if getattr(row, "status", "published") != "published":
        issues.append(ValidationIssue(level="error", code="unpublished_linked_content", field=field, message=message))


def _validate_optional_parent_status(db: Session, model: type, item_id: int | None, field: str, issues: list[ValidationIssue]) -> None:
    if not item_id:
        return
    row = db.get(model, item_id)
    if row is None:
        return
    if getattr(row, "status", "published") != "published":
        issues.append(
            ValidationIssue(
                level="warning",
                code="unpublished_linked_content",
                field=field,
                message=f"Linked {field.replace('_id', '').replace('_', ' ')} is not published yet.",
            )
        )


def _validate_optional_statuses(
    db: Session,
    model: type,
    item_ids: list[int],
    field: str,
    issues: list[ValidationIssue],
    level: str,
) -> None:
    for item_id in item_ids:
        row = db.get(model, item_id)
        if row is None:
            continue
        if getattr(row, "status", "published") != "published":
            issues.append(
                ValidationIssue(
                    level=level,  # type: ignore[arg-type]
                    code="unpublished_linked_content",
                    field=field,
                    message=f"{field} includes unpublished item {item_id}.",
                )
            )


def _validate_block_links(db: Session, block: dict[str, Any], issues: list[ValidationIssue], *, prefix: str = "") -> None:
    payload = block.get("payload") or {}
    block_type = block.get("block_type")
    if block_type == "exercise":
        exercise_ids = []
        if payload.get("exercise_id"):
            exercise_ids.append(payload["exercise_id"])
        if isinstance(payload.get("exercise_ids"), list):
            exercise_ids.extend(payload["exercise_ids"])
        for exercise_id in exercise_ids:
            row = db.get(Exercise, exercise_id)
            if row is None:
                continue
            if getattr(row, "status", "published") != "published":
                issues.append(
                    ValidationIssue(
                        level="error",
                        code="unpublished_linked_content",
                        field=_field(prefix, "payload.exercise_id"),
                        message=f"Exercise block references unpublished exercise {exercise_id}.",
                    )
                )
    if block_type == "scenario_link" and payload.get("scenario_id"):
        row = db.get(Scenario, payload["scenario_id"])
        if row is None:
            return
        if getattr(row, "status", "published") != "published":
            issues.append(
                ValidationIssue(
                    level="error",
                    code="unpublished_linked_content",
                    field=_field(prefix, "payload.scenario_id"),
                    message=f"Scenario block references unpublished scenario {payload['scenario_id']}.",
                )
            )


def _field(prefix: str, field: str) -> str:
    if not prefix:
        return field
    return f"{prefix}.{field}"
