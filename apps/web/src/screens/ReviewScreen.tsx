import { Check, Clock3, Ear, Layers3, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ExerciseFeedbackCard } from "../components/exercises/ExerciseFeedbackCard";
import { ExerciseRenderer } from "../components/exercises/ExerciseRenderer";
import { ActionCard, Button, EmptyState, ErrorState, FilterChip, HeroCard, LoadingCard, SectionHeading, StatusChip, Surface } from "../components/ui";
import { useI18n } from "../lib/i18n";
import { track } from "../lib/analytics";
import { api } from "../lib/api";
import { compactDate, compactTime, interpolate } from "../lib/format";
import type { AppRoute, ReviewMode } from "../lib/routes";
import type { AuthUser, Exercise, ExerciseFeedback, Progress, QuizSession, ReviewItem, ReviewOverview } from "../types";

const sizeOptions = [5, 10, 20];

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
  const { content, explanationLanguage, topicLabel, ui } = useI18n();
  const [activeMode, setActiveMode] = useState<ReviewMode>(mode);
  const [sessionSize, setSessionSize] = useState(size);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<Progress | null>(null);
  const [queue, setQueue] = useState<ReviewItem[]>([]);
  const [quizSession, setQuizSession] = useState<QuizSession | null>(null);
  const [feedback, setFeedback] = useState<ExerciseFeedback | null>(null);
  const [busy, setBusy] = useState(false);
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
    setBusy(false);

    const loader = usesQuizMode(activeMode)
      ? api.quizStart(quizPayloadForMode(activeMode, sessionSize))
      : api.reviewQueue(user.telegram_id, activeMode === "mistakes", Math.max(sessionSize * 2, 20));

    Promise.all([api.progress(user.telegram_id), loader])
      .then(([progressValue, result]) => {
        if (cancelled) return;
        setProgress(progressValue);

        if (usesQuizMode(activeMode)) {
          setQuizSession(result as QuizSession);
          setQueue([]);
        } else {
          const items = (result as ReviewItem[])
            .filter((item) => {
              if (activeMode === "vocab") return item.item_type === "vocabulary";
              if (activeMode === "grammar") return item.item_type === "grammar" || item.content.topic === "grammar";
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
      .catch(() => {
        if (!cancelled) setError(ui("review.load_error", "Could not load review content."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeMode, sessionSize, user.telegram_id]);

  const reviewOverview = progress?.review_overview || emptyOverview();
  const reviewSchedule = reviewOverview.schedule || emptyOverview().schedule;
  const reviewItem = queue[currentIndex];
  const quizExercise = quizSession?.exercises[currentIndex] || null;
  const isQuiz = usesQuizMode(activeMode);
  const total = isQuiz ? quizSession?.exercises.length || 0 : queue.length;
  const complete = !loading && total > 0 && currentIndex >= total;
  const modeOptions: Array<{ value: ReviewMode; label: string }> = [
    { value: "due", label: ui("home.review_due_title", "Due review") },
    { value: "mistakes", label: ui("home.mistakes_title", "Mistakes review") },
    { value: "vocab", label: ui("route.vocab", "Vocabulary") },
    { value: "grammar", label: ui("route.grammar", "Grammar") },
    { value: "listening", label: ui("lesson.listen", "Listening") },
    { value: "mixed", label: ui("route.review", "Review") }
  ];

  const title = useMemo(() => {
    const current = modeOptions.find((item) => item.value === activeMode);
    return current?.label || ui("route.review", "Review");
  }, [activeMode, modeOptions, ui]);

  async function answerReview(item: ReviewItem, correct: boolean) {
    setBusy(true);
    try {
      await api.submitReview(user.telegram_id, item.id, correct, correct ? 4 : 1);
      track("review_item_answered", {
        telegram_id: user.telegram_id,
        audience_language: user.interface_language,
        properties: { mode: activeMode, item_type: item.item_type, item_id: item.item_id, correct }
      });
      setCorrectCount((value) => value + (correct ? 1 : 0));
      setCurrentIndex((value) => value + 1);
    } finally {
      setBusy(false);
    }
  }

  async function answerQuiz(exercise: Exercise, answer: unknown) {
    setBusy(true);
    try {
      const result = await api.submitExercise(user.telegram_id, null, exercise.id, answer);
      setFeedback(result);
      track("review_quiz_answered", {
        telegram_id: user.telegram_id,
        audience_language: user.interface_language,
        properties: { mode: activeMode, exercise_id: exercise.id, exercise_type: exercise.exercise_type, correct: result.is_correct }
      });
    } finally {
      setBusy(false);
    }
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
    return <LoadingCard label={ui("route.review", "Review")} />;
  }

  if (error) {
    return <ErrorState description={error} onRetry={() => restart()} />;
  }

  if (complete) {
    const accuracy = total ? Math.round((correctCount / total) * 100) : 0;
    return (
      <div className="space-y-4">
        <HeroCard eyebrow={ui("review.session_complete", "Session complete")} title={interpolate(ui("review.finished", "{title} finished"), { title })} description={interpolate(ui("review.completed_summary", "You completed {count} prompts with {accuracy}% accuracy."), { count: total, accuracy })}>
          <div className="grid grid-cols-2 gap-3">
            <Surface className="p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{ui("review.correct", "Correct")}</p>
              <p className="mt-2 text-2xl font-semibold">{correctCount}</p>
            </Surface>
            <Surface className="p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{ui("review.accuracy", "Accuracy")}</p>
              <p className="mt-2 text-2xl font-semibold">{accuracy}%</p>
            </Surface>
          </div>
        </HeroCard>
        <div className="grid gap-3 sm:grid-cols-2">
          {reviewOverview.guided_sessions.slice(0, 2).map((session) => (
            <ActionCard
              key={session.mode}
              title={session.title}
              description={session.description}
              cta={ui("action.open", "Open")}
              icon={session.mode === "listening" ? Ear : Sparkles}
              tone={session.tone}
              onClick={() => restart(session.mode, session.size)}
            />
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => restart()}>{ui("review.repeat_session", "Repeat session")}</Button>
          <Button variant="secondary" onClick={() => restart("due", 5)}>{ui("home.two_minute_review", "2-minute review")}</Button>
          <Button variant="ghost" onClick={() => onNavigate({ screen: "home" })}>{ui("action.back_home", "Back home")}</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <HeroCard eyebrow={ui("review.center", "Review center")} title={title} description={modeDescription(activeMode, reviewOverview, ui)}>
        <div className="flex flex-wrap gap-2">
          {modeOptions.map((option) => (
            <FilterChip key={option.value} active={option.value === activeMode} onClick={() => restart(option.value, sessionSize)}>
              {option.label}
            </FilterChip>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <StatusChip tone="neutral"><Layers3 size={12} /> {sessionSize} {ui("review.items", "items")}</StatusChip>
          <Button variant="secondary" onClick={() => restart("due", 5)}>{ui("home.two_minute_review", "2-minute review")}</Button>
        </div>
      </HeroCard>

      <Surface>
        <SectionHeading eyebrow={ui("home.spaced_repetition", "Spaced repetition")} title={ui("review.schedule_title", "Scheduled reviews")} description={ui("review.schedule_description", "Use the due queue now, but keep an eye on what is landing over the next day and week.")} />
        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            { key: "due", label: ui("home.due_reviews", "Due reviews"), value: reviewSchedule.due_now },
            { key: "24h", label: ui("home.next_day", "Next 24h"), value: reviewSchedule.next_24h },
            { key: "7d", label: ui("home.next_week", "Next 7d"), value: reviewSchedule.next_7d },
            { key: "mistakes", label: ui("home.mistakes_title", "Mistakes review"), value: reviewSchedule.mistake_queue },
          ].map((item) => (
            <div key={item.key} className="rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{item.label}</p>
              <p className="mt-2 text-2xl font-semibold">{item.value}</p>
            </div>
          ))}
        </div>
        {reviewSchedule.next_review_at ? (
          <div className="mt-4 flex items-center gap-2 text-sm text-[color:var(--app-muted)]">
            <Clock3 size={14} />
            <span>
              {ui("review.next_review_slot", "Next scheduled review")}: {compactDate(reviewSchedule.next_review_at, user.interface_language)} {compactTime(reviewSchedule.next_review_at, user.interface_language)}
            </span>
          </div>
        ) : null}
      </Surface>

      <Surface>
        <SectionHeading eyebrow={ui("review.session_size", "Session size")} title={ui("review.choose_length", "Choose the session length")} />
        <div className="mt-4 flex flex-wrap gap-2">
          {sizeOptions.map((value) => (
            <FilterChip key={value} active={sessionSize === value} onClick={() => restart(activeMode, value)}>
              {value} {ui("review.items", "items")}
            </FilterChip>
          ))}
        </div>
      </Surface>

      {reviewOverview.guided_sessions.length ? (
        <Surface>
          <SectionHeading eyebrow={ui("home.review_now", "Review now")} title={ui("home.attention_first", "What needs attention first")} description={ui("review.center", "Review center")} />
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {reviewOverview.guided_sessions.slice(0, 4).map((session) => (
              <ActionCard
                key={session.mode}
                title={session.title}
                description={`${session.description} ${session.item_count} ${ui("review.items", "items")} ready.`}
                cta={ui("action.open", "Open")}
                icon={session.mode === "listening" ? Ear : Sparkles}
                tone={session.tone}
                onClick={() => restart(session.mode, session.size)}
              />
            ))}
          </div>
        </Surface>
      ) : null}

      <Surface>
        <SectionHeading eyebrow={ui("review.signals", "Signals")} title={ui("review.clustering", "Where mistakes are clustering")} description={ui("progress.trajectory_description", "A compact view of what is working, what is slipping, and what to do next.")} />
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{ui("review.weak_grammar", "Weak grammar")}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {reviewOverview.weak_grammar.length ? reviewOverview.weak_grammar.slice(0, 4).map((item) => <StatusChip key={item.key} tone="warning">{item.label} · {item.mistakes}</StatusChip>) : <span className="text-sm text-[color:var(--app-muted)]">{ui("review.no_grammar_cluster", "No grammar cluster yet.")}</span>}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{ui("review.repeated_mistakes", "Repeated mistakes")}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {reviewOverview.repeated_mistakes.length ? reviewOverview.repeated_mistakes.slice(0, 4).map((item) => <StatusChip key={item.review_item_id} tone="danger">{truncate(item.label)} · {item.mistake_count}</StatusChip>) : <span className="text-sm text-[color:var(--app-muted)]">{ui("review.no_repeated", "No repeated misses right now.")}</span>}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{ui("review.by_type", "By exercise type")}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {reviewOverview.exercise_type_breakdown.length ? reviewOverview.exercise_type_breakdown.slice(0, 5).map((item) => <StatusChip key={item.exercise_type} tone="neutral">{item.exercise_type.replaceAll("_", " ")} · {item.count}</StatusChip>) : <span className="text-sm text-[color:var(--app-muted)]">{ui("review.no_breakdown", "No type breakdown yet.")}</span>}
            </div>
          </div>
        </div>
      </Surface>

      {total === 0 ? (
        <EmptyState
          title={ui("review.empty_title", "Nothing in this queue")}
          description={emptyStateCopy(activeMode, ui)}
          action={<Button onClick={() => onNavigate({ screen: "lesson" })}>{ui("home.continue_lesson", "Continue lesson")}</Button>}
        />
      ) : null}

      {reviewItem ? (
        <Surface>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{interpolate(ui("review.review_item", "Review {current}/{total}"), { current: currentIndex + 1, total })}</p>
              <p className="mt-1 text-sm text-[color:var(--app-muted)]">{reviewItem.item_type} · {reviewItem.mastery_status}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatusChip tone={reviewItem.mistake_count ? "danger" : "neutral"}>{interpolate(ui("review.mistakes_count", "{count} mistakes"), { count: reviewItem.mistake_count })}</StatusChip>
              <StatusChip tone="neutral"><Clock3 size={12} /> {compactDate(reviewItem.next_review_at, user.interface_language)} {compactTime(reviewItem.next_review_at, user.interface_language)}</StatusChip>
            </div>
          </div>
          <p className="mt-4 text-xl font-semibold leading-8">{labelFor(reviewItem, content, ui)}</p>
          {reviewSubtitle(reviewItem, content) ? <p className="mt-2 text-sm leading-6 text-[color:var(--app-muted)]">{reviewSubtitle(reviewItem, content)}</p> : null}
          <div className="mt-4 flex flex-wrap gap-2">
            {contentDifficulty(reviewItem) ? <StatusChip tone="neutral">{contentDifficulty(reviewItem)}</StatusChip> : null}
            {contentExerciseType(reviewItem) ? <StatusChip tone="neutral">{contentExerciseType(reviewItem)?.replaceAll("_", " ")}</StatusChip> : null}
            {contentTopic(reviewItem) ? <StatusChip tone="neutral">{topicLabel(contentTopic(reviewItem) || "")}</StatusChip> : null}
          </div>
          <div className="mt-6 grid grid-cols-2 gap-2">
            <Button variant="secondary" disabled={busy} onClick={() => answerReview(reviewItem, false)}>
              <X size={16} />
              {ui("review.still_shaky", "Still shaky")}
            </Button>
            <Button disabled={busy} onClick={() => answerReview(reviewItem, true)}>
              <Check size={16} />
              {ui("review.solid_now", "Solid now")}
            </Button>
          </div>
        </Surface>
      ) : null}

      {quizExercise ? (
        <div className="space-y-4">
          <Surface>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{title} {currentIndex + 1}/{total}</p>
                <p className="mt-1 text-sm text-[color:var(--app-muted)]">{quizSession?.source || "mixed"} · {topicLabel(quizExercise.topic)}</p>
              </div>
              <StatusChip tone="accent"><Sparkles size={12} /> {ui("review.active_review", "Active review")}</StatusChip>
            </div>
          </Surface>

          <ExerciseRenderer exercise={quizExercise} language={explanationLanguage} onSubmit={(answer) => answerQuiz(quizExercise, answer)} disabled={busy || Boolean(feedback)} />

          {feedback ? (
            <ExerciseFeedbackCard
              exercise={quizExercise}
              feedback={feedback}
              language={explanationLanguage}
              nextLabel={feedback.is_correct ? ui("review.next_item", "Next item") : ui("review.try_again", "Try again")}
              onContinue={advanceQuiz}
            />
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function usesQuizMode(mode: ReviewMode): boolean {
  return ["mistakes", "grammar", "listening", "mixed"].includes(mode);
}

function quizPayloadForMode(mode: ReviewMode, limit: number) {
  if (mode === "mistakes") return { limit, mistakes_only: true };
  if (mode === "grammar") return { limit, focus: "grammar", mistakes_only: true };
  if (mode === "listening") return { limit, focus: "listening", require_audio: true };
  return { limit };
}

function emptyOverview(): ReviewOverview {
  return {
    weak_items: [],
    weak_grammar: [],
    repeated_mistakes: [],
    exercise_type_breakdown: [],
    guided_sessions: [],
    schedule: {
      due_now: 0,
      next_24h: 0,
      next_7d: 0,
      scheduled_total: 0,
      mistake_queue: 0,
      next_review_at: null,
    },
  };
}

function modeDescription(mode: ReviewMode, overview: ReviewOverview, ui: (key: string, fallback?: string) => string): string {
  const guided = overview.guided_sessions.find((item) => item.mode === mode);
  if (guided) return guided.description;
  if (mode === "due") return ui("home.review_due_title", "Due review");
  if (mode === "mistakes") return ui("home.mistakes_title", "Mistakes review");
  if (mode === "grammar") return ui("route.grammar", "Grammar");
  if (mode === "listening") return ui("lesson.listen", "Listening");
  if (mode === "vocab") return ui("route.vocab", "Vocabulary");
  return ui("review.center", "Review center");
}

function emptyStateCopy(mode: ReviewMode, ui: (key: string, fallback?: string) => string): string {
  if (mode === "listening") return ui("scenario.audio_issue_description", "Playback for one or more premium clips is temporarily unavailable. Dialogue study will still work.");
  if (mode === "grammar") return ui("grammar.empty_description", "Try another category or a broader search.");
  if (mode === "mistakes") return ui("home.no_mistake_queue", "No open mistake queue right now.");
  if (mode === "mixed") return ui("review.center", "Review center");
  return ui("review.empty_title", "Nothing in this queue");
}

function labelFor(item: ReviewItem, content: (text: Record<string, string> | undefined, fallback?: string) => string, ui: (key: string, fallback?: string) => string): string {
  const prompt = item.content.prompt as Record<string, string> | undefined;
  if (prompt) return content(prompt, ui("exercise.prompt", "Exercise prompt"));
  if (typeof item.content.korean === "string") return item.content.korean;
  if (typeof item.content.pattern === "string") return item.content.pattern;
  return ui("review.center", "Review");
}

function reviewSubtitle(item: ReviewItem, content: (text: Record<string, string> | undefined, fallback?: string) => string): string {
  if (item.item_type === "vocabulary" && item.content.translations) {
    return content(item.content.translations as Record<string, string>);
  }
  if (item.item_type === "grammar" && item.content.title) {
    return content(item.content.title as Record<string, string>);
  }
  return "";
}

function contentExerciseType(item: ReviewItem): string | null {
  return typeof item.content.exercise_type === "string" ? item.content.exercise_type : null;
}

function contentDifficulty(item: ReviewItem): string | null {
  return typeof item.content.difficulty === "string" ? item.content.difficulty : null;
}

function contentTopic(item: ReviewItem): string | null {
  return typeof item.content.topic === "string" ? item.content.topic : null;
}

function truncate(value: string, max = 28): string {
  return value.length <= max ? value : `${value.slice(0, max - 3)}...`;
}
