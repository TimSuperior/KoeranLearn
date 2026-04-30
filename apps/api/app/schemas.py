from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


Language = Literal["ru", "uz", "en"]


class LocalizedText(BaseModel):
    ru: str = ""
    uz: str = ""
    en: str = ""


class TelegramAuthRequest(BaseModel):
    init_data: str


class TelegramUserPayload(BaseModel):
    id: int | str
    username: str | None = None
    first_name: str | None = None
    language_code: str | None = None


class AuthResponse(BaseModel):
    telegram_id: str
    interface_language: str
    explanation_language: str
    is_onboarded: bool
    is_premium: bool
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class OnboardingStartRequest(BaseModel):
    telegram_id: str
    username: str | None = None
    first_name: str | None = None
    telegram_language_code: str | None = None
    deep_link: str | None = None


class OnboardingCompleteRequest(OnboardingStartRequest):
    interface_language: Language
    explanation_language: Language | None = None
    goal: str
    level: str
    daily_minutes: int = Field(ge=5, le=30)
    learning_style: str
    timezone: str = "Asia/Seoul"
    reminder_time: str = "19:00"


class UserSummary(BaseModel):
    telegram_id: str
    interface_language: str
    explanation_language: str
    is_onboarded: bool
    is_premium: bool
    xp: int
    streak_count: int
    current_lesson_id: int | None = None
    current_path_id: int | None = None


class PathDTO(BaseModel):
    id: int
    slug: str
    title: dict[str, str]
    description: dict[str, str]
    target_goal: str
    level: str
    order_index: int
    is_premium: bool

    class Config:
        from_attributes = True


class AudioCueDTO(BaseModel):
    id: int
    public_id: str
    label: dict[str, str] = {}
    attachment_role: str
    variant: str
    duration_seconds: float | None = None
    playback_url: str
    transcript: dict[str, str] = {}
    transcript_mode: str = "toggle"
    source_language: str | None = None
    target_language: str | None = None
    metadata_json: dict[str, Any] = {}


class LessonReferenceDTO(BaseModel):
    id: int
    slug: str
    title: dict[str, str]
    summary: dict[str, str] = {}
    has_audio: bool = False
    has_premium_audio: bool = False
    audio_locked: bool = False
    estimated_minutes: int = 0

    class Config:
        from_attributes = True


class ScenarioReferenceDTO(BaseModel):
    id: int
    slug: str
    title: dict[str, str]
    description: dict[str, str]
    topic: str
    difficulty: str
    context_labels: list[str] = []
    is_premium: bool = False
    has_premium_audio: bool = False
    audio_locked: bool = False

    class Config:
        from_attributes = True


class LessonVocabularyReferenceDTO(BaseModel):
    id: int
    slug: str
    korean: str
    reading: str | None
    translations: dict[str, str]
    topic: str
    difficulty: str
    audio_asset_url: str | None = None
    audio_items: list[AudioCueDTO] = []
    audio_locked: bool = False
    is_premium: bool

    class Config:
        from_attributes = True


class LessonGrammarReferenceDTO(BaseModel):
    id: int
    slug: str
    korean_pattern: str
    title: dict[str, str]
    category: str
    difficulty: str
    is_premium: bool

    class Config:
        from_attributes = True


class ExerciseOptionDTO(BaseModel):
    id: int
    value: str
    label: dict[str, str]
    order_index: int

    class Config:
        from_attributes = True


class ExerciseDTO(BaseModel):
    id: int
    slug: str
    exercise_type: str
    prompt: dict[str, str]
    instructions: dict[str, str] = {}
    payload: dict[str, Any]
    answer_key: dict[str, Any] = {}
    explanation: dict[str, str]
    difficulty: str
    topic: str
    tags: list[str] = []
    politeness_level: str | None
    order_index: int
    is_premium: bool
    options: list[ExerciseOptionDTO] = []

    class Config:
        from_attributes = True


class LessonBlockDTO(BaseModel):
    id: int
    block_type: str
    title: dict[str, str]
    body: dict[str, str]
    payload: dict[str, Any]
    order_index: int
    status: str

    class Config:
        from_attributes = True


class LessonAssetDTO(BaseModel):
    id: int
    asset_type: str
    url: str
    metadata_json: dict[str, Any] = {}

    class Config:
        from_attributes = True


