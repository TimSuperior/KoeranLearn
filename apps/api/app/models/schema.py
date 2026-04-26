from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AccessControlledMixin:
    access_state: Mapped[str] = mapped_column(String(32), default="free", index=True)
    resolved_access_state: Mapped[str] = mapped_column(String(32), default="free", index=True)
    created_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    updated_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)


lesson_vocabulary_links = Table(
    "lesson_vocabulary_links",
    Base.metadata,
    Column("lesson_id", ForeignKey("lessons.id"), primary_key=True),
    Column("vocabulary_id", ForeignKey("vocabulary.id"), primary_key=True),
)


lesson_grammar_links = Table(
    "lesson_grammar_links",
    Base.metadata,
    Column("lesson_id", ForeignKey("lessons.id"), primary_key=True),
    Column("grammar_point_id", ForeignKey("grammar_points.id"), primary_key=True),
)


lesson_scenario_links = Table(
    "lesson_scenario_links",
    Base.metadata,
    Column("lesson_id", ForeignKey("lessons.id"), primary_key=True),
    Column("scenario_id", ForeignKey("scenarios.id"), primary_key=True),
)


scenario_vocabulary_links = Table(
    "scenario_vocabulary_links",
    Base.metadata,
    Column("scenario_id", ForeignKey("scenarios.id"), primary_key=True),
    Column("vocabulary_id", ForeignKey("vocabulary.id"), primary_key=True),
)


