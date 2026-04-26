from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.schema import Exercise, GrammarPoint, ReviewHistory, ReviewItem, User, Vocabulary


def get_or_create_review_item(
    db: Session,
    user: User,
    item_type: str,
    item_id: int,
    source_lesson_id: int | None = None,
    wrong: bool = False,
) -> ReviewItem:
    item = (
        db.query(ReviewItem)
        .filter(ReviewItem.user_id == user.id, ReviewItem.item_type == item_type, ReviewItem.item_id == item_id)
        .first()
    )
    if item:
        if wrong:
            item.mistake_count += 1
            item.next_review_at = datetime.now(timezone.utc) + timedelta(minutes=10)
            item.mastery_status = "mistake"
        return item

    item = ReviewItem(
        user_id=user.id,
        item_type=item_type,
        item_id=item_id,
        source_lesson_id=source_lesson_id,
        next_review_at=datetime.now(timezone.utc) + (timedelta(minutes=10) if wrong else timedelta(days=1)),
        mastery_status="mistake" if wrong else "learning",
        mistake_count=1 if wrong else 0,
    )
    db.add(item)
    return item


def due_review_items(db: Session, user: User, limit: int = 20, mistakes_only: bool = False) -> list[dict[str, Any]]:
    query = db.query(ReviewItem).filter(ReviewItem.user_id == user.id)
    if mistakes_only:
        query = query.filter(ReviewItem.mistake_count > 0)
    else:
        query = query.filter(ReviewItem.next_review_at <= datetime.now(timezone.utc))
    rows = query.order_by(ReviewItem.next_review_at).limit(limit).all()
    return [{**_serialize_review_item(db, row), "id": row.id} for row in rows]


def _serialize_review_item(db: Session, item: ReviewItem) -> dict[str, Any]:
    content: dict[str, Any] = {}
    if item.item_type == "exercise":
        exercise = db.get(Exercise, item.item_id)
        if exercise:
            content = {
                "prompt": exercise.prompt,
                "exercise_type": exercise.exercise_type,
                "topic": exercise.topic,
                "answer_key": exercise.answer_key,
            }
    elif item.item_type == "vocabulary":
        vocab = db.get(Vocabulary, item.item_id)
        if vocab:
            content = {"korean": vocab.korean, "translations": vocab.translations, "topic": vocab.topic}
    elif item.item_type == "grammar":
        grammar = db.get(GrammarPoint, item.item_id)
        if grammar:
            content = {"pattern": grammar.korean_pattern, "title": grammar.title, "category": grammar.category}

    return {
        "item_type": item.item_type,
        "item_id": item.item_id,
        "source_lesson_id": item.source_lesson_id,
        "ease_score": item.ease_score,
        "interval_days": item.interval_days,
        "repetitions": item.repetitions,
        "next_review_at": item.next_review_at,
        "mastery_status": item.mastery_status,
        "mistake_count": item.mistake_count,
        "content": content,
    }


def submit_review_result(db: Session, user: User, review_item_id: int, answer: dict, is_correct: bool, quality: int) -> ReviewItem:
    item = db.get(ReviewItem, review_item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found")

    previous_interval = item.interval_days
    if is_correct and quality >= 3:
        item.repetitions += 1
        if item.repetitions == 1:
            item.interval_days = 1
        elif item.repetitions == 2:
            item.interval_days = 3
        else:
            item.interval_days = max(1, round(item.interval_days * item.ease_score))
        item.ease_score = max(1.3, item.ease_score + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        item.mastery_status = "reviewing" if item.repetitions < 4 else "mastered"
        item.next_review_at = datetime.now(timezone.utc) + timedelta(days=item.interval_days)
    else:
        item.repetitions = 0
        item.interval_days = 0
        item.ease_score = max(1.3, item.ease_score - 0.2)
        item.mistake_count += 1
        item.mastery_status = "mistake"
        item.next_review_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    db.add(
        ReviewHistory(
            review_item_id=item.id,
            user_id=user.id,
            answer=answer,
            is_correct=is_correct,
            quality=quality,
            previous_interval_days=previous_interval,
            next_interval_days=item.interval_days,
        )
    )
    db.commit()
    db.refresh(item)
    return item