class LessonDTO(BaseModel):
    id: int
    slug: str
    title: dict[str, str]
    summary: dict[str, str]
    objectives: list[str] = []
    korean_text: str | None
    explanation: dict[str, str]
    transfer_notes: dict[str, list[str]]
    tags: list[str]
    difficulty: str
    topic: str
    grammar_category: str | None
    politeness_level: str
    estimated_minutes: int
    order_index: int
    cover_metadata: dict[str, Any] = {}
    audience_metadata: dict[str, Any] = {}
    prerequisite_lesson_ids: list[int] = []
    is_premium: bool
    status: str = "published"
    access_state: str = "free"
    resolved_access_state: str = "free"
    has_audio: bool = False
    has_premium_audio: bool = False
    audio_locked: bool = False
    audio_missing: bool = False
    assets: list[LessonAssetDTO] = []
    blocks: list[LessonBlockDTO] = []
    exercises: list[ExerciseDTO] = []
    related_vocabulary: list[LessonVocabularyReferenceDTO] = []
    related_grammar: list[LessonGrammarReferenceDTO] = []
    related_scenarios: list[ScenarioReferenceDTO] = []

    class Config:
        from_attributes = True


class LessonStartRequest(BaseModel):
    telegram_id: str | None = None


class ExerciseSubmitRequest(BaseModel):
    telegram_id: str | None = None
    answer: Any
    lesson_id: int | None = None


class ExerciseSubmitResponse(BaseModel):
    is_correct: bool
    expected: Any
    explanation: dict[str, str]
    validator: str = "exact"
    lesson_completed: bool = False
    xp_awarded: int = 0


class ReviewItemDTO(BaseModel):
    id: int
    item_type: str
    item_id: int
    source_lesson_id: int | None
    ease_score: float
    interval_days: int
    repetitions: int
    next_review_at: datetime
    mastery_status: str
    mistake_count: int
    content: dict[str, Any]


class ReviewSubmitRequest(BaseModel):
    telegram_id: str | None = None
    answer: dict[str, Any] = {}
    is_correct: bool
    quality: int = Field(default=3, ge=0, le=5)


class ProgressDTO(BaseModel):
    telegram_id: str
    xp: int
    streak_count: int
    completed_lessons: int
    due_reviews: int
    mistake_reviews: int = 0
    current_path: dict[str, Any] | None
    current_module: dict[str, Any] | None = None
    current_lesson: dict[str, Any] | None
    last_completed_lesson: dict[str, Any] | None = None
    difficult_topics: list[dict[str, Any]]
    review_overview: dict[str, Any] = {}


class GrammarDTO(BaseModel):
    id: int
    slug: str
    korean_pattern: str
    title: dict[str, str]
    explanation: dict[str, str]
    usage_notes: dict[str, str] = {}
    transfer_notes: dict[str, list[str]]
    common_errors: dict[str, list[str]]
    natural_alternatives: list[dict[str, Any]]
    category: str
    difficulty: str
    politeness_level: str | None
    tags: list[str]
    is_premium: bool

    class Config:
        from_attributes = True


class ExampleSentenceDTO(BaseModel):
    id: int
    korean: str
    translations: dict[str, str]
    explanation: dict[str, str] = {}
    context_labels: list[str] = []
    politeness_level: str
    register: str
    audio_items: list[AudioCueDTO] = []
    audio_locked: bool = False
    is_premium: bool

    class Config:
        from_attributes = True


class GrammarDetailDTO(GrammarDTO):
    example_sentences: list[ExampleSentenceDTO] = []
    related_lessons: list[LessonReferenceDTO] = []
    related_scenarios: list[ScenarioReferenceDTO] = []


class VocabularyDTO(BaseModel):
    id: int
    slug: str
    korean: str
    reading: str | None
    translations: dict[str, str]
    usage_notes: dict[str, str]
    notes: dict[str, str] = {}
    variants: list[dict[str, Any] | str] = []
    topic: str
    tags: list[str]
    difficulty: str
    politeness_level: str | None
    example_sentences: list[dict[str, Any]]
    audio_asset_url: str | None = None
    audio_items: list[AudioCueDTO] = []
    audio_locked: bool = False
    has_premium_audio: bool = False
    is_premium: bool

    class Config:
        from_attributes = True


class VocabularyDetailDTO(VocabularyDTO):
    related_lessons: list[LessonReferenceDTO] = []
    related_scenarios: list[ScenarioReferenceDTO] = []


class WritingCorrectionRequest(BaseModel):
    telegram_id: str | None = None
    text: str = Field(min_length=1, max_length=500)
    target_register: str | None = "polite_informal"
    include_translation: bool = True


class WritingCorrectionResponse(BaseModel):
    corrected_text: str
    natural_text: str
    feedback: dict[str, Any]
    provider: str
    remaining_daily_quota: int | None = None