scenario_grammar_links = Table(
    "scenario_grammar_links",
    Base.metadata,
    Column("scenario_id", ForeignKey("scenarios.id"), primary_key=True),
    Column("grammar_point_id", ForeignKey("grammar_points.id"), primary_key=True),
)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    interface_language: Mapped[str] = mapped_column(String(8), default="en")
    role: Mapped[str] = mapped_column(String(32), default="user", index=True)
    is_onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    streak_count: Mapped[int] = mapped_column(Integer, default=0)
    last_study_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    preferences: Mapped["UserPreference"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    level: Mapped[str] = mapped_column(String(64), default="complete_beginner")
    daily_minutes: Mapped[int] = mapped_column(Integer, default=5)
    learning_style: Mapped[str] = mapped_column(String(64), default="mixed")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Seoul")

    user: Mapped[User] = relationship(back_populates="profile")


class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    explanation_language: Mapped[str] = mapped_column(String(8), default="en")
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_time: Mapped[str] = mapped_column(String(8), default="19:00")
    quiet_hours: Mapped[dict] = mapped_column(JSON, default=lambda: {"start": "22:00", "end": "08:00"})
    difficulty: Mapped[str] = mapped_column(String(32), default="normal")

    user: Mapped[User] = relationship(back_populates="preferences")


class UserGoal(Base, TimestampMixin):
    __tablename__ = "user_goals"
    __table_args__ = (UniqueConstraint("user_id", "goal", name="uq_user_goal"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    goal: Mapped[str] = mapped_column(String(64), index=True)


class LearningPath(Base, TimestampMixin, AccessControlledMixin):
    __tablename__ = "learning_paths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[dict] = mapped_column(JSON)
    description: Mapped[dict] = mapped_column(JSON, default=dict)
    target_goal: Mapped[str] = mapped_column(String(64), default="korean_from_zero")
    level: Mapped[str] = mapped_column(String(32), default="A0")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    courses: Mapped[list["Course"]] = relationship(back_populates="path")


class UserPathProgress(Base, TimestampMixin):
    __tablename__ = "user_path_progress"
    __table_args__ = (UniqueConstraint("user_id", "path_id", name="uq_user_path"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("learning_paths.id"), index=True)
    current_module_id: Mapped[int | None] = mapped_column(ForeignKey("modules.id"), nullable=True)
    current_lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"), nullable=True)
    completed_lessons: Mapped[int] = mapped_column(Integer, default=0)
    percent_complete: Mapped[float] = mapped_column(Float, default=0.0)


class Course(Base, TimestampMixin, AccessControlledMixin):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    path_id: Mapped[int | None] = mapped_column(ForeignKey("learning_paths.id"), nullable=True)
    title: Mapped[dict] = mapped_column(JSON)
    description: Mapped[dict] = mapped_column(JSON, default=dict)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    path: Mapped[LearningPath | None] = relationship(back_populates="courses")
    modules: Mapped[list["Module"]] = relationship(back_populates="course")


class Module(Base, TimestampMixin, AccessControlledMixin):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[dict] = mapped_column(JSON)
    description: Mapped[dict] = mapped_column(JSON, default=dict)
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)
    difficulty: Mapped[str] = mapped_column(String(32), default="A0")
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=20)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    course: Mapped[Course] = relationship(back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="module")


class Lesson(Base, TimestampMixin, AccessControlledMixin):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), index=True)
    title: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    objectives: Mapped[list] = mapped_column(JSON, default=list)
    korean_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    transfer_notes: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    difficulty: Mapped[str] = mapped_column(String(32), default="A0")
    topic: Mapped[str] = mapped_column(String(128), default="general")
    grammar_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    politeness_level: Mapped[str] = mapped_column(String(64), default="polite_informal")
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=5)
    cover_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    audience_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    prerequisite_lesson_ids: Mapped[list] = mapped_column(JSON, default=list)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    review_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    module: Mapped[Module] = relationship(back_populates="lessons")
    exercises: Mapped[list["Exercise"]] = relationship(back_populates="lesson")
    blocks: Mapped[list["LessonBlock"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")
    assets: Mapped[list["LessonAsset"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")
    audio_assets: Mapped[list["AudioAsset"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")
    related_vocabulary: Mapped[list["Vocabulary"]] = relationship(secondary=lesson_vocabulary_links, back_populates="related_lessons")
    related_grammar: Mapped[list["GrammarPoint"]] = relationship(secondary=lesson_grammar_links, back_populates="related_lessons")
    related_scenarios: Mapped[list["Scenario"]] = relationship(secondary=lesson_scenario_links, back_populates="related_lessons")

    @property
    def has_audio(self) -> bool:
        if any(not asset.is_deleted and asset.status == "published" and asset.compliance_state == "active" for asset in self.audio_assets):
            return True
        if any(asset.url for asset in self.assets if "audio" in (asset.asset_type or "").lower()):
            return True
        if any((block.payload or {}).get(key) for block in self.blocks for key in ("audio_url", "audio_asset_url")):
            return True
        return any((exercise.payload or {}).get(key) for exercise in self.exercises for key in ("audio_url", "audio_asset_url"))


class LessonBlock(Base, TimestampMixin):
    __tablename__ = "lesson_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    block_type: Mapped[str] = mapped_column(String(64), default="text", index=True)
    title: Mapped[dict] = mapped_column(JSON, default=dict)
    body: Mapped[dict] = mapped_column(JSON, default=dict)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    lesson: Mapped[Lesson] = relationship(back_populates="blocks")
    audio_assets: Mapped[list["AudioAsset"]] = relationship(back_populates="lesson_block", cascade="all, delete-orphan")


class LessonProgress(Base, TimestampMixin):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="not_started")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Exercise(Base, TimestampMixin, AccessControlledMixin):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"), nullable=True, index=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    exercise_type: Mapped[str] = mapped_column(String(64), index=True)
    prompt: Mapped[dict] = mapped_column(JSON)
    instructions: Mapped[dict] = mapped_column(JSON, default=dict)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    answer_key: Mapped[dict] = mapped_column(JSON, default=dict)
    answer_validation: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    difficulty: Mapped[str] = mapped_column(String(32), default="A0")
    topic: Mapped[str] = mapped_column(String(128), default="general")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    grammar_point_id: Mapped[int | None] = mapped_column(ForeignKey("grammar_points.id"), nullable=True)
    vocabulary_id: Mapped[int | None] = mapped_column(ForeignKey("vocabulary.id"), nullable=True)
    politeness_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    lesson: Mapped[Lesson | None] = relationship(back_populates="exercises")
    options: Mapped[list["ExerciseOption"]] = relationship(back_populates="exercise", cascade="all, delete-orphan")
    grammar_point: Mapped["GrammarPoint | None"] = relationship(back_populates="exercises")
    vocabulary: Mapped["Vocabulary | None"] = relationship(back_populates="exercises")
    audio_assets: Mapped[list["AudioAsset"]] = relationship(back_populates="exercise", cascade="all, delete-orphan")


class ExerciseOption(Base, TimestampMixin):
    __tablename__ = "exercise_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    value: Mapped[str] = mapped_column(String(255))
    label: Mapped[dict] = mapped_column(JSON)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    exercise: Mapped[Exercise] = relationship(back_populates="options")


class Vocabulary(Base, TimestampMixin, AccessControlledMixin):
    __tablename__ = "vocabulary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    korean: Mapped[str] = mapped_column(String(255), index=True)
    reading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    translations: Mapped[dict] = mapped_column(JSON)
    usage_notes: Mapped[dict] = mapped_column(JSON, default=dict)
    topic: Mapped[str] = mapped_column(String(128), default="general", index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    difficulty: Mapped[str] = mapped_column(String(32), default="A0")
    politeness_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    example_sentences: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[dict] = mapped_column(JSON, default=dict)
    variants: Mapped[list] = mapped_column(JSON, default=list)
    audio_asset_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    review_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    related_lessons: Mapped[list[Lesson]] = relationship(secondary=lesson_vocabulary_links, back_populates="related_vocabulary")
    related_scenarios: Mapped[list["Scenario"]] = relationship(secondary=scenario_vocabulary_links, back_populates="related_vocabulary")
    exercises: Mapped[list[Exercise]] = relationship(back_populates="vocabulary")
    example_sentence_records: Mapped[list["ExampleSentence"]] = relationship(back_populates="vocabulary")
    audio_assets: Mapped[list["AudioAsset"]] = relationship(back_populates="vocabulary", cascade="all, delete-orphan")


class GrammarPoint(Base, TimestampMixin, AccessControlledMixin):
    __tablename__ = "grammar_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    korean_pattern: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[dict] = mapped_column(JSON)
    explanation: Mapped[dict] = mapped_column(JSON)
    usage_notes: Mapped[dict] = mapped_column(JSON, default=dict)
    transfer_notes: Mapped[dict] = mapped_column(JSON, default=dict)
    common_errors: Mapped[dict] = mapped_column(JSON, default=dict)
    natural_alternatives: Mapped[list] = mapped_column(JSON, default=list)
    category: Mapped[str] = mapped_column(String(128), default="grammar", index=True)
    difficulty: Mapped[str] = mapped_column(String(32), default="A0")
    politeness_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    related_lessons: Mapped[list[Lesson]] = relationship(secondary=lesson_grammar_links, back_populates="related_grammar")
    related_scenarios: Mapped[list["Scenario"]] = relationship(secondary=scenario_grammar_links, back_populates="related_grammar")
    exercises: Mapped[list[Exercise]] = relationship(back_populates="grammar_point")
    example_sentence_records: Mapped[list["ExampleSentence"]] = relationship(back_populates="grammar_point")


class Scenario(Base, TimestampMixin, AccessControlledMixin):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[dict] = mapped_column(JSON)
    description: Mapped[dict] = mapped_column(JSON, default=dict)
    context_labels: Mapped[list] = mapped_column(JSON, default=list)
    roles: Mapped[list] = mapped_column(JSON, default=list)
    target_grammar_ids: Mapped[list] = mapped_column(JSON, default=list)
    target_vocabulary_ids: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    audience_languages: Mapped[list] = mapped_column(JSON, default=lambda: ["ru", "uz", "en"])
    audience_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    topic: Mapped[str] = mapped_column(String(128), default="daily_life")
    difficulty: Mapped[str] = mapped_column(String(32), default="A0")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    dialogues: Mapped[list["Dialogue"]] = relationship(back_populates="scenario")
    related_lessons: Mapped[list[Lesson]] = relationship(secondary=lesson_scenario_links, back_populates="related_scenarios")
    related_vocabulary: Mapped[list["Vocabulary"]] = relationship(secondary=scenario_vocabulary_links, back_populates="related_scenarios")
    related_grammar: Mapped[list["GrammarPoint"]] = relationship(secondary=scenario_grammar_links, back_populates="related_scenarios")
    audio_assets: Mapped[list["AudioAsset"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")


class Dialogue(Base, TimestampMixin, AccessControlledMixin):
    __tablename__ = "dialogues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), index=True)
    title: Mapped[dict] = mapped_column(JSON)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    lines: Mapped[list] = mapped_column(JSON)
    checks: Mapped[list] = mapped_column(JSON, default=list)
    useful_expressions: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    politeness_level: Mapped[str] = mapped_column(String(64), default="polite_informal")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    scenario: Mapped[Scenario] = relationship(back_populates="dialogues")
    dialogue_lines: Mapped[list["DialogueLine"]] = relationship(back_populates="dialogue", cascade="all, delete-orphan")


class DialogueLine(Base, TimestampMixin):
    __tablename__ = "dialogue_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dialogue_id: Mapped[int] = mapped_column(ForeignKey("dialogues.id"), index=True)
    speaker: Mapped[str] = mapped_column(String(128))
    korean: Mapped[str] = mapped_column(Text)
    translations: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[dict] = mapped_column(JSON, default=dict)
    audio_asset_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reveal_mode: Mapped[str] = mapped_column(String(32), default="toggle")
    highlighted_expressions: Mapped[list] = mapped_column(JSON, default=list)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_useful_expression: Mapped[bool] = mapped_column(Boolean, default=False)

    dialogue: Mapped[Dialogue] = relationship(back_populates="dialogue_lines")
    audio_assets: Mapped[list["AudioAsset"]] = relationship(back_populates="dialogue_line", cascade="all, delete-orphan")


class ExampleSentence(Base, TimestampMixin, AccessControlledMixin):
    __tablename__ = "example_sentences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    korean: Mapped[str] = mapped_column(Text)
    translations: Mapped[dict] = mapped_column(JSON)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    grammar_point_id: Mapped[int | None] = mapped_column(ForeignKey("grammar_points.id"), nullable=True)
    vocabulary_id: Mapped[int | None] = mapped_column(ForeignKey("vocabulary.id"), nullable=True)
    context_labels: Mapped[list] = mapped_column(JSON, default=list)
    politeness_level: Mapped[str] = mapped_column(String(64), default="polite_informal")
    register: Mapped[str] = mapped_column(String(64), default="spoken")
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    grammar_point: Mapped[GrammarPoint | None] = relationship(back_populates="example_sentence_records")
    vocabulary: Mapped[Vocabulary | None] = relationship(back_populates="example_sentence_records")
    audio_assets: Mapped[list["AudioAsset"]] = relationship(back_populates="example_sentence", cascade="all, delete-orphan")


class LessonAsset(Base, TimestampMixin):
    __tablename__ = "lesson_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(64))
    url: Mapped[str] = mapped_column(String(500))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    lesson: Mapped[Lesson | None] = relationship(back_populates="assets")


class AudioAsset(Base, TimestampMixin):
    __tablename__ = "audio_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=lambda: uuid4().hex)
    label: Mapped[dict] = mapped_column(JSON, default=dict)
    attachment_role: Mapped[str] = mapped_column(String(64), default="general", index=True)
    variant: Mapped[str] = mapped_column(String(32), default="default", index=True)
    source_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    storage_backend: Mapped[str] = mapped_column(String(32), default="local")
    storage_key: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(128), default="audio/mpeg")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    transcript: Mapped[dict] = mapped_column(JSON, default=dict)
    transcript_mode: Mapped[str] = mapped_column(String(32), default="toggle")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    premium_only: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    compliance_state: Mapped[str] = mapped_column(String(32), default="active", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cache_version: Mapped[int] = mapped_column(Integer, default=1)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    updated_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)

    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"), nullable=True, index=True)
    lesson_block_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_blocks.id"), nullable=True, index=True)
    exercise_id: Mapped[int | None] = mapped_column(ForeignKey("exercises.id"), nullable=True, index=True)
    vocabulary_id: Mapped[int | None] = mapped_column(ForeignKey("vocabulary.id"), nullable=True, index=True)
    example_sentence_id: Mapped[int | None] = mapped_column(ForeignKey("example_sentences.id"), nullable=True, index=True)
    dialogue_line_id: Mapped[int | None] = mapped_column(ForeignKey("dialogue_lines.id"), nullable=True, index=True)
    scenario_id: Mapped[int | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)

    lesson: Mapped[Lesson | None] = relationship(back_populates="audio_assets")
    lesson_block: Mapped[LessonBlock | None] = relationship(back_populates="audio_assets")
    exercise: Mapped[Exercise | None] = relationship(back_populates="audio_assets")
    vocabulary: Mapped[Vocabulary | None] = relationship(back_populates="audio_assets")
    example_sentence: Mapped[ExampleSentence | None] = relationship(back_populates="audio_assets")
    dialogue_line: Mapped[DialogueLine | None] = relationship(back_populates="audio_assets")
    scenario: Mapped[Scenario | None] = relationship(back_populates="audio_assets")


class ReviewItem(Base, TimestampMixin):
    __tablename__ = "review_items"
    __table_args__ = (UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_review_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(64), index=True)
    item_id: Mapped[int] = mapped_column(Integer, index=True)
    source_lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"), nullable=True)
    ease_score: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    mastery_status: Mapped[str] = mapped_column(String(32), default="learning")
    mistake_count: Mapped[int] = mapped_column(Integer, default=0)


class ReviewHistory(Base, TimestampMixin):
    __tablename__ = "review_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_item_id: Mapped[int] = mapped_column(ForeignKey("review_items.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    answer: Mapped[dict] = mapped_column(JSON, default=dict)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    quality: Mapped[int] = mapped_column(Integer, default=3)
    previous_interval_days: Mapped[int] = mapped_column(Integer, default=0)
    next_interval_days: Mapped[int] = mapped_column(Integer, default=1)


class WritingSubmission(Base, TimestampMixin):
    __tablename__ = "writing_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    original_text: Mapped[str] = mapped_column(Text)
    corrected_text: Mapped[str] = mapped_column(Text)
    natural_text: Mapped[str] = mapped_column(Text)
    feedback: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    provider: Mapped[str] = mapped_column(String(64), default="deterministic")


class Achievement(Base, TimestampMixin):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True)
    title: Mapped[dict] = mapped_column(JSON)
    description: Mapped[dict] = mapped_column(JSON, default=dict)
    trigger: Mapped[dict] = mapped_column(JSON, default=dict)
    xp_reward: Mapped[int] = mapped_column(Integer, default=0)


class UserAchievement(Base, TimestampMixin):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id"), index=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PremiumPack(Base, TimestampMixin):
    __tablename__ = "premium_packs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True)
    title: Mapped[dict] = mapped_column(JSON)
    description: Mapped[dict] = mapped_column(JSON, default=dict)
    price_minor: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    content_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), default="telegram")
    status: Mapped[str] = mapped_column(String(32), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reminder_type: Mapped[str] = mapped_column(String(64), default="daily")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_time: Mapped[str] = mapped_column(String(8), default="19:00")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Seoul")
    quiet_hours: Mapped[dict] = mapped_column(JSON, default=lambda: {"start": "22:00", "end": "08:00"})
    next_send_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AnalyticsEvent(Base, TimestampMixin):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_name: Mapped[str] = mapped_column(String(128), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    telegram_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    audience_language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)


class AdminUser(Base, TimestampMixin):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(64), default="editor")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LocalizationEntry(Base, TimestampMixin):
    __tablename__ = "localization_entries"
    __table_args__ = (UniqueConstraint("namespace", "key", "language", name="uq_localization_key_language"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    namespace: Mapped[str] = mapped_column(String(128), index=True)
    key: Mapped[str] = mapped_column(String(255), index=True)
    language: Mapped[str] = mapped_column(String(8), index=True)
    value: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class ContentTag(Base, TimestampMixin):
    __tablename__ = "content_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[dict] = mapped_column(JSON, default=dict)
    description: Mapped[dict] = mapped_column(JSON, default=dict)
    category: Mapped[str] = mapped_column(String(64), default="topic", index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class AuthSession(Base, TimestampMixin):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    subject_type: Mapped[str] = mapped_column(String(32), index=True)
    role: Mapped[str] = mapped_column(String(64), default="user")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(128), nullable=True)


class UserScenarioProgress(Base, TimestampMixin):
    __tablename__ = "user_scenario_progress"
    __table_args__ = (UniqueConstraint("user_id", "scenario_id", name="uq_user_scenario"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), index=True)
    dialogue_id: Mapped[int | None] = mapped_column(ForeignKey("dialogues.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="in_progress", index=True)
    current_line_index: Mapped[int] = mapped_column(Integer, default=0)
    comprehension_score: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserBookmark(Base, TimestampMixin):
    __tablename__ = "user_bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_bookmark"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(64), index=True)
    item_id: Mapped[int] = mapped_column(Integer, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AdminAuditLog(Base, TimestampMixin):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str] = mapped_column(String(128), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
