import { RotateCcw, Send } from "lucide-react";
import { useMemo, useState } from "react";

import { interpolate } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { Exercise, Language } from "../../types";
import { Button, Field, StatusChip, Surface, TextInput } from "../ui";
import { canonicalExerciseType, exerciseInstruction, normalizeExerciseSubmission } from "./exerciseMeta";

type Props = {
  exercise: Exercise;
  language: Language;
  onSubmit: (answer: unknown) => void;
  disabled?: boolean;
  compact?: boolean;
};

export function ExerciseRenderer({ exercise, language, onSubmit, disabled = false, compact = false }: Props) {
  const { content, topicLabel, ui } = useI18n();

  return (
    <Surface className={compact ? "p-4" : ""}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          <StatusChip tone="neutral">{exercise.difficulty}</StatusChip>
          <StatusChip tone="neutral">{topicLabel(exercise.topic)}</StatusChip>
        </div>
      </div>
      <p className="mt-4 text-lg font-semibold leading-8 text-[color:var(--app-text)]">{content(exercise.prompt, ui("exercise.prompt", "Exercise prompt"))}</p>
      <p className="mt-2 text-sm leading-6 text-[color:var(--app-muted)]">{exerciseInstruction(exercise, language, ui)}</p>
      <div className="mt-5">
        <Renderer key={`${exercise.id}-${exercise.exercise_type}`} exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} />
      </div>
    </Surface>
  );
}

function Renderer({ exercise, language, onSubmit, disabled }: Props) {
  const exerciseType = canonicalExerciseType(exercise.exercise_type);

  if (exerciseType === "multiple_choice") return <ChoiceExercise exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} />;
  if (exerciseType === "fill_blank") return <TextAnswerExercise exercise={exercise} onSubmit={onSubmit} disabled={disabled} />;
  if (exerciseType === "sentence_reorder" || exerciseType === "listen_and_order") return <SentenceReorderExercise exercise={exercise} onSubmit={onSubmit} disabled={disabled} />;
  if (exerciseType === "match_pairs" || exerciseType === "listen_and_match") return <MatchPairsExercise exercise={exercise} onSubmit={onSubmit} disabled={disabled} />;
  if (exerciseType === "choose_particle") return <ChoiceExercise exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} />;
  if (exerciseType === "choose_verb_ending") return <ChoiceExercise exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} />;
  if (exerciseType === "translation_selection") return <ChoiceExercise exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} />;
  if (exerciseType === "dialogue_continuation") return <ChoiceExercise exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} />;
  if (exerciseType === "reading_comprehension") return <ChoiceExercise exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} />;
  if (exerciseType === "listen_and_choose") return <ChoiceExercise exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} />;
  if (exerciseType === "true_false") return <ChoiceExercise exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} columns={2} />;
  if (exerciseType === "recap_quiz") {
    return exercise.options.length ? <ChoiceExercise exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} /> : <TextAnswerExercise exercise={exercise} onSubmit={onSubmit} disabled={disabled} />;
  }
  if (exerciseType === "flashcard_review") return <FlashcardReviewExercise exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} />;
  return <TextAnswerExercise exercise={exercise} onSubmit={onSubmit} disabled={disabled} />;
}

function ChoiceExercise({ exercise, language, onSubmit, disabled, columns = 1 }: Props & { columns?: 1 | 2 }) {
  const options = [...exercise.options].sort((left, right) => left.order_index - right.order_index);
  const { content } = useI18n();

  return (
    <div className={`grid gap-2 ${columns === 2 ? "sm:grid-cols-2" : ""}`}>
      {options.map((option) => (
        <button
          type="button"
          key={option.id}
          disabled={disabled}
          onClick={() => onSubmit(normalizeExerciseSubmission(exercise, option.value))}
          className="min-h-12 rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left text-sm font-medium text-[color:var(--app-text)] transition hover:border-[color:var(--app-accent)] disabled:opacity-50"
        >
          {content(option.label, option.value)}
        </button>
      ))}
      {options.length === 0 ? <TextAnswerExercise exercise={exercise} onSubmit={onSubmit} disabled={disabled} /> : null}
    </div>
  );
}

