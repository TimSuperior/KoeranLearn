import { RotateCcw, Send } from "lucide-react";
import { useMemo, useState } from "react";
import { Button, Field, SelectInput, Surface, TextArea, TextInput } from "../ui";
import { t } from "../../lib/format";
import type { Exercise, Language } from "../../types";

type Props = {
  exercise: Exercise;
  language: Language;
  onSubmit: (answer: unknown) => void;
  disabled?: boolean;
  compact?: boolean;
};

export function ExerciseRenderer({ exercise, language, onSubmit, disabled = false, compact = false }: Props) {
  return (
    <Surface className={compact ? "p-4" : ""}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{exercise.exercise_type.replaceAll("_", " ")}</p>
        <span className="rounded-full border border-[color:var(--app-line)] px-2.5 py-1 text-[11px] font-semibold text-[color:var(--app-muted)]">{exercise.topic}</span>
      </div>
      <p className="mt-3 text-lg font-semibold leading-8 text-[color:var(--app-text)]">{t(exercise.prompt, language, "Exercise prompt")}</p>
      {t(exercise.instructions, language) ? <p className="mt-2 text-sm leading-6 text-[color:var(--app-muted)]">{t(exercise.instructions, language)}</p> : null}
      <div className="mt-4">
        <Renderer exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} />
      </div>
    </Surface>
  );
}

function Renderer({ exercise, language, onSubmit, disabled }: Props) {
  if (["multiple_choice", "choose_particle", "choose_verb_ending", "translation_selection", "dialogue_continuation", "reading_comprehension", "listen_and_choose", "true_false"].includes(exercise.exercise_type)) {
    return <OptionButtons exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} />;
  }
  if (["sentence_reorder", "sentence_reordering", "listen_and_order"].includes(exercise.exercise_type)) {
    return <SentenceReorder exercise={exercise} onSubmit={onSubmit} disabled={disabled} />;
  }
  if (["match_pairs", "match_korean_translation", "match_word_usage", "listen_and_match"].includes(exercise.exercise_type)) {
    return <MatchPairs onSubmit={onSubmit} disabled={disabled} />;
  }
  if (exercise.exercise_type === "flashcard_review") {
    return <Flashcard exercise={exercise} language={language} onSubmit={onSubmit} disabled={disabled} />;
  }
  return <TextAnswer onSubmit={onSubmit} disabled={disabled} />;
}

function OptionButtons({ exercise, language, onSubmit, disabled }: Props) {
  return (
    <div className="grid gap-2">
      {exercise.options.map((option) => (
        <button
          type="button"
          key={option.id}
          disabled={disabled}
          onClick={() => onSubmit(option.value)}
          className="min-h-12 rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left text-sm font-medium text-[color:var(--app-text)] transition hover:border-[color:var(--app-accent)] disabled:opacity-50"
        >
          {t(option.label, language)}
        </button>
      ))}
      {exercise.options.length === 0 ? <TextAnswer onSubmit={onSubmit} disabled={disabled} /> : null}
    </div>
  );
}

function TextAnswer({ onSubmit, disabled }: { onSubmit: (answer: unknown) => void; disabled?: boolean }) {
  const [value, setValue] = useState("");
  return (
    <div className="space-y-3">
      <Field label="Your answer">
        <TextInput value={value} onChange={(event) => setValue(event.target.value)} placeholder="한국어" disabled={disabled} />
      </Field>
      <Button disabled={disabled || !value.trim()} onClick={() => onSubmit(value.trim())}>
        Submit
        <Send size={16} />
      </Button>
    </div>
  );
}

function SentenceReorder({ exercise, onSubmit, disabled }: { exercise: Exercise; onSubmit: (answer: unknown) => void; disabled?: boolean }) {
  const tokens = useMemo(() => (Array.isArray(exercise.payload.tokens) ? exercise.payload.tokens.map(String) : []), [exercise.payload.tokens]);
  const [available, setAvailable] = useState(tokens);
  const [answer, setAnswer] = useState<string[]>([]);

  function reset() {
    setAvailable(tokens);
    setAnswer([]);
  }

  if (!tokens.length) return <TextAnswer onSubmit={onSubmit} disabled={disabled} />;

  return (
    <div className="space-y-3">
      <div className="min-h-16 rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-3">
        <div className="flex flex-wrap gap-2">
          {answer.map((token, index) => (
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
          ))}
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
        <Button disabled={disabled || answer.length === 0} onClick={() => onSubmit(answer)}>
          Submit
        </Button>
      </div>
    </div>
  );
}

function MatchPairs({ onSubmit, disabled }: { onSubmit: (answer: unknown) => void; disabled?: boolean }) {
  const [value, setValue] = useState("");
  return (
    <div className="space-y-3">
      <Field label="Pair the terms" hint="Use value=meaning, comma separated">
        <TextArea value={value} disabled={disabled} onChange={(event) => setValue(event.target.value)} placeholder="물=water, 학교=school" />
      </Field>
      <Button
        disabled={disabled || !value.trim()}
        onClick={() => {
          const answer = Object.fromEntries(
            value
              .split(",")
              .map((pair) => pair.split("=").map((item) => item.trim()))
              .filter((pair) => pair.length === 2)
          );
          onSubmit(answer);
        }}
      >
        Submit
      </Button>
    </div>
  );
}

function Flashcard({ exercise, language, onSubmit, disabled }: Props) {
  const [revealed, setRevealed] = useState(false);
  const value = exercise.options[0]?.value || "known";
  return (
    <div className="space-y-3">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setRevealed((current) => !current)}
        className="min-h-36 w-full rounded-[22px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-5 text-left"
      >
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{revealed ? "Meaning" : "Tap to reveal"}</p>
        <p className="mt-3 text-lg font-semibold leading-8">{revealed ? t(exercise.explanation, language, "Check your recall.") : "Think first, then reveal."}</p>
      </button>
      <div className="grid grid-cols-2 gap-2">
        <Button variant="secondary" disabled={disabled} onClick={() => onSubmit("missed")}>Missed</Button>
        <Button disabled={disabled} onClick={() => onSubmit(value)}>Knew it</Button>
      </div>
    </div>
  );
}
