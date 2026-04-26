import type { AdminEntityKey, AdminRow, LocalizedText } from "./types";

export function localized(value = ""): LocalizedText {
  return { ru: value, uz: value, en: value };
}

export function parseLines(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function joinLines(items: unknown): string {
  return Array.isArray(items) ? items.map(String).join("\n") : "";
}

export function parseTags(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function joinTags(items: unknown): string {
  return Array.isArray(items) ? items.map(String).join(", ") : "";
}

export function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

export function moveItem<T>(items: T[], from: number, to: number): T[] {
  if (from === to || from < 0 || to < 0 || from >= items.length || to >= items.length) {
    return items;
  }
  const next = [...items];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

export function withOrder<T extends Record<string, any>>(items: T[]): T[] {
  return items.map((item, index) => ({ ...item, order_index: index }));
}

export function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function blankBlock(): AdminRow {
  return {
    block_type: "explanation",
    title: localized(""),
    body: localized(""),
    payload: {},
    order_index: 0,
    status: "draft",
  };
}

export function blankDialogueLine(): AdminRow {
  return {
    speaker: "",
    korean: "",
    translations: localized(""),
    notes: localized(""),
    reveal_mode: "toggle",
    highlighted_expressions: [],
    order_index: 0,
    is_useful_expression: false,
  };
}

export function blankLessonAsset(): AdminRow {
  return {
    asset_type: "support_file",
    url: "",
    metadata_json: {},
  };
}

export function blankDialogue(): AdminRow {
  return {
    title: localized(""),
    context: localized(""),
    explanation: localized(""),
    politeness_level: "polite_informal",
    access_state: "inherit",
    status: "draft",
    order_index: 0,
    dialogue_lines: [blankDialogueLine()],
  };
}

export function blankExerciseOption(): AdminRow {
  return {
    value: "",
    label: localized(""),
    is_correct: false,
    order_index: 0,
  };
}

export function blankExercise(): AdminRow {
  return {
    slug: "",
    lesson_id: null,
    exercise_type: "multiple_choice",
    prompt: localized(""),
    instructions: localized(""),
    payload: {},
    answer_key: { value: "" },
    answer_validation: { strategy: "one_of" },
    explanation: localized(""),
    difficulty: "A0",
    topic: "general",
    tags: [],
    grammar_point_id: null,
    vocabulary_id: null,
    access_state: "inherit",
    status: "draft",
    order_index: 0,
    options: [blankExerciseOption(), blankExerciseOption()],
  };
}

export function blankEntity(entity: AdminEntityKey): AdminRow {
  if (entity === "paths") {
    return {
      slug: "",
      title: localized(""),
      description: localized(""),
      target_goal: "korean_from_zero",
      level: "A0",
      order_index: 0,
      access_state: "free",
      status: "draft",
    };
  }
  if (entity === "courses") {
    return {
      slug: "",
      path_id: null,
      title: localized(""),
      description: localized(""),
      order_index: 0,
      access_state: "inherit",
      status: "draft",
    };
  }
  if (entity === "modules") {
    return {
      slug: "",
      course_id: null,
      title: localized(""),
      description: localized(""),
      prerequisites: [],
      difficulty: "A0",
      estimated_minutes: 20,
      order_index: 0,
      access_state: "inherit",
      status: "draft",
    };
  }
  if (entity === "lessons") {
    return {
      slug: "",
      module_id: null,
      title: localized(""),
      summary: localized(""),
      objectives: [],
      explanation: localized(""),
      transfer_notes: { ru: [], uz: [], en: [] },
      tags: [],
      difficulty: "A0",
      topic: "general",
      grammar_category: "",
      politeness_level: "polite_informal",
      estimated_minutes: 10,
      cover_metadata: {},
      audience_metadata: { audience: "", notes: localized("") },
      prerequisite_lesson_ids: [],
      access_state: "inherit",
      status: "draft",
      order_index: 0,
      relation_ids: { related_vocabulary: [], related_grammar: [], related_scenarios: [] },
      blocks: [blankBlock()],
    };
  }
  if (entity === "vocabulary") {
    return {
      slug: "",
      korean: "",
      reading: "",
      translations: localized(""),
      usage_notes: localized(""),
      notes: localized(""),
      topic: "general",
      tags: [],
      difficulty: "A0",
      politeness_level: "",
      example_sentences: [],
      variants: [],
      access_state: "free",
      status: "draft",
      relation_ids: { related_lessons: [], related_scenarios: [] },
    };
  }
  if (entity === "grammar") {
    return {
      slug: "",
      korean_pattern: "",
      title: localized(""),
      explanation: localized(""),
      usage_notes: localized(""),
      transfer_notes: { ru: [], uz: [], en: [] },
      common_errors: { ru: [], uz: [], en: [] },
      natural_alternatives: [],
      category: "grammar",
      difficulty: "A0",
      politeness_level: "",
      tags: [],
      access_state: "free",
      status: "draft",
      relation_ids: { related_lessons: [], related_scenarios: [] },
    };
  }
  if (entity === "scenarios") {
    return {
      slug: "",
      title: localized(""),
      description: localized(""),
      context_labels: [],
      roles: [],
      tags: [],
      audience_languages: ["ru", "uz", "en"],
      audience_metadata: { audience: "", notes: localized("") },
      topic: "daily_life",
      difficulty: "A0",
      access_state: "free",
      status: "draft",
      order_index: 0,
      relation_ids: { related_vocabulary: [], related_grammar: [], related_lessons: [] },
      dialogues: [blankDialogue()],
    };
  }
  if (entity === "dialogues") {
    return {
      scenario_id: null,
      title: localized(""),
      context: localized(""),
      explanation: localized(""),
      checks: [],
      useful_expressions: [],
      politeness_level: "polite_informal",
      access_state: "inherit",
      status: "draft",
      order_index: 0,
      dialogue_lines: [blankDialogueLine()],
    };
  }
  if (entity === "exercises") {
    return blankExercise();
  }
  if (entity === "example-sentences") {
    return {
      korean: "",
      translations: localized(""),
      explanation: localized(""),
      grammar_point_id: null,
      vocabulary_id: null,
      context_labels: [],
      politeness_level: "polite_informal",
      register: "spoken",
      access_state: "free",
      status: "draft",
    };
  }
  if (entity === "audio-assets") {
    return {
      label: localized(""),
      attachment_role: "general",
      variant: "default",
      source_language: "ko",
      target_language: "en",
      transcript: localized(""),
      transcript_mode: "toggle",
      metadata_json: {},
      premium_only: true,
      status: "draft",
      compliance_state: "active",
      order_index: 0,
      lesson_id: null,
      lesson_block_id: null,
      exercise_id: null,
      vocabulary_id: null,
      example_sentence_id: null,
      dialogue_line_id: null,
      scenario_id: null,
    };
  }
  if (entity === "tags") {
    return {
      slug: "",
      title: localized(""),
      description: localized(""),
      category: "topic",
      order_index: 0,
      status: "draft",
    };
  }
  if (entity === "localization") {
    return {
      namespace: "admin",
      key: "",
      language: "en",
      value: "",
      status: "draft",
    };
  }
  return {
    slug: "",
    title: localized(""),
    description: localized(""),
    price_minor: 0,
    currency: "USD",
    content_rules: {},
    order_index: 0,
    status: "draft",
    is_active: true,
  };
}
