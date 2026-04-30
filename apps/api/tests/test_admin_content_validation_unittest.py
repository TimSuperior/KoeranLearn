import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base
from app.models import schema  # noqa: F401
from app.models.schema import Course, Exercise, ExerciseOption, LearningPath, Module
from app.services.admin_content_service import validate_current_entity
from app.services.content_validation import validate_entity_payload


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()


class AdminContentValidationTests(unittest.TestCase):
    def test_lesson_validation_flags_unpublished_module_and_block_dependencies(self) -> None:
        db = make_session()
        try:
            path = LearningPath(slug="path-1", title={"ru": "A", "uz": "A", "en": "A"}, status="published")
            db.add(path)
            db.flush()
            course = Course(slug="course-1", path_id=path.id, title={"ru": "A", "uz": "A", "en": "A"}, status="published")
            db.add(course)
            db.flush()
            module = Module(slug="module-1", course_id=course.id, title={"ru": "A", "uz": "A", "en": "A"}, status="draft")
            exercise = Exercise(
                slug="exercise-1",
                exercise_type="multiple_choice",
                prompt={"ru": "Q", "uz": "Q", "en": "Q"},
                answer_key={"value": "a"},
                answer_validation={"strategy": "one_of"},
                status="draft",
            )
            db.add_all([module, exercise])
            db.commit()

            result = validate_entity_payload(
                db,
                "lessons",
                {
                    "slug": "lesson-1",
                    "module_id": module.id,
                    "title": {"ru": "L", "uz": "L", "en": "L"},
                    "objectives": ["Goal"],
                    "status": "draft",
                },
                children={
                    "blocks": [
                        {
                            "block_type": "exercise",
                            "title": {"ru": "B", "uz": "B", "en": "B"},
                            "body": {"ru": "Body", "uz": "Body", "en": "Body"},
                            "payload": {"exercise_id": exercise.id},
                            "status": "draft",
                        }
                    ]
                },
            )

            self.assertTrue(any(issue.field == "module_id" and issue.code == "unpublished_linked_content" for issue in result.issues))
            self.assertTrue(any(issue.field == "blocks[1].payload.exercise_id" and issue.code == "unpublished_linked_content" for issue in result.issues))
        finally:
            db.close()

    def test_listening_exercise_requires_published_audio_asset(self) -> None:
        db = make_session()
        try:
            exercise = Exercise(
                slug="listen-1",
                exercise_type="listen_and_choose",
                prompt={"ru": "Q", "uz": "Q", "en": "Q"},
                answer_key={"value": "a"},
                answer_validation={"strategy": "one_of"},
                status="draft",
            )
            db.add(exercise)
            db.flush()
            db.add_all(
                [
                    ExerciseOption(exercise_id=exercise.id, value="a", label={"ru": "A", "uz": "A", "en": "A"}, is_correct=True),
                    ExerciseOption(exercise_id=exercise.id, value="b", label={"ru": "B", "uz": "B", "en": "B"}, is_correct=False),
                ]
            )
            db.commit()

            result = validate_current_entity(db, "exercises", exercise.id)

            self.assertTrue(any(issue.code == "missing_audio_reference" for issue in result.issues))
        finally:
            db.close()

    def test_grammar_validation_warns_when_transfer_notes_are_identical(self) -> None:
        db = make_session()
        try:
            result = validate_entity_payload(
                db,
                "grammar",
                {
                    "slug": "grammar-1",
                    "korean_pattern": "-은/는",
                    "title": {"ru": "Тема", "uz": "Mavzu", "en": "Topic"},
                    "explanation": {"ru": "Объяснение", "uz": "Izoh", "en": "Explanation"},
                    "transfer_notes": {
                        "ru": ["same note"],
                        "uz": ["same note"],
                        "en": ["same note"],
                    },
                    "common_errors": {
                        "ru": ["same error"],
                        "uz": ["same error"],
                        "en": ["same error"],
                    },
                },
            )

            warning_fields = {(issue.code, issue.field) for issue in result.issues}
            self.assertIn(("localized_transfer_needs_adaptation", "transfer_notes"), warning_fields)
            self.assertIn(("localized_transfer_needs_adaptation", "common_errors"), warning_fields)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
