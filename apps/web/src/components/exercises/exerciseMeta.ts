import { t } from "../../lib/format";
import type { Exercise, Language } from "../../types";

const EXERCISE_ALIASES: Record<string, string> = {
  choose_ending: "choose_verb_ending",
  sentence_reordering: "sentence_reorder",
  listening_comprehension: "listen_and_choose"
};

type ExercisePresentation = {
  label: string;
  instruction: string;
  mistakeCopy: string;
  answerLabel: string;
  submitLabel: string;
};

const PRESENTATION: Record<string, ExercisePresentation> = {
  multiple_choice: {
    label: "Multiple choice",
    instruction: "Choose the single answer that best matches the prompt.",
    mistakeCopy: "Re-read the prompt and eliminate one distractor before you answer again.",
    answerLabel: "Choose one answer",
    submitLabel: "Check answer"
  },
  fill_blank: {
    label: "Fill in the blank",
    instruction: "Type only the missing word, particle, or ending.",
    mistakeCopy: "Focus on the exact missing form, not the whole sentence.",
    answerLabel: "Missing text",
    submitLabel: "Check answer"
  },
  sentence_reorder: {
    label: "Sentence reorder",
    instruction: "Build the sentence in natural Korean order, then submit it.",
    mistakeCopy: "Put the sentence together from left to right and keep the ending in the right place.",
    answerLabel: "Sentence order",
    submitLabel: "Check order"
  },
  match_pairs: {
    label: "Match pairs",
    instruction: "Pair each left-side item with its correct partner.",
    mistakeCopy: "Double-check each pair before you lock it in.",
    answerLabel: "Pairs",
    submitLabel: "Save matches"
  },
  choose_particle: {
    label: "Choose particle",
    instruction: "Pick the particle that fits the noun role in the sentence.",
    mistakeCopy: "Check whether the noun is topic, subject, or object before choosing.",
    answerLabel: "Particle",
    submitLabel: "Check particle"
  },
  choose_verb_ending: {
    label: "Choose ending",
    instruction: "Choose the ending that matches tone, politeness, and sentence form.",
    mistakeCopy: "Check the intended politeness and ending shape before you retry.",
    answerLabel: "Ending",
    submitLabel: "Check ending"
  },
  translation_selection: {
    label: "Translation selection",
    instruction: "Choose the translation that preserves the full meaning, not just one word.",
    mistakeCopy: "Watch for polite meaning and small context words, not only vocabulary.",
    answerLabel: "Translation",
    submitLabel: "Check translation"
  },
  dialogue_continuation: {
    label: "Dialogue continuation",
    instruction: "Pick the reply that sounds natural in the conversation.",
    mistakeCopy: "Listen for the social context and choose the response that fits the exchange.",
    answerLabel: "Reply",
    submitLabel: "Check reply"
  },
  reading_comprehension: {
    label: "Reading comprehension",
    instruction: "Read the sentence carefully, then choose the answer supported by the text.",
    mistakeCopy: "Base your answer on what the text actually says, not on a guess from one keyword.",
    answerLabel: "Answer",
    submitLabel: "Check reading"
  },
  listen_and_choose: {
    label: "Listening comprehension",
    instruction: "Play the audio cue first, then choose the best answer.",
    mistakeCopy: "Replay the prompt and listen for the key word or ending you missed.",
    answerLabel: "Answer",
    submitLabel: "Check listening"
  },
  true_false: {
    label: "True or false",
    instruction: "Decide whether the statement is correct as written.",
    mistakeCopy: "Treat this like a fact check. One wrong detail makes the whole statement false.",
    answerLabel: "True or false",
    submitLabel: "Check answer"
  },
  recap_quiz: {
    label: "Recap quiz",
    instruction: "Use the lesson recap to choose the strongest answer.",
    mistakeCopy: "Think back to the lesson target instead of answering from habit.",
    answerLabel: "Best answer",
    submitLabel: "Check recap"
  },
  flashcard_review: {
    label: "Flashcard review",
    instruction: "Try to recall the answer before you reveal it, then rate yourself honestly.",
    mistakeCopy: "If recall was shaky, mark it as missed so it comes back sooner.",
    answerLabel: "Recall",
    submitLabel: "Save review"
  }
};

export function canonicalExerciseType(exerciseType: string): string {
  const normalized = String(exerciseType || "").trim().toLowerCase();
  return EXERCISE_ALIASES[normalized] || normalized;
}

export function exercisePresentation(exercise: Exercise | string): ExercisePresentation {
  const exerciseType = typeof exercise === "string" ? exercise : exercise.exercise_type;
  return PRESENTATION[canonicalExerciseType(exerciseType)] || {
    label: humanizeExerciseType(exerciseType),
    instruction: "Read the prompt carefully and submit the strongest answer you can.",
    mistakeCopy: "Use the explanation, then try the prompt one more time.",
    answerLabel: "Your answer",
    submitLabel: "Check answer"
  };
}

