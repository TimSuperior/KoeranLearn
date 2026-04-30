from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base
from app.models.schema import Exercise, Lesson, Module, ReviewHistory, ReviewItem, User, utcnow
from app.services.review_service import build_review_overview


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_build_review_overview_groups_grammar_and_listening_review() -> None:
    db = _session()
    user = User(telegram_id="123", interface_language="en")
    module = Module(slug="module", course_id=1, title={"en": "Module"})
    lesson = Lesson(slug="lesson", module=module, title={"en": "Lesson"}, summary={"en": "Summary"}, explanation={"en": "Explain"})
    grammar_exercise = Exercise(
        lesson=lesson,
        slug="grammar-ex",
        exercise_type="choose_particle",
        prompt={"en": "Pick the particle."},
        answer_key={"value": "topic"},
        explanation={"en": "Particle drill."},
        difficulty="A0",
        topic="grammar",
        payload={},
    )
    listening_exercise = Exercise(
        lesson=lesson,
        slug="listen-ex",
        exercise_type="listen_and_choose",
        prompt={"en": "Listen and choose."},
        answer_key={"value": "water"},
        explanation={"en": "Listening drill."},
        difficulty="A0",
        topic="daily_life",
        payload={"audio_asset_url": "s3://audio/prompt.mp3"},
    )
    db.add_all([user, module, lesson, grammar_exercise, listening_exercise])
    db.flush()

    grammar_item = ReviewItem(
        user_id=user.id,
        item_type="exercise",
        item_id=grammar_exercise.id,
        mistake_count=3,
        mastery_status="mistake",
        next_review_at=utcnow() - timedelta(minutes=5),
    )
    listening_item = ReviewItem(
        user_id=user.id,
        item_type="exercise",
        item_id=listening_exercise.id,
        mistake_count=1,
        mastery_status="mistake",
        next_review_at=utcnow() - timedelta(minutes=1),
    )
    db.add_all([grammar_item, listening_item])
    db.flush()
    db.add_all(
        [
            ReviewHistory(review_item_id=grammar_item.id, user_id=user.id, answer={}, is_correct=False, quality=1),
            ReviewHistory(review_item_id=grammar_item.id, user_id=user.id, answer={}, is_correct=False, quality=1),
        ]
    )
    db.commit()

    overview = build_review_overview(db, user)

    grammar_labels = [item["label"] for item in overview["weak_grammar"]]
    session_modes = [item["mode"] for item in overview["guided_sessions"]]
    repeated_ids = [item["review_item_id"] for item in overview["repeated_mistakes"]]
    schedule = overview["schedule"]

    assert "Particles" in grammar_labels
    assert "grammar" in session_modes
    assert "listening" in session_modes
    assert grammar_item.id in repeated_ids
    assert schedule["due_now"] == 2
    assert schedule["mistake_queue"] == 2
    assert schedule["scheduled_total"] == 2


def test_build_review_overview_localizes_guided_sessions() -> None:
    db = _session()
    user = User(telegram_id="777", interface_language="ru")
    module = Module(slug="module-ru", course_id=1, title={"ru": "Module", "en": "Module"})
    lesson = Lesson(slug="lesson-ru", module=module, title={"ru": "Lesson", "en": "Lesson"}, summary={"ru": "Summary", "en": "Summary"}, explanation={"ru": "Explain", "en": "Explain"})
    exercise = Exercise(
        lesson=lesson,
        slug="exercise-ru",
        exercise_type="listen_and_choose",
        prompt={"ru": "Listen", "en": "Listen"},
        answer_key={"value": "a"},
        explanation={"ru": "Explain", "en": "Explain"},
        difficulty="A0",
        topic="daily_life",
        payload={"audio_asset_url": "s3://audio/prompt.mp3"},
    )
    db.add_all([user, module, lesson, exercise])
    db.flush()
    db.add(
        ReviewItem(
            user_id=user.id,
            item_type="exercise",
            item_id=exercise.id,
            mistake_count=1,
            mastery_status="mistake",
            next_review_at=utcnow() - timedelta(minutes=1),
        )
    )
    db.commit()

    overview = build_review_overview(db, user)

    assert overview["guided_sessions"][0]["title"] in {"Разбор ошибок", "Повтор по сроку"}


def test_build_review_overview_includes_upcoming_schedule_buckets() -> None:
    db = _session()
    user = User(telegram_id="555", interface_language="en")
    module = Module(slug="module-schedule", course_id=1, title={"en": "Module"})
    lesson = Lesson(slug="lesson-schedule", module=module, title={"en": "Lesson"}, summary={"en": "Summary"}, explanation={"en": "Explain"})
    exercise = Exercise(
        lesson=lesson,
        slug="exercise-schedule",
        exercise_type="multiple_choice",
        prompt={"en": "Choose the right answer."},
        answer_key={"value": "a"},
        explanation={"en": "Explain"},
        difficulty="A0",
        topic="daily_life",
        payload={},
    )
    db.add_all([user, module, lesson, exercise])
    db.flush()
    now = utcnow()
    db.add_all(
        [
            ReviewItem(user_id=user.id, item_type="exercise", item_id=exercise.id, mistake_count=0, mastery_status="learning", next_review_at=now - timedelta(minutes=5)),
            ReviewItem(user_id=user.id, item_type="exercise", item_id=exercise.id, mistake_count=0, mastery_status="learning", next_review_at=now + timedelta(hours=6)),
            ReviewItem(user_id=user.id, item_type="exercise", item_id=exercise.id, mistake_count=0, mastery_status="learning", next_review_at=now + timedelta(days=3)),
            ReviewItem(user_id=user.id, item_type="exercise", item_id=exercise.id, mistake_count=0, mastery_status="learning", next_review_at=now + timedelta(days=10)),
        ]
    )
    db.commit()

    overview = build_review_overview(db, user)
    schedule = overview["schedule"]

    assert schedule["due_now"] == 1
    assert schedule["next_24h"] == 1
    assert schedule["next_7d"] == 1
    assert schedule["scheduled_total"] == 4
    assert schedule["next_review_at"] is not None
