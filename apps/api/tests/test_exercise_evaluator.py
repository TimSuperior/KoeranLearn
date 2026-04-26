from app.models.schema import Exercise
from app.services.exercise_evaluator import evaluate_exercise


def test_sentence_reorder_uses_ordered_list_strategy() -> None:
    exercise = Exercise(
        exercise_type="sentence_reorder",
        prompt={"en": "Reorder"},
        answer_key={"value": ["저는", "김치를", "먹어요"]},
        answer_validation={"strategy": "ordered_list"},
    )

    assert evaluate_exercise(exercise, ["저는", "김치를", "먹어요"])
    assert not evaluate_exercise(exercise, ["김치를", "저는", "먹어요"])


def test_text_answers_are_normalized() -> None:
    exercise = Exercise(
        exercise_type="fill_blank",
        prompt={"en": "Blank"},
        answer_key={"value": "안녕하세요"},
        answer_validation={"strategy": "one_of"},
    )

    assert evaluate_exercise(exercise, "  안녕하세요  ")
