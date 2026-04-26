import { Check, Clock3, Flame, Layers3, RefreshCcw, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button, EmptyState, ErrorState, FilterChip, HeroCard, LoadingCard, SectionHeading, StatusChip, Surface } from "../components/ui";
import { ExerciseRenderer } from "../components/exercises/ExerciseRenderer";
import { track } from "../lib/analytics";
import { compactDate, compactTime, t, topicLabel } from "../lib/format";
import { api } from "../lib/api";
import type { AppRoute, ReviewMode } from "../lib/routes";
import type { AuthUser, Exercise, QuizSession, ReviewItem } from "../types";

const sizeOptions = [5, 10, 20];
const modeOptions: Array<{ value: ReviewMode; label: string }> = [
  { value: "due", label: "Due review" },
  { value: "mistakes", label: "Mistakes" },
  { value: "vocab", label: "Vocabulary" },
  { value: "grammar", label: "Grammar" },
  { value: "mixed", label: "Mixed quick review" }
];

type QuizFeedback = {
  is_correct: boolean;
  expected: unknown;
  explanation: Record<string, string>;
};

export function ReviewScreen({
  user,
  mode = "due",
  size = 10,
  onNavigate
}: {
  user: AuthUser;
  mode?: ReviewMode;
  size?: number;
  onNavigate: (route: AppRoute) => void;
}) {
  const [activeMode, setActiveMode] = useState<ReviewMode>(mode);
  const [sessionSize, setSessionSize] = useState(size);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [queue, setQueue] = useState<ReviewItem[]>([]);
  const [quizSession, setQuizSession] = useState<QuizSession | null>(null);
  const [feedback, setFeedback] = useState<QuizFeedback | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);

  useEffect(() => {
    setActiveMode(mode);
    setSessionSize(size);
  }, [mode, size]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    setCurrentIndex(0);
    setCorrectCount(0);
    setFeedback(null);

    const loader =
      activeMode === "mixed"
        ? api.quizStart({ limit: sessionSize })
        : api.reviewQueue(user.telegram_id, activeMode === "mistakes", Math.max(sessionSize * 2, 20));

    loader
      .then((result) => {
        if (cancelled) return;
        if (activeMode === "mixed") {
          setQuizSession(result as QuizSession);
          setQueue([]);
        } else {
          const items = (result as ReviewItem[])
            .filter((item) => {
              if (activeMode === "vocab") return item.item_type === "vocabulary";
              if (activeMode === "grammar") return item.item_type === "grammar";
              return true;
            })
            .slice(0, sessionSize);
          setQueue(items);
          setQuizSession(null);
        }

        track("review_session_started", {
          telegram_id: user.telegram_id,
          audience_language: user.interface_language,
          properties: { mode: activeMode, size: sessionSize }
        });
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load review content.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeMode, sessionSize, user.interface_language, user.telegram_id]);

  const reviewItem = queue[currentIndex];
  const quizExercise = quizSession?.exercises[currentIndex] || null;
  const isMixed = activeMode === "mixed";
  const total = isMixed ? quizSession?.exercises.length || 0 : queue.length;
  const complete = !loading && total > 0 && currentIndex >= total;

  const title = useMemo(() => {
    const current = modeOptions.find((item) => item.value === activeMode);
    return current?.label || "Review";
  }, [activeMode]);

  async function answerReview(item: ReviewItem, correct: boolean) {
    await api.submitReview(user.telegram_id, item.id, correct, correct ? 4 : 1);
    track("review_item_answered", {
      telegram_id: user.telegram_id,
      audience_language: user.interface_language,
      properties: { mode: activeMode, item_type: item.item_type, item_id: item.item_id, correct }
    });
    setCorrectCount((value) => value + (correct ? 1 : 0));
    setCurrentIndex((value) => value + 1);
  }

  async function answerQuiz(exercise: Exercise, answer: unknown) {
    const result = await api.submitExercise(user.telegram_id, null, exercise.id, answer);
    setFeedback(result);
    track("review_quiz_answered", {
      telegram_id: user.telegram_id,
      audience_language: user.interface_language,
      properties: { mode: activeMode, exercise_id: exercise.id, correct: result.is_correct }
    });
  }

  function advanceQuiz() {
    if (feedback?.is_correct) {
      setCorrectCount((value) => value + 1);
      setCurrentIndex((value) => value + 1);
    }
    setFeedback(null);
  }

  function restart(modeOverride?: ReviewMode, sizeOverride?: number) {
    onNavigate({
      screen: "review",
      mode: modeOverride || activeMode,
      size: sizeOverride || sessionSize,
      shortcut: sizeOverride === 5 ? "two-minute" : undefined
    });
  }

  if (loading) {
    return <LoadingCard label="Loading review" />;
  }

  if (error) {
    return <ErrorState description={error} onRetry={() => restart()} />;
  }

  if (complete) {
    const accuracy = total ? Math.round((correctCount / total) * 100) : 0;
    return (
      <div className="space-y-4">
        <HeroCard eyebrow="Session complete" title={`${title} finished`} description={`You completed ${total} prompts with ${accuracy}% accuracy.`}>
          <div className="grid grid-cols-2 gap-3">
            <Surface className="p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">Correct</p>
              <p className="mt-2 text-2xl font-semibold">{correctCount}</p>
            </Surface>
            <Surface className="p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">Accuracy</p>
              <p className="mt-2 text-2xl font-semibold">{accuracy}%</p>
            </Surface>
          </div>
        </HeroCard>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => restart()}>Repeat session</Button>
          <Button variant="secondary" onClick={() => restart("due", 5)}>2-minute review</Button>
          <Button variant="ghost" onClick={() => onNavigate({ screen: "home" })}>Back home</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <HeroCard eyebrow="Review center" title={title} description="Use short, deliberate passes. The session size controls make review fit the Telegram rhythm.">
        <div className="flex flex-wrap gap-2">
          {modeOptions.map((option) => (
            <FilterChip key={option.value} active={option.value === activeMode} onClick={() => restart(option.value, sessionSize)}>
              {option.label}
            </FilterChip>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <StatusChip tone="neutral"><Layers3 size={12} /> {sessionSize} items</StatusChip>
          <Button variant="secondary" onClick={() => restart("due", 5)}>2-minute review</Button>
        </div>
      </HeroCard>

      <Surface>
        <SectionHeading eyebrow="Session size" title="Choose the session length" />
        <div className="mt-4 flex flex-wrap gap-2">
          {sizeOptions.map((value) => (
            <FilterChip key={value} active={sessionSize === value} onClick={() => restart(activeMode, value)}>
              {value} items
            </FilterChip>
          ))}
        </div>
      </Surface>

      {total === 0 ? (
        <EmptyState title="Nothing in this queue" description={activeMode === "mixed" ? "No quick-review prompts are available right now." : "This queue is clear. Try another review mode or continue your lesson."} action={<Button onClick={() => onNavigate({ screen: "lesson" })}>Open lesson</Button>} />
      ) : null}

      {reviewItem ? (
        <div className="space-y-4">
          <Surface>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">Review {currentIndex + 1}/{total}</p>
                <p className="mt-1 text-sm text-[color:var(--app-muted)]">{reviewItem.item_type} • {reviewItem.mastery_status}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusChip tone={reviewItem.mistake_count ? "danger" : "neutral"}>{reviewItem.mistake_count} mistakes</StatusChip>
                <StatusChip tone="neutral"><Clock3 size={12} /> {compactDate(reviewItem.next_review_at)} {compactTime(reviewItem.next_review_at)}</StatusChip>
              </div>
            </div>
            <p className="mt-4 text-xl font-semibold leading-8">{labelFor(reviewItem, user.interface_language)}</p>
            {reviewItem.item_type === "vocabulary" && reviewItem.content.translations ? (
              <p className="mt-2 text-sm leading-6 text-[color:var(--app-muted)]">{t(reviewItem.content.translations as Record<string, string>, user.interface_language)}</p>
            ) : null}
            {typeof reviewItem.content.topic === "string" ? <div className="mt-4"><StatusChip tone="neutral">{topicLabel(reviewItem.content.topic as string)}</StatusChip></div> : null}
            <div className="mt-6 grid grid-cols-2 gap-2">
              <Button variant="secondary" onClick={() => answerReview(reviewItem, false)}>
                <X size={16} />
                Missed
              </Button>
              <Button onClick={() => answerReview(reviewItem, true)}>
                <Check size={16} />
                Knew it
              </Button>
            </div>
          </Surface>
        </div>
      ) : null}

      {quizExercise ? (
        <div className="space-y-4">
          <Surface>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">Mixed review {currentIndex + 1}/{total}</p>
                <p className="mt-1 text-sm text-[color:var(--app-muted)]">{quizSession?.source || "mixed"} • {topicLabel(quizExercise.topic)}</p>
              </div>
              <StatusChip tone="accent"><Sparkles size={12} /> Quick review</StatusChip>
            </div>
          </Surface>

          <ExerciseRenderer exercise={quizExercise} language={user.interface_language} onSubmit={(answer) => answerQuiz(quizExercise, answer)} disabled={Boolean(feedback)} />

          {feedback ? (
            <Surface className={feedback.is_correct ? "border-emerald-500/20 bg-emerald-500/5" : "border-[color:var(--app-secondary)]/20 bg-[color:var(--app-secondary)]/5"}>
              <SectionHeading title={feedback.is_correct ? "Correct" : "Review the answer"} description={t(feedback.explanation, user.interface_language, feedback.is_correct ? "Move on to the next item." : "Use the explanation, then try again.")} />
              {!feedback.is_correct ? (
                <p className="mt-4 rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-sm text-[color:var(--app-text)]">Expected: {JSON.stringify(feedback.expected)}</p>
              ) : null}
              <div className="mt-4">
                <Button onClick={advanceQuiz}>{feedback.is_correct ? "Next item" : "Try again"}</Button>
              </div>
            </Surface>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function labelFor(item: ReviewItem, language: AuthUser["interface_language"]): string {
  const prompt = item.content.prompt as Record<string, string> | undefined;
  if (prompt) return t(prompt, language, "Review item");
  if (typeof item.content.korean === "string") return item.content.korean;
  if (typeof item.content.pattern === "string") return item.content.pattern;
  return "Review item";
}
