from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.schema import Exercise, GrammarPoint, ReviewHistory, ReviewItem, User, Vocabulary
from app.services.audio_service import exercise_has_audio_prompt, listening_exercise
from app.services.exercise_evaluator import GRAMMAR_EXERCISE_TYPES, canonical_exercise_type
from app.services.localization import normalize_language

REVIEW_COPY: dict[str, dict[str, dict[str, str]]] = {
    "guided.due.title": {
        "ru": {"text": "Повтор по сроку"},
        "uz": {"text": "Navbatdagi takror"},
        "en": {"text": "Due review"},
    },
    "guided.due.description": {
        "ru": {"text": "Сначала закройте то, что уже подошло по сроку, чтобы это не стало повторяющейся ошибкой."},
        "uz": {"text": "Avval muddati kelgan elementlarni yoping, shunda ular takroriy xatoga aylanmaydi."},
        "en": {"text": "Clear items that are already due before they become repeated mistakes."},
    },
    "guided.mistakes.title": {
        "ru": {"text": "Разбор ошибок"},
        "uz": {"text": "Xatolarni tuzatish"},
        "en": {"text": "Mistake repair"},
    },
    "guided.mistakes.description": {
        "ru": {"text": "Повторите именно те элементы, в которых вы ошибались, а не перечитывайте их пассивно."},
        "uz": {"text": "Passiv qayta o'qish o'rniga aynan xato qilgan elementlarni qayta ishlang."},
        "en": {"text": "Retry the items you have been missing instead of rereading them passively."},
    },
    "guided.grammar.title": {
        "ru": {"text": "Грамматические тренировки"},
        "uz": {"text": "Grammatika mashqlari"},
        "en": {"text": "Grammar drills"},
    },
    "guided.grammar.description": {
        "ru": {"text": "Практикуйте слабые частицы, окончания и формы предложения через активные задания."},
        "uz": {"text": "Zaif partikllar, qo'shimchalar va gap shakllarini faol mashq orqali mustahkamlang."},
        "en": {"text": "Practice weak particles, endings, and sentence forms with active prompts."},
    },
    "guided.listening.title": {
        "ru": {"text": "Повтор аудирования"},
        "uz": {"text": "Tinglab takrorlash"},
        "en": {"text": "Listening review"},
    },
    "guided.listening.description": {
        "ru": {"text": "Показываются только аудио-задания, где действительно есть воспроизводимый звук."},
        "uz": {"text": "Faqat haqiqatan ham tinglash mumkin bo'lgan audio topshiriqlar ko'rsatiladi."},
        "en": {"text": "Only shows listening prompts that actually have playable audio."},
    },
    "grammar.particles": {
        "ru": {"text": "Частицы"},
        "uz": {"text": "Partikllar"},
        "en": {"text": "Particles"},
    },
    "grammar.endings": {
        "ru": {"text": "Глагольные окончания"},
        "uz": {"text": "Fe'l qo'shimchalari"},
        "en": {"text": "Verb endings"},
    },
    "grammar.sentence_form": {
        "ru": {"text": "Форма предложения"},
        "uz": {"text": "Gap shakli"},
        "en": {"text": "Sentence form"},
    },
}


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
        exercise = (
            db.query(Exercise)
            .options(selectinload(Exercise.options), selectinload(Exercise.audio_assets))
            .filter(Exercise.id == item.item_id)
            .first()
        )
        if exercise:
            content = {
                "prompt": exercise.prompt,
                "exercise_type": exercise.exercise_type,
                "instructions": exercise.instructions,
                "payload": exercise.payload,
                "options": [{"id": option.id, "value": option.value, "label": option.label, "order_index": option.order_index} for option in exercise.options],
                "explanation": exercise.explanation,
                "difficulty": exercise.difficulty,
                "topic": exercise.topic,
                "answer_key": exercise.answer_key,
                "has_audio": exercise_has_audio_prompt(exercise),
            }
    elif item.item_type == "vocabulary":
        vocab = db.get(Vocabulary, item.item_id)
        if vocab:
            content = {"korean": vocab.korean, "translations": vocab.translations, "topic": vocab.topic, "difficulty": vocab.difficulty}
    elif item.item_type == "grammar":
        grammar = db.get(GrammarPoint, item.item_id)
        if grammar:
            content = {"pattern": grammar.korean_pattern, "title": grammar.title, "category": grammar.category, "difficulty": grammar.difficulty}

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


