from datetime import datetime, timezone

from app.models.schema import ReviewItem, User
from app.services.review_service import submit_review_result


class FakeDb:
    def __init__(self, item: ReviewItem) -> None:
        self.item = item
        self.added = []

    def get(self, model, item_id):  # noqa: ANN001
        return self.item if model is ReviewItem and item_id == self.item.id else None

    def add(self, value):  # noqa: ANN001
        self.added.append(value)

    def commit(self):
        return None

    def refresh(self, value):  # noqa: ANN001
        return None


def test_srs_wrong_answer_returns_soon() -> None:
    user = User(id=1, telegram_id="10001")
    item = ReviewItem(
        id=10,
        user_id=1,
        item_type="exercise",
        item_id=1,
        ease_score=2.5,
        interval_days=3,
        repetitions=2,
        next_review_at=datetime.now(timezone.utc),
    )
    db = FakeDb(item)

    updated = submit_review_result(db, user, 10, {}, False, 1)

    assert updated.interval_days == 0
    assert updated.mastery_status == "mistake"
    assert updated.mistake_count == 1