class ReminderSettingsDTO(BaseModel):
    enabled: bool = True
    reminder_time: str = "19:00"
    timezone: str = "Asia/Seoul"
    quiet_hours: dict[str, str] = Field(default_factory=lambda: {"start": "22:00", "end": "08:00"})


class UserSettingsDTO(BaseModel):
    interface_language: Language
    explanation_language: Language
    reminders_enabled: bool = True
    reminder_time: str = "19:00"
    timezone: str = "Asia/Seoul"
    learning_style: str = "mixed"
    difficulty: str = "normal"


class UserSettingsUpdate(BaseModel):
    interface_language: Language | None = None
    explanation_language: Language | None = None
    reminders_enabled: bool | None = None
    reminder_time: str | None = None
    timezone: str | None = None
    learning_style: str | None = None
    difficulty: str | None = None


class PremiumAccessDTO(BaseModel):
    telegram_id: str
    is_premium: bool
    active_subscription: dict[str, Any] | None = None
    limits: dict[str, int]


class AnalyticsEventCreate(BaseModel):
    event_name: str
    telegram_id: str | None = None
    audience_language: str | None = None
    properties: dict[str, Any] = {}


class AdminLessonCreate(BaseModel):
    module_id: int
    slug: str
    title: dict[str, str]
    summary: dict[str, str] = {}
    korean_text: str | None = None
    explanation: dict[str, str] = {}
    transfer_notes: dict[str, list[str]] = {}
    tags: list[str] = []
    difficulty: str = "A0"
    topic: str = "general"
    grammar_category: str | None = None
    politeness_level: str = "polite_informal"
    estimated_minutes: int = 5
    order_index: int = 0
    is_premium: bool = False


class AdminLessonUpdate(BaseModel):
    title: dict[str, str] | None = None
    summary: dict[str, str] | None = None
    korean_text: str | None = None
    explanation: dict[str, str] | None = None
    transfer_notes: dict[str, list[str]] | None = None
    tags: list[str] | None = None
    difficulty: str | None = None
    topic: str | None = None
    grammar_category: str | None = None
    politeness_level: str | None = None
    estimated_minutes: int | None = None
    order_index: int | None = None
    is_premium: bool | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminMeDTO(BaseModel):
    id: int
    email: str
    role: str


class ScenarioDTO(BaseModel):
    id: int
    slug: str
    title: dict[str, str]
    description: dict[str, str]
    context_labels: list[str]
    roles: list[str]
    target_grammar_ids: list[int]
    target_vocabulary_ids: list[int]
    tags: list[str]
    audience_languages: list[str]
    topic: str
    difficulty: str
    order_index: int
    is_premium: bool
    has_premium_audio: bool = False
    audio_locked: bool = False
    status: str = "published"
    progress: dict[str, Any] | None = None
    is_favorited: bool = False

    class Config:
        from_attributes = True


class DialogueDTO(BaseModel):
    id: int
    scenario_id: int
    title: dict[str, str]
    context: dict[str, str]
    lines: list[dict[str, Any]]
    checks: list[dict[str, Any]]
    useful_expressions: list[dict[str, Any]]
    explanation: dict[str, str]
    politeness_level: str
    order_index: int
    is_premium: bool
    status: str = "published"

    class Config:
        from_attributes = True


class ScenarioDetailDTO(ScenarioDTO):
    dialogues: list[DialogueDTO] = []
    audio_items: list[AudioCueDTO] = []
    audio_missing: bool = False
    related_vocab: list[VocabularyDTO] = []
    related_grammar: list[GrammarDTO] = []


class ScenarioProgressDTO(BaseModel):
    scenario_id: int
    dialogue_id: int | None = None
    status: str
    current_line_index: int = 0
    comprehension_score: float = 0.0


class ScenarioCompleteRequest(BaseModel):
    comprehension_score: float = Field(default=1.0, ge=0, le=1)


class ScenarioFavoriteRequest(BaseModel):
    favorite: bool = True


class QuizStartRequest(BaseModel):
    topic: str | None = None
    limit: int = Field(default=5, ge=1, le=20)
    mistakes_only: bool = False
    due_only: bool = False
    focus: str | None = None
    require_audio: bool = False


class QuizSessionDTO(BaseModel):
    exercises: list[ExerciseDTO]
    source: str


class ContentEntityPayload(BaseModel):
    data: dict[str, Any]


class LocalizationEntryDTO(BaseModel):
    id: int
    namespace: str
    key: str
    language: str
    value: str
    status: str = "published"

    class Config:
        from_attributes = True