function TextAnswerExercise({ exercise, onSubmit, disabled }: { exercise: Exercise; onSubmit: (answer: unknown) => void; disabled?: boolean }) {
  const { ui } = useI18n();
  const [value, setValue] = useState("");

  return (
    <div className="space-y-3">
      <Field label={ui("exercise.prompt", "Exercise prompt")}>
        <TextInput value={value} onChange={(event) => setValue(event.target.value)} placeholder={ui("exercise.answer_placeholder", "Type your answer")} disabled={disabled} />
      </Field>
      <Button disabled={disabled || !value.trim()} onClick={() => onSubmit(normalizeExerciseSubmission(exercise, value))}>
        {ui("action.continue", "Continue")}
        <Send size={16} />
      </Button>
    </div>
  );
}

function SentenceReorderExercise({ exercise, onSubmit, disabled }: { exercise: Exercise; onSubmit: (answer: unknown) => void; disabled?: boolean }) {
  const { ui } = useI18n();
  const tokens = useMemo(() => orderedTokens(exercise), [exercise]);
  const [available, setAvailable] = useState(tokens);
  const [answer, setAnswer] = useState<string[]>([]);

  function reset() {
    setAvailable(tokens);
    setAnswer([]);
  }

  if (!tokens.length) return <TextAnswerExercise exercise={exercise} onSubmit={onSubmit} disabled={disabled} />;

  return (
    <div className="space-y-3">
      <div className="min-h-16 rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-3">
        <div className="flex flex-wrap gap-2">
          {answer.length ? (
            answer.map((token, index) => (
              <button
                key={`${token}-${index}`}
                type="button"
                disabled={disabled}
                onClick={() => {
                  setAnswer((items) => items.filter((_, itemIndex) => itemIndex !== index));
                  setAvailable((items) => [...items, token]);
                }}
                className="rounded-full bg-white px-3 py-2 text-sm font-medium text-[color:var(--app-text)]"
              >
                {token}
              </button>
            ))
          ) : (
            <p className="text-sm text-[color:var(--app-muted)]">{ui("exercise.reorder_hint", "Tap tokens below to build the sentence.")}</p>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {available.map((token, index) => (
          <button
            key={`${token}-${index}`}
            type="button"
            disabled={disabled}
            onClick={() => {
              setAvailable((items) => items.filter((_, itemIndex) => itemIndex !== index));
              setAnswer((items) => [...items, token]);
            }}
            className="rounded-full border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-3 py-2 text-sm text-[color:var(--app-text)]"
          >
            {token}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <Button variant="secondary" className="px-3" disabled={disabled} onClick={reset}>
          <RotateCcw size={16} />
        </Button>
        <Button disabled={disabled || answer.length === 0} onClick={() => onSubmit(normalizeExerciseSubmission(exercise, answer))}>
          {ui("action.continue", "Continue")}
        </Button>
      </div>
    </div>
  );
}

function MatchPairsExercise({ exercise, onSubmit, disabled }: { exercise: Exercise; onSubmit: (answer: unknown) => void; disabled?: boolean }) {
  const { ui } = useI18n();
  const pairs = useMemo(() => exercisePairs(exercise), [exercise]);
  const leftItems = pairs.map(([left]) => left);
  const rightItems = useMemo(() => {
    const values = pairs.map(([, right]) => right);
    if (values.length <= 1) return values;
    const rotated = [...values.slice(1), values[0]];
    return rotated.join("|") === values.join("|") ? [...values].reverse() : rotated;
  }, [pairs]);
  const [selectedLeft, setSelectedLeft] = useState<string | null>(null);
  const [matches, setMatches] = useState<Record<string, string>>({});

  if (!pairs.length) return <TextAnswerExercise exercise={exercise} onSubmit={onSubmit} disabled={disabled} />;

  function assign(right: string) {
    if (!selectedLeft) return;
    setMatches((current) => {
      const next = { ...current };
      Object.entries(next).forEach(([left, value]) => {
        if (value === right) delete next[left];
      });
      next[selectedLeft] = right;
      return next;
    });
    setSelectedLeft(null);
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2">
          {leftItems.map((left) => (
            <button
              key={left}
              type="button"
              disabled={disabled}
              onClick={() => setSelectedLeft(left)}
              className={`w-full rounded-[18px] border px-4 py-3 text-left text-sm ${selectedLeft === left ? "border-[color:var(--app-accent)] bg-[color:var(--app-accent)]/8" : "border-[color:var(--app-line)] bg-[color:var(--app-elevated)]"}`}
            >
              <p className="font-semibold text-[color:var(--app-text)]">{left}</p>
              <p className="mt-1 text-xs text-[color:var(--app-muted)]">
                {matches[left]
                  ? interpolate(ui("exercise.match_selected", "Matched to {value}"), { value: matches[left] })
                  : ui("exercise.match_hint", "Pick this first, then choose its pair.")}
              </p>
            </button>
          ))}
        </div>
        <div className="space-y-2">
          {rightItems.map((right) => (
            <button
              key={right}
              type="button"
              disabled={disabled || !selectedLeft}
              onClick={() => assign(right)}
              className="w-full rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left text-sm text-[color:var(--app-text)] disabled:opacity-50"
            >
              {right}
            </button>
          ))}
        </div>
      </div>
      <div className="flex gap-2">
        <Button variant="secondary" disabled={disabled || Object.keys(matches).length === 0} onClick={() => { setMatches({}); setSelectedLeft(null); }}>
          {ui("exercise.clear", "Clear")}
        </Button>
        <Button disabled={disabled || Object.keys(matches).length !== leftItems.length} onClick={() => onSubmit(normalizeExerciseSubmission(exercise, matches))}>
          {ui("action.continue", "Continue")}
        </Button>
      </div>
    </div>
  );
}

function FlashcardReviewExercise({ exercise, language, onSubmit, disabled }: Props) {
  const { content, ui } = useI18n();
  const [revealed, setRevealed] = useState(false);
  const knownValue = exercise.options[0]?.value || exercise.answer_key.value || "known";

  return (
    <div className="space-y-3">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setRevealed((current) => !current)}
        className="min-h-36 w-full rounded-[22px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-5 text-left"
      >
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{revealed ? ui("exercise.answer_revealed", "Answer revealed") : ui("exercise.recall_first", "Recall first")}</p>
        <p className="mt-3 text-lg font-semibold leading-8">{revealed ? content(exercise.explanation, ui("exercise.recall_description", "Check your recall.")) : ui("exercise.recall_description", "Pause and try to say it before you reveal the answer.")}</p>
      </button>
      <div className="grid grid-cols-2 gap-2">
        <Button variant="secondary" disabled={disabled} onClick={() => onSubmit(normalizeExerciseSubmission(exercise, "missed"))}>{ui("exercise.missed", "Missed it")}</Button>
        <Button disabled={disabled} onClick={() => onSubmit(normalizeExerciseSubmission(exercise, knownValue))}>{ui("exercise.knew", "Knew it")}</Button>
      </div>
    </div>
  );
}

function orderedTokens(exercise: Exercise): string[] {
  const payloadTokens = Array.isArray(exercise.payload.tokens) ? exercise.payload.tokens.map(String) : [];
  const answerTokens = Array.isArray(exercise.answer_key.value) ? exercise.answer_key.value.map(String) : [];
  const source = payloadTokens.length ? payloadTokens : answerTokens;
  return source.length > 1 ? [...source].reverse() : source;
}

function exercisePairs(exercise: Exercise): Array<[string, string]> {
  const payloadPairs = Array.isArray(exercise.payload.pairs) ? exercise.payload.pairs : [];
  if (payloadPairs.length) {
    return payloadPairs
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
  if (exercise.answer_key.value && typeof exercise.answer_key.value === "object" && !Array.isArray(exercise.answer_key.value)) {
    return Object.entries(exercise.answer_key.value as Record<string, unknown>).map(([left, right]) => [left, String(right)]);
  }
  if (Array.isArray(exercise.answer_key.value)) {
    return exercise.answer_key.value
      .map((item) => {
        if (Array.isArray(item) && item.length === 2) return [String(item[0]), String(item[1])] as [string, string];
        return null;
      })
      .filter((item): item is [string, string] => Boolean(item));
  }
  return [];
}
