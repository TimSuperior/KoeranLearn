import re
from typing import Any

from app.models.schema import Exercise


def normalize_answer(value: Any) -> Any:
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value.strip()).casefold()
    if isinstance(value, list):
        return [normalize_answer(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_answer(item) for key, item in value.items()}
    return value


def evaluate_exercise(exercise: Exercise, answer: Any) -> bool:
    expected = exercise.answer_key.get("value")
    strategy = exercise.answer_validation.get("strategy") or _default_strategy(exercise.exercise_type)
    normalized_answer = normalize_answer(answer)
    normalized_expected = normalize_answer(expected)

    if strategy == "one_of":
        values = normalized_expected if isinstance(normalized_expected, list) else [normalized_expected]
        return normalized_answer in values
    if strategy == "ordered_list":
        return isinstance(normalized_answer, list) and normalized_answer == normalized_expected
    if strategy == "unordered_pairs":
        return _as_pair_set(normalized_answer) == _as_pair_set(normalized_expected)
    if strategy == "contains":
        values = normalized_expected if isinstance(normalized_expected, list) else [normalized_expected]
        return all(isinstance(normalized_answer, str) and item in normalized_answer for item in values)
    if isinstance(normalized_expected, dict):
        return normalized_answer == normalized_expected or normalized_answer in normalized_expected.values()
    return normalized_answer == normalized_expected


def _default_strategy(exercise_type: str) -> str:
    if exercise_type in {"multiple_choice", "choose_particle", "choose_verb_ending", "translation_selection", "true_false", "dialogue_continuation", "listen_and_choose"}:
        return "one_of"
    if exercise_type in {"sentence_reorder", "sentence_reordering", "listen_and_order"}:
        return "ordered_list"
    if exercise_type in {"match_pairs", "match_korean_translation", "match_word_usage", "listen_and_match"}:
        return "unordered_pairs"
    return "exact"


def _as_pair_set(value: Any) -> set[tuple[str, str]]:
    if isinstance(value, dict):
        return {(str(key), str(item)) for key, item in value.items()}
    if isinstance(value, list):
        pairs = set()
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                pairs.add((str(item[0]), str(item[1])))
            elif isinstance(item, dict) and {"left", "right"} <= set(item):
                pairs.add((str(item["left"]), str(item["right"])))
        return pairs
    return set()