def build_review_overview(db: Session, user: User, limit: int = 5) -> dict[str, Any]:
    interface_language = normalize_language(getattr(user, "interface_language", None))
    explanation_language = normalize_language(getattr(getattr(user, "preferences", None), "explanation_language", None) or interface_language)
    items = db.query(ReviewItem).filter(ReviewItem.user_id == user.id).all()
    if not items:
        return {
            "weak_items": [],
            "weak_grammar": [],
            "repeated_mistakes": [],
            "exercise_type_breakdown": [],
            "guided_sessions": [],
        }

    exercise_ids = [item.item_id for item in items if item.item_type == "exercise"]
    exercises = (
        db.query(Exercise)
        .options(selectinload(Exercise.audio_assets), selectinload(Exercise.options), selectinload(Exercise.grammar_point), selectinload(Exercise.lesson))
        .filter(Exercise.id.in_(exercise_ids))
        .all()
        if exercise_ids
        else []
    )
    exercise_map = {exercise.id: exercise for exercise in exercises}

    history_rows = (
        db.query(ReviewHistory)
        .filter(ReviewHistory.user_id == user.id, ReviewHistory.review_item_id.in_([item.id for item in items]))
        .order_by(ReviewHistory.created_at.desc())
        .all()
        if items
        else []
    )
    recent_history: dict[int, list[ReviewHistory]] = {}
    for row in history_rows:
        recent_history.setdefault(row.review_item_id, [])
        if len(recent_history[row.review_item_id]) < 3:
            recent_history[row.review_item_id].append(row)

    weak_items = [
        _weak_item_payload(item, exercise_map.get(item.item_id), explanation_language)
        for item in sorted(items, key=lambda row: (row.mistake_count, row.next_review_at), reverse=True)
        if item.mistake_count > 0
    ][:limit]

    grammar_buckets: dict[str, dict[str, Any]] = {}
    for item in items:
        if item.item_type != "exercise" or item.mistake_count <= 0:
            continue
        exercise = exercise_map.get(item.item_id)
        if not exercise:
            continue
        bucket_key, label = _grammar_bucket(exercise, explanation_language)
        if not bucket_key:
            continue
        bucket = grammar_buckets.setdefault(bucket_key, {"key": bucket_key, "label": label, "mistakes": 0, "items": 0})
        bucket["mistakes"] += item.mistake_count
        bucket["items"] += 1

    repeated_mistakes = []
    for item in sorted(items, key=lambda row: row.mistake_count, reverse=True):
        if item.mistake_count < 2:
            continue
        if not _is_repeated_mistake(item, recent_history.get(item.id, [])):
            continue
        repeated_mistakes.append(_weak_item_payload(item, exercise_map.get(item.item_id), explanation_language))
        if len(repeated_mistakes) >= limit:
            break

    breakdown: dict[str, int] = {}
    due_exercise_items = 0
    mistake_exercise_items = 0
    grammar_focus_items = 0
    listening_items = 0
    now = datetime.now(timezone.utc)
    for item in items:
        if item.item_type != "exercise":
            continue
        exercise = exercise_map.get(item.item_id)
        if not exercise:
            continue
        exercise_type = canonical_exercise_type(exercise.exercise_type)
        if item.mistake_count > 0 or item.next_review_at <= now:
            breakdown[exercise_type] = breakdown.get(exercise_type, 0) + 1
        if item.next_review_at <= now:
            due_exercise_items += 1
        if item.mistake_count > 0:
            mistake_exercise_items += 1
        if exercise_type in GRAMMAR_EXERCISE_TYPES and item.mistake_count > 0:
            grammar_focus_items += 1
        if exercise_has_audio_prompt(exercise) and listening_exercise(exercise) and (item.mistake_count > 0 or item.next_review_at <= now):
            listening_items += 1

    guided_sessions = []
    if due_exercise_items:
        guided_sessions.append(
            {
                "mode": "due",
                "title": _review_text("guided.due.title", interface_language),
                "description": _review_text("guided.due.description", interface_language),
                "item_count": due_exercise_items,
                "size": min(max(due_exercise_items, 5), 10),
                "tone": "accent",
            }
        )
    if mistake_exercise_items:
        guided_sessions.append(
            {
                "mode": "mistakes",
                "title": _review_text("guided.mistakes.title", interface_language),
                "description": _review_text("guided.mistakes.description", interface_language),
                "item_count": mistake_exercise_items,
                "size": min(max(mistake_exercise_items, 5), 10),
                "tone": "danger",
            }
        )
    if grammar_focus_items:
        guided_sessions.append(
            {
                "mode": "grammar",
                "title": _review_text("guided.grammar.title", interface_language),
                "description": _review_text("guided.grammar.description", interface_language),
                "item_count": grammar_focus_items,
                "size": min(max(grammar_focus_items, 5), 10),
                "tone": "warning",
            }
        )
    if listening_items:
        guided_sessions.append(
            {
                "mode": "listening",
                "title": _review_text("guided.listening.title", interface_language),
                "description": _review_text("guided.listening.description", interface_language),
                "item_count": listening_items,
                "size": min(max(listening_items, 5), 10),
                "tone": "success",
            }
        )

    return {
        "weak_items": weak_items,
        "weak_grammar": sorted(grammar_buckets.values(), key=lambda row: (row["mistakes"], row["items"]), reverse=True)[:limit],
        "repeated_mistakes": repeated_mistakes,
        "exercise_type_breakdown": [{"exercise_type": key, "count": value} for key, value in sorted(breakdown.items(), key=lambda row: row[1], reverse=True)],
        "guided_sessions": guided_sessions,
    }


