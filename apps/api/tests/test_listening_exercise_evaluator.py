from app.models.schema import Exercise
from app.services.exercise_evaluator import evaluate_exercise


def test_listen_and_order_uses_ordered_list_strategy() -> None:
    exercise = Exercise(
        exercise_type="listen_and_order",
        prompt={"en": "Order what you hear"},
        answer_key={"value": ["a", "b", "c"]},
        answer_validation={"strategy": "ordered_list"},
    )

    assert evaluate_exercise(exercise, ["a", "b", "c"])
    assert not evaluate_exercise(exercise, ["b", "a", "c"])


def test_listen_and_match_uses_unordered_pairs_strategy() -> None:
    exercise = Exercise(
        exercise_type="listen_and_match",
        prompt={"en": "Match what you hear"},
        answer_key={"value": {"alpha": "A", "beta": "B"}},
        answer_validation={"strategy": "unordered_pairs"},
    )

    assert evaluate_exercise(exercise, {"beta": "B", "alpha": "A"})
    assert not evaluate_exercise(exercise, {"beta": "A", "alpha": "B"})
