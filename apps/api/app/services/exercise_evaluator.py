import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.models.schema import Exercise


CHOICE_EXERCISE_TYPES = {
    "multiple_choice",
    "choose_particle",
    "choose_verb_ending",
    "translation_selection",
    "dialogue_continuation",
    "reading_comprehension",
    "listen_and_choose",
    "listening_comprehension",
    "true_false",
    "recap_quiz",
}
ORDER_EXERCISE_TYPES = {"sentence_reorder", "sentence_reordering", "listen_and_order"}
PAIR_EXERCISE_TYPES = {"match_pairs", "match_korean_translation", "match_word_usage", "listen_and_match"}
GRAMMAR_EXERCISE_TYPES = {"fill_blank", "choose_particle", "choose_verb_ending", "sentence_reorder", "sentence_reordering"}
LISTENING_REVIEW_EXERCISE_TYPES = {"listen_and_choose", "listen_and_order", "listen_and_match", "listening_comprehension"}
EXERCISE_TYPE_ALIASES = {
    "choose_ending": "choose_verb_ending",
    "sentence_reordering": "sentence_reorder",
    "listening_comprehension": "listen_and_choose",
}
BOOLEAN_TRUE_VALUES = {"true", "t", "yes", "y", "1", "correct"}
BOOLEAN_FALSE_VALUES = {"false", "f", "no", "n", "0", "incorrect"}
FLASHCARD_MISS_VALUES = {"missed", "again", "unknown", "hard", "false", "0"}


@dataclass(frozen=True)
class ExerciseEvaluation:
    is_correct: bool
    validator: str
    normalized_answer: Any
    normalized_expected: Any


def canonical_exercise_type(exercise_type: str) -> str:
    normalized_type = str(exercise_type or "").strip().casefold()
    return EXERCISE_TYPE_ALIASES.get(normalized_type, normalized_type)


def normalize_answer(value: Any) -> Any:
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFKC", value)
        normalized = normalized.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
        return re.sub(r"\s+", " ", normalized.strip()).casefold()
    if isinstance(value, list):
        return [normalize_answer(item) for item in value]
    if isinstance(value, dict):
        return {str(normalize_answer(key)): normalize_answer(item) for key, item in value.items()}
    return value


def evaluate_exercise(exercise: Exercise, answer: Any) -> bool:
    return evaluate_exercise_submission(exercise, answer).is_correct


def evaluate_exercise_submission(exercise: Exercise, answer: Any) -> ExerciseEvaluation:
    exercise_type = canonical_exercise_type(exercise.exercise_type)

    if exercise_type in {"multiple_choice", "choose_particle", "choose_verb_ending", "translation_selection", "dialogue_continuation", "reading_comprehension", "listen_and_choose", "recap_quiz"}:
        return _evaluate_choice_submission(exercise, answer, exercise_type)
    if exercise_type == "fill_blank":
        return _evaluate_fill_blank_submission(exercise, answer)
    if exercise_type in {"sentence_reorder", "listen_and_order"}:
        return _evaluate_order_submission(exercise, answer, exercise_type)
    if exercise_type in PAIR_EXERCISE_TYPES:
        return _evaluate_pair_submission(exercise, answer, exercise_type)
    if exercise_type == "true_false":
        return _evaluate_true_false_submission(exercise, answer)
    if exercise_type == "flashcard_review":
        return _evaluate_flashcard_submission(exercise, answer)
    return _evaluate_exact_submission(exercise, answer, exercise_type)


def _default_strategy(exercise_type: str) -> str:
    exercise_type = canonical_exercise_type(exercise_type)
    if exercise_type in CHOICE_EXERCISE_TYPES:
        return "one_of"
    if exercise_type in {"sentence_reorder", "listen_and_order"}:
        return "ordered_list"
    if exercise_type in PAIR_EXERCISE_TYPES:
        return "unordered_pairs"
    if exercise_type == "flashcard_review":
        return "self_assess"
    return "exact"


def _as_pair_set(value: Any) -> set[tuple[str, str]]:
    if isinstance(value, dict):
        return {(str(normalize_answer(key)), str(normalize_answer(item))) for key, item in value.items()}
    if isinstance(value, list):
        pairs = set()
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                pairs.add((str(normalize_answer(item[0])), str(normalize_answer(item[1]))))
            elif isinstance(item, dict) and {"left", "right"} <= set(item):
                pairs.add((str(normalize_answer(item["left"])), str(normalize_answer(item["right"]))))
        return pairs
    return set()


def _evaluate_choice_submission(exercise: Exercise, answer: Any, validator: str) -> ExerciseEvaluation:
    strategy = exercise.answer_validation.get("strategy") or _default_strategy(validator)
    normalized_answer = _canonical_choice_value(exercise, answer)
    expected_values = [_canonical_choice_value(exercise, item) for item in _choice_expected_values(exercise)]
    if strategy == "contains":
        is_correct = isinstance(normalized_answer, str) and all(item in normalized_answer for item in expected_values if isinstance(item, str))
    else:
        is_correct = normalized_answer in expected_values
    normalized_expected = expected_values if len(expected_values) > 1 else (expected_values[0] if expected_values else "")
    return ExerciseEvaluation(is_correct=is_correct, validator=validator, normalized_answer=normalized_answer, normalized_expected=normalized_expected)