export function exerciseInstruction(
  exercise: Exercise,
  language: Language,
  translate?: (key: string, fallback?: string) => string,
): string {
  if (t(exercise.instructions, language)) {
    return t(exercise.instructions, language);
  }
  const presentation = exercisePresentation(exercise);
  const exerciseType = canonicalExerciseType(exercise.exercise_type);
  return translate?.(`exercise.instruction.${exerciseType}`, presentation.instruction)
    || translate?.("exercise.instruction.fallback", presentation.instruction)
    || presentation.instruction;
}

export function humanizeExerciseType(exerciseType: string): string {
  return canonicalExerciseType(exerciseType).replaceAll("_", " ");
}

export function difficultyCopy(difficulty: string): string {
  const normalized = String(difficulty || "").toUpperCase();
  if (normalized.startsWith("A0")) return `${normalized} starter`;
  if (normalized.startsWith("A1")) return `${normalized} foundation`;
  if (normalized.startsWith("A2")) return `${normalized} stretch`;
  if (normalized.startsWith("B1")) return `${normalized} applied`;
  if (normalized.startsWith("B2")) return `${normalized} advanced`;
  return difficulty || "Mixed level";
}

export function normalizeExerciseSubmission(exercise: Exercise, answer: unknown): unknown {
  const exerciseType = canonicalExerciseType(exercise.exercise_type);
  if (exerciseType === "fill_blank") return normalizeText(answer);
  if (exerciseType === "sentence_reorder" || exerciseType === "listen_and_order") {
    if (Array.isArray(answer)) return answer.map((item) => normalizeText(item)).filter(Boolean);
    if (typeof answer === "string") return normalizeText(answer).split(" ").filter(Boolean);
    return [];
  }
  if (exerciseType === "match_pairs" || exerciseType === "listen_and_match") return normalizePairs(answer);
  if (typeof answer === "string") return normalizeText(answer);
  return answer;
}

export function formatExpectedAnswer(exercise: Exercise, expected: unknown, language: Language): string[] {
  const exerciseType = canonicalExerciseType(exercise.exercise_type);
  if (exerciseType === "match_pairs" || exerciseType === "listen_and_match") {
    return pairEntries(expected).map(([left, right]) => `${left} -> ${right}`);
  }
  if (exerciseType === "sentence_reorder" || exerciseType === "listen_and_order") {
    if (Array.isArray(expected)) return [expected.map((item) => String(item)).join(" ")];
    if (typeof expected === "string") return [expected];
  }
  if (choiceExercise(exerciseType)) {
    return choiceValues(expected).map((value) => optionLabel(exercise, value, language));
  }
  if (Array.isArray(expected)) return expected.map((item) => String(item));
  if (expected && typeof expected === "object") return [JSON.stringify(expected)];
  if (expected == null) return [];
  return [String(expected)];
}

function choiceExercise(exerciseType: string): boolean {
  return [
    "multiple_choice",
    "choose_particle",
    "choose_verb_ending",
    "translation_selection",
    "dialogue_continuation",
    "reading_comprehension",
    "listen_and_choose",
    "true_false",
    "recap_quiz",
    "flashcard_review"
  ].includes(exerciseType);
}

function optionLabel(exercise: Exercise, value: unknown, language: Language): string {
  const normalizedValue = normalizeText(value);
  const match = exercise.options.find((option) => normalizeText(option.value) === normalizedValue);
  if (!match) return String(value);
  return t(match.label, language) || match.value;
}

function choiceValues(expected: unknown): unknown[] {
  if (Array.isArray(expected)) return expected;
  if (expected == null) return [];
  return [expected];
}

function pairEntries(value: unknown): Array<[string, string]> {
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (Array.isArray(item) && item.length === 2) return [String(item[0]), String(item[1])] as [string, string];
        if (item && typeof item === "object" && "left" in item && "right" in item) {
          const pair = item as Record<string, unknown>;
          return [String(pair.left), String(pair.right)] as [string, string];
        }
        return null;
      })
      .filter((item): item is [string, string] => Boolean(item));
  }
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).map(([left, right]) => [left, String(right)]);
  }
  return [];
}

function normalizePairs(value: unknown): Record<string, string> {
  if (!value || typeof value !== "object") return {};
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .map(([left, right]) => [normalizeText(left), normalizeText(right)] as const)
      .filter(([left, right]) => left && right)
  );
}

function normalizeText(value: unknown): string {
  return String(value || "").trim().replace(/\s+/g, " ");
}
