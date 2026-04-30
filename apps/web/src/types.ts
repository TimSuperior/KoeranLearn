export type Language = "ru" | "uz" | "en";

export type Localized = Record<Language, string>;

export type AuthUser = {
  telegram_id: string;
  interface_language: Language;
  explanation_language: Language;
  is_onboarded: boolean;
  is_premium: boolean;
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type ExerciseOption = {
  id: number;
  value: string;
  label: Localized;
  order_index: number;
};

export type AudioCue = {
  id: number;
  public_id: string;
  label: Partial<Localized>;
  attachment_role: string;
  variant: string;
  duration_seconds: number | null;
  playback_url: string;
  transcript: Partial<Localized>;
  transcript_mode: string;
  source_language: string | null;
  target_language: string | null;
  metadata_json: Record<string, unknown>;
};

export type Exercise = {
  id: number;
  slug: string;
  exercise_type: string;
  prompt: Localized;
  instructions: Localized;
  payload: Record<string, unknown>;
  answer_key: Record<string, unknown>;
  explanation: Localized;
  difficulty: string;
  topic: string;
  tags: string[];
  politeness_level: string | null;
  order_index: number;
  is_premium: boolean;
  options: ExerciseOption[];
};

export type ExerciseFeedback = {
  is_correct: boolean;
  expected: unknown;
  explanation: Localized;
  validator: string;
  lesson_completed?: boolean;
  xp_awarded?: number;
};

export type LessonBlock = {
  id: number;
  block_type: string;
  title: Localized;
  body: Localized;
  payload: Record<string, unknown>;
  order_index: number;
  status: string;
};

export type LessonAsset = {
  id: number;
  asset_type: string;
  url: string;
  metadata_json: Record<string, unknown>;
};

export type ExampleSentence = {
  id: number;
  korean: string;
  translations: Localized;
  explanation: Localized;
  context_labels: string[];
  politeness_level: string;
  register: string;
  audio_items: AudioCue[];
  audio_locked: boolean;
  is_premium: boolean;
};

export type LessonReference = {
  id: number;
  slug: string;
  title: Localized;
  summary: Localized;
  has_audio: boolean;
  has_premium_audio: boolean;
  audio_locked: boolean;
  estimated_minutes: number;
};

export type ScenarioReference = {
  id: number;
  slug: string;
  title: Localized;
  description: Localized;
  topic: string;
  difficulty: string;
  context_labels: string[];
  is_premium: boolean;
  has_premium_audio: boolean;
  audio_locked: boolean;
};

export type LessonVocabularyReference = {
  id: number;
  slug: string;
  korean: string;
  reading: string | null;
  translations: Localized;
  topic: string;
  difficulty: string;
  audio_asset_url: string | null;
  audio_items: AudioCue[];
  audio_locked: boolean;
  is_premium: boolean;
};

export type LessonGrammarReference = {
  id: number;
  slug: string;
  korean_pattern: string;
  title: Localized;
  category: string;
  difficulty: string;
  is_premium: boolean;
};

export type Lesson = {
  id: number;
  slug: string;
  title: Localized;
  summary: Localized;
  objectives: string[];
  korean_text: string | null;
  explanation: Localized;
  transfer_notes: Record<Language, string[]>;
  tags: string[];
  difficulty: string;
  topic: string;
  grammar_category: string | null;
  politeness_level: string;
  estimated_minutes: number;
  order_index: number;
  cover_metadata: Record<string, unknown>;
  audience_metadata: Record<string, unknown>;
  prerequisite_lesson_ids: number[];
  is_premium: boolean;
  status: string;
  access_state: string;
  resolved_access_state: string;
  has_audio: boolean;
  has_premium_audio: boolean;
  audio_locked: boolean;
  audio_missing: boolean;
  assets: LessonAsset[];
  blocks: LessonBlock[];
  exercises: Exercise[];
  related_vocabulary: LessonVocabularyReference[];
  related_grammar: LessonGrammarReference[];
  related_scenarios: ScenarioReference[];
};

export type Progress = {
  telegram_id: string;
  xp: number;
  streak_count: number;
  completed_lessons: number;
  due_reviews: number;
  mistake_reviews: number;
  current_path: {
    id: number;
    slug: string;
    title: Localized;
    percent_complete: number;
    completed_lessons: number;
    total_lessons: number;
  } | null;
  current_module: { id: number; title: Localized; slug: string } | null;
  current_lesson: {
    id: number;
    title: Localized;
    slug: string;
    summary: Localized;
    has_audio: boolean;
    has_premium_audio: boolean;
    audio_locked: boolean;
    estimated_minutes: number;
  } | null;
  last_completed_lesson: { id: number; title: Localized; slug: string } | null;
  difficult_topics: { topic: string }[];
  review_overview: ReviewOverview;
};

export type StudyPlan = {
  path: { id: number; slug: string; title: Localized; level: string } | null;
  module: { id: number; slug: string; title: Localized } | null;
  next_lesson: { id: number; slug: string; title: Localized } | null;
  completed_lessons: number;
  total_lessons: number;
  percent_complete: number;
};

export type Path = {
  id: number;
  slug: string;
  title: Localized;
  description: Localized;
  target_goal: string;
  level: string;
  order_index: number;
  is_premium: boolean;
};

export type GrammarPoint = {
  id: number;
  slug: string;
  korean_pattern: string;
  title: Localized;
  explanation: Localized;
  usage_notes: Localized;
  transfer_notes: Record<Language, string[]>;
  common_errors: Record<Language, string[]>;
  natural_alternatives: Array<Record<string, unknown>>;
  category: string;
  difficulty: string;
  politeness_level: string | null;
  tags: string[];
  is_premium: boolean;
  example_sentences?: ExampleSentence[];
  related_lessons?: LessonReference[];
  related_scenarios?: ScenarioReference[];
};

export type Vocabulary = {
  id: number;
  slug: string;
  korean: string;
  reading: string | null;
  translations: Localized;
  usage_notes: Localized;
  notes: Localized;
  variants: Array<Record<string, unknown> | string>;
  topic: string;
  tags: string[];
  difficulty: string;
  politeness_level: string | null;
  example_sentences: ExampleSentence[];
  audio_asset_url?: string | null;
  audio_items: AudioCue[];
  audio_locked: boolean;
  has_premium_audio: boolean;
  is_premium: boolean;
  related_lessons?: LessonReference[];
  related_scenarios?: ScenarioReference[];
};

export type ReviewItem = {
  id: number;
  item_type: string;
  item_id: number;
  source_lesson_id: number | null;
  ease_score: number;
  interval_days: number;
  repetitions: number;
  next_review_at: string;
  mastery_status: string;
  mistake_count: number;
  content: Record<string, unknown>;
};

export type ReviewInsightItem = {
  review_item_id: number;
  item_type: string;
  item_id: number;
  label: string;
  exercise_type: string | null;
  difficulty: string | null;
  topic: string | null;
  mistake_count: number;
  mastery_status: string;
  next_review_at: string;
  has_audio: boolean;
};

export type ReviewGrammarInsight = {
  key: string;
  label: string;
  mistakes: number;
  items: number;
};

export type ReviewExerciseBreakdown = {
  exercise_type: string;
  count: number;
};

export type ReviewScheduleSummary = {
  due_now: number;
  next_24h: number;
  next_7d: number;
  scheduled_total: number;
  mistake_queue: number;
  next_review_at: string | null;
};

export type ReviewGuidedSession = {
  mode: "due" | "mistakes" | "vocab" | "grammar" | "mixed" | "listening";
  title: string;
  description: string;
  item_count: number;
  size: number;
  tone: "accent" | "success" | "warning" | "danger" | "neutral";
};

export type ReviewOverview = {
  weak_items: ReviewInsightItem[];
  weak_grammar: ReviewGrammarInsight[];
  repeated_mistakes: ReviewInsightItem[];
  exercise_type_breakdown: ReviewExerciseBreakdown[];
  guided_sessions: ReviewGuidedSession[];
  schedule: ReviewScheduleSummary;
};

export type ScenarioProgress = {
  scenario_id: number;
  dialogue_id: number | null;
  status: string;
  current_line_index: number;
  comprehension_score: number;
};

export type Scenario = {
  id: number;
  slug: string;
  title: Localized;
  description: Localized;
  context_labels: string[];
  roles: string[];
  target_grammar_ids: number[];
  target_vocabulary_ids: number[];
  tags: string[];
  audience_languages: string[];
  topic: string;
  difficulty: string;
  order_index: number;
  is_premium: boolean;
  has_premium_audio: boolean;
  audio_locked: boolean;
  progress?: ScenarioProgress | null;
  is_favorited: boolean;
};

export type DialogueLine = {
  id?: number;
  speaker: string;
  korean: string;
  translations: Localized;
  notes?: Localized;
  audio_asset_url?: string | null;
  audio_items: AudioCue[];
  audio_locked: boolean;
  reveal_mode?: string;
  highlighted_expressions?: string[];
  is_useful_expression?: boolean;
  register?: string;
};

export type DialogueCheck = {
  prompt: Localized;
  answer: string;
};

export type DialogueExpression = {
  korean: string;
  translations: Localized;
};

export type Dialogue = {
  id: number;
  scenario_id: number;
  title: Localized;
  context: Localized;
  lines: DialogueLine[];
  checks: DialogueCheck[];
  useful_expressions: DialogueExpression[];
  explanation: Localized;
  politeness_level: string;
  order_index: number;
  is_premium: boolean;
  status?: string;
};

export type ScenarioDetail = Scenario & {
  dialogues: Dialogue[];
  audio_items: AudioCue[];
  audio_missing: boolean;
  related_vocab: Vocabulary[];
  related_grammar: GrammarPoint[];
};

export type QuizSession = {
  exercises: Exercise[];
  source: string;
};

export type UserSettings = {
  interface_language: Language;
  explanation_language: Language;
  reminders_enabled: boolean;
  reminder_time: string;
  timezone: string;
  learning_style: string;
  difficulty: string;
};