def _weak_item_payload(item: ReviewItem, exercise: Exercise | None, language: str) -> dict[str, Any]:
    label = f"{item.item_type} #{item.item_id}"
    exercise_type = None
    difficulty = None
    topic = None
    has_audio = False
    if exercise:
        exercise_type = canonical_exercise_type(exercise.exercise_type)
        difficulty = exercise.difficulty
        topic = exercise.topic
        label = _localized_text(exercise.prompt, language, exercise.slug)
        has_audio = exercise_has_audio_prompt(exercise)
    return {
        "review_item_id": item.id,
        "item_type": item.item_type,
        "item_id": item.item_id,
        "label": label,
        "exercise_type": exercise_type,
        "difficulty": difficulty,
        "topic": topic,
        "mistake_count": item.mistake_count,
        "mastery_status": item.mastery_status,
        "next_review_at": item.next_review_at,
        "has_audio": has_audio,
    }


def _grammar_bucket(exercise: Exercise, language: str) -> tuple[str | None, str | None]:
    if exercise.grammar_point:
        label = _localized_text(exercise.grammar_point.title, language, exercise.grammar_point.korean_pattern)
        return f"grammar:{exercise.grammar_point.id}", str(label)

    exercise_type = canonical_exercise_type(exercise.exercise_type)
    if exercise_type == "choose_particle":
        return "grammar:particles", _review_text("grammar.particles", language)
    if exercise_type == "choose_verb_ending":
        return "grammar:endings", _review_text("grammar.endings", language)
    if exercise_type in {"fill_blank", "sentence_reorder"}:
        return "grammar:sentence_form", _review_text("grammar.sentence_form", language)
    if exercise.lesson and exercise.lesson.grammar_category:
        return f"grammar:{exercise.lesson.grammar_category}", str(exercise.lesson.grammar_category).replace("_", " ").title()
    return None, None


def _is_repeated_mistake(item: ReviewItem, history: list[ReviewHistory]) -> bool:
    if item.mistake_count >= 3:
        return True
    return len(history) >= 2 and all(not row.is_correct for row in history[:2])


def _localized_text(value: Any, language: str, fallback: str = "") -> str:
    if isinstance(value, dict):
        return str(value.get(language) or value.get("en") or value.get("ru") or value.get("uz") or fallback)
    return fallback


def _review_text(key: str, language: str) -> str:
    entry = REVIEW_COPY.get(key) or {}
    current = entry.get(language) or entry.get("en") or {}
    return str(current.get("text") or key)
