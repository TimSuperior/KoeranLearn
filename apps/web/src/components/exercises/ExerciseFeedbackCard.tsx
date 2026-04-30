import { Check, RotateCcw, Sparkles } from "lucide-react";

import { useI18n } from "../../lib/i18n";
import type { Exercise, ExerciseFeedback, Language } from "../../types";
import { Button, SectionHeading, StatusChip, Surface } from "../ui";
import { formatExpectedAnswer } from "./exerciseMeta";

export function ExerciseFeedbackCard({
  exercise,
  feedback,
  language,
  nextLabel,
  onContinue
}: {
  exercise: Exercise;
  feedback: ExerciseFeedback;
  language: Language;
  nextLabel: string;
  onContinue: () => void;
}) {
  const { content, ui } = useI18n();
  const expectedLines = feedback.is_correct ? [] : formatExpectedAnswer(exercise, feedback.expected, language);

  return (
    <Surface className={feedback.is_correct ? "border-emerald-500/20 bg-emerald-500/5" : "border-[color:var(--app-secondary)]/20 bg-[color:var(--app-secondary)]/5"}>
      <SectionHeading
        eyebrow={feedback.is_correct ? ui("feedback.checked", "Answer checked") : ui("feedback.try_again", "Try again")}
        title={feedback.is_correct ? ui("feedback.correct", "Correct") : ui("feedback.not_yet", "Not quite yet")}
        description={content(feedback.explanation, feedback.is_correct ? ui("feedback.correct", "Correct") : ui("feedback.try_again", "Try again"))}
      />
      {expectedLines.length ? (
        <div className="mt-4 rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{ui("feedback.expected", "Expected answer")}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {expectedLines.map((line) => (
              <StatusChip key={line} tone="neutral">{line}</StatusChip>
            ))}
          </div>
        </div>
      ) : null}
      <div className="mt-4 flex items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          <StatusChip tone={feedback.is_correct ? "success" : "warning"}>
            {feedback.is_correct ? <Check size={12} /> : <RotateCcw size={12} />}
            {ui("exercise.prompt", "Exercise")}
          </StatusChip>
          {typeof feedback.xp_awarded === "number" ? (
            <StatusChip tone={feedback.is_correct ? "success" : "neutral"}>
              <Sparkles size={12} />
              {feedback.xp_awarded} XP
            </StatusChip>
          ) : null}
        </div>
        <Button onClick={onContinue}>{nextLabel}</Button>
      </div>
    </Surface>
  );
}