def _evaluate_fill_blank_submission(exercise: Exercise, answer: Any) -> ExerciseEvaluation:
    strategy = exercise.answer_validation.get("strategy") or "one_of"
    normalized_answer = normalize_answer(answer)
    expected_values = [normalize_answer(item) for item in _choice_expected_values(exercise)]
    if strategy == "contains":
        is_correct = isinstance(normalized_answer, str) and all(item in normalized_answer for item in expected_values if isinstance(item, str))
    else:
        is_correct = normalized_answer in expected_values
    normalized_expected = expected_values if len(expected_values) > 1 else (expected_values[0] if expected_values else "")
    return ExerciseEvaluation(is_correct=is_correct, validator="fill_blank", normalized_answer=normalized_answer, normalized_expected=normalized_expected)


def _evaluate_order_submission(exercise: Exercise, answer: Any, validator: str) -> ExerciseEvaluation:
    normalized_answer = _normalize_sequence(answer)
    normalized_expected = _normalize_sequence(exercise.answer_key.get("value"))
    return ExerciseEvaluation(
        is_correct=bool(normalized_answer) and normalized_answer == normalized_expected,
        validator=validator,
        normalized_answer=normalized_answer,
        normalized_expected=normalized_expected,
    )


def _evaluate_pair_submission(exercise: Exercise, answer: Any, validator: str) -> ExerciseEvaluation:
    normalized_answer = _as_pair_set(answer)
    normalized_expected = _as_pair_set(exercise.answer_key.get("value"))
    return ExerciseEvaluation(
        is_correct=bool(normalized_answer) and normalized_answer == normalized_expected,
        validator=validator,
        normalized_answer=sorted(normalized_answer),
        normalized_expected=sorted(normalized_expected),
    )


def _evaluate_true_false_submission(exercise: Exercise, answer: Any) -> ExerciseEvaluation:
    normalized_answer = _canonical_boolean(_canonical_choice_value(exercise, answer))
    normalized_expected = _canonical_boolean(_canonical_choice_value(exercise, exercise.answer_key.get("value")))
    return ExerciseEvaluation(
        is_correct=normalized_answer == normalized_expected and normalized_answer in {"true", "false"},
        validator="true_false",
        normalized_answer=normalized_answer,
        normalized_expected=normalized_expected,
    )


def _evaluate_flashcard_submission(exercise: Exercise, answer: Any) -> ExerciseEvaluation:
    normalized_answer = _canonical_choice_value(exercise, answer)
    normalized_expected = _canonical_choice_value(exercise, exercise.answer_key.get("value") or exercise.options[0].value if exercise.options else "known")
    return ExerciseEvaluation(
        is_correct=bool(normalized_answer) and normalized_answer not in FLASHCARD_MISS_VALUES,
        validator="flashcard_review",
        normalized_answer=normalized_answer,
        normalized_expected=normalized_expected,
    )


def _evaluate_exact_submission(exercise: Exercise, answer: Any, validator: str) -> ExerciseEvaluation:
    strategy = exercise.answer_validation.get("strategy") or _default_strategy(validator)
    normalized_answer = normalize_answer(answer)
    normalized_expected = normalize_answer(exercise.answer_key.get("value"))
    if strategy == "contains":
        values = normalized_expected if isinstance(normalized_expected, list) else [normalized_expected]
        is_correct = all(isinstance(normalized_answer, str) and item in normalized_answer for item in values)
    elif isinstance(normalized_expected, dict):
        is_correct = normalized_answer == normalized_expected or normalized_answer in normalized_expected.values()
    else:
        is_correct = normalized_answer == normalized_expected
    return ExerciseEvaluation(is_correct=is_correct, validator=validator, normalized_answer=normalized_answer, normalized_expected=normalized_expected)


def _normalize_sequence(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item for item in normalize_answer(value).split(" ") if item]
    if isinstance(value, list):
        return [str(item) for item in normalize_answer(value) if str(item)]
    return []


def _choice_expected_values(exercise: Exercise) -> list[Any]:
    primary = exercise.answer_key.get("value")
    alternatives = exercise.answer_key.get("alternatives") or []
    values: list[Any] = []
    if isinstance(primary, list):
        values.extend(primary)
    elif primary is not None:
        values.append(primary)
    if isinstance(alternatives, list):
        values.extend(alternatives)
    elif alternatives:
        values.append(alternatives)
    return values


def _canonical_choice_value(exercise: Exercise, value: Any) -> str:
    if isinstance(value, dict):
        for key in ("value", "answer", "selected", "id", "label"):
            if key in value:
                return _canonical_choice_value(exercise, value[key])
        return normalize_answer(next(iter(value.values()), ""))
    if isinstance(value, bool):
        return "true" if value else "false"

    normalized = normalize_answer(value)
    if not isinstance(normalized, str):
        return str(normalized)
    alias_map = _choice_alias_map(exercise)
    return alias_map.get(normalized, normalized)


def _choice_alias_map(exercise: Exercise) -> dict[str, str]:
    alias_map: dict[str, str] = {}
    for option in exercise.options:
        canonical_value = normalize_answer(option.value)
        if not isinstance(canonical_value, str):
            canonical_value = str(canonical_value)
        alias_map[canonical_value] = canonical_value
        alias_map[str(option.id)] = canonical_value
        for label in (option.label or {}).values():
            normalized_label = normalize_answer(label)
            if isinstance(normalized_label, str) and normalized_label:
                alias_map[normalized_label] = canonical_value
    return alias_map


def _canonical_boolean(value: Any) -> str:
    normalized = normalize_answer(value)
    if normalized in BOOLEAN_TRUE_VALUES:
        return "true"
    if normalized in BOOLEAN_FALSE_VALUES:
        return "false"
    return str(normalized)
