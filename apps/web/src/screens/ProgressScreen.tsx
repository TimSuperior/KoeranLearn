import { ArrowRight, BookOpenCheck, Flame, Repeat2, Sparkles, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { ActionCard, Button, EmptyState, ErrorState, LoadingCard, MetricCard, SectionHeading, StatusChip, Surface } from "../components/ui";
import { t, topicLabel } from "../lib/format";
import type { AppRoute } from "../lib/routes";
import { api } from "../lib/api";
import type { AuthUser, Progress, Scenario } from "../types";

type StreakSummary = {
  streak_count: number;
  xp: number;
  due_reviews: number;
  next_milestone: number;
  weekly_activity: Array<{ day_offset: number; active: boolean }>;
};

export function ProgressScreen({ user, onNavigate }: { user: AuthUser; onNavigate: (route: AppRoute) => void }) {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [streak, setStreak] = useState<StreakSummary | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    Promise.all([api.progress(user.telegram_id), api.streak(), api.scenarios()])
      .then(([progressValue, streakValue, scenarioValue]) => {
        if (cancelled) return;
        setProgress(progressValue);
        setStreak(streakValue);
        setScenarios(scenarioValue);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load progress.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user.telegram_id]);

  const topRecommendation =
    (progress?.due_reviews || 0) > 0
      ? {
          title: "Clear your due reviews",
          description: `${progress?.due_reviews || 0} items are waiting. A short review session will improve retention before the next lesson.`,
          route: { screen: "review", mode: "due", size: 10 } as AppRoute
        }
      : (progress?.mistake_reviews || 0) > 0
        ? {
            title: "Repair recent mistakes",
            description: `${progress?.mistake_reviews || 0} items need a focused retry.`,
            route: { screen: "review", mode: "mistakes", size: 10 } as AppRoute
          }
        : scenarios.find((scenario) => scenario.progress?.status === "in_progress")
          ? {
              title: "Finish your active scenario",
              description: "Keep reading and listening momentum with the scenario you already started.",
              route: { screen: "scenarios", scenario: scenarios.find((scenario) => scenario.progress?.status === "in_progress")?.slug } as AppRoute
            }
          : {
              title: "Continue the guided path",
              description: "Your lesson track is ready. Push the next lesson forward while your streak is warm.",
              route: { screen: "lesson" } as AppRoute
            };

  if (loading) {
    return (
      <div className="space-y-4">
        <LoadingCard label="Loading progress" />
        <div className="grid grid-cols-2 gap-3">
          <LoadingCard label="Stats" />
          <LoadingCard label="Stats" />
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorState description={error} onRetry={() => window.location.reload()} />;
  }

  if (!progress || !streak) {
    return <EmptyState title="No progress yet" description="Complete your first lesson and your learning stats will appear here." />;
  }

  const reviewHealth = progress.due_reviews === 0 ? "Healthy" : progress.due_reviews <= 10 ? "Manageable" : "Needs attention";

  return (
    <div className="space-y-4">
      <Surface>
        <SectionHeading eyebrow="Overview" title="Your learning trajectory" description="A compact view of what is working, what is slipping, and what to do next." />
        <div className="mt-4 grid grid-cols-2 gap-3">
          <MetricCard label="Completed" value={progress.completed_lessons} detail="Lessons finished" icon={BookOpenCheck} tone="accent" />
          <MetricCard label="Streak" value={streak.streak_count} detail={`Next milestone ${streak.next_milestone}`} icon={Flame} tone="warning" />
          <MetricCard label="XP" value={progress.xp} detail="Lifetime momentum" icon={Sparkles} tone="success" />
          <MetricCard label="Review health" value={reviewHealth} detail={`${progress.due_reviews} due • ${progress.mistake_reviews} mistakes`} icon={Repeat2} tone="neutral" />
        </div>
      </Surface>

      <Surface>
        <SectionHeading eyebrow="Path" title={progress.current_path ? t(progress.current_path.title, user.interface_language, "Korean from zero") : "Current path"} description={progress.current_module ? t(progress.current_module.title, user.interface_language) : "Guided curriculum"} />
        <div className="mt-4 h-3 overflow-hidden rounded-full bg-black/6">
          <div className="h-full rounded-full bg-[linear-gradient(90deg,var(--app-accent),#4ca483)]" style={{ width: `${progress.current_path?.percent_complete || 0}%` }} />
        </div>
        <div className="mt-3 flex items-center justify-between text-sm text-[color:var(--app-muted)]">
          <span>{progress.current_path?.completed_lessons || 0}/{progress.current_path?.total_lessons || 0} lessons complete</span>
          <span>{Math.round(progress.current_path?.percent_complete || 0)}%</span>
        </div>
        <div className="mt-4 rounded-[22px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--app-muted)]">Current lesson</p>
          <p className="mt-2 text-base font-semibold">{progress.current_lesson ? t(progress.current_lesson.title, user.interface_language) : "No lesson active"}</p>
          {progress.current_lesson?.summary ? <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{t(progress.current_lesson.summary, user.interface_language)}</p> : null}
          <div className="mt-4">
            <Button onClick={() => onNavigate({ screen: "lesson", lessonId: progress.current_lesson?.id })}>
              Continue lesson
              <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      </Surface>

      <Surface>
        <SectionHeading eyebrow="Habit" title="Weekly study rhythm" description="Consistency matters more than intensity in the first months." />
        <div className="mt-4 grid grid-cols-7 gap-2">
          {streak.weekly_activity.map((item) => (
            <div
              key={item.day_offset}
              className={`flex h-20 items-end justify-center rounded-[18px] border px-2 pb-3 ${
                item.active
                  ? "border-[color:var(--app-accent)]/20 bg-[color:var(--app-accent)]/10 text-[color:var(--app-accent)]"
                  : "border-[color:var(--app-line)] bg-[color:var(--app-elevated)] text-[color:var(--app-muted)]"
              }`}
            >
              <span className="text-xs font-semibold">{item.active ? "On" : "Off"}</span>
            </div>
          ))}
        </div>
      </Surface>

      <div className="grid gap-4 md:grid-cols-2">
        <Surface>
          <SectionHeading eyebrow="Weak areas" title="Topics that need extra touchpoints" />
          <div className="mt-4 flex flex-wrap gap-2">
            {progress.difficult_topics.length ? (
              progress.difficult_topics.map((item) => <StatusChip key={item.topic} tone="warning">{topicLabel(item.topic)}</StatusChip>)
            ) : (
              <p className="text-sm leading-6 text-[color:var(--app-muted)]">No repeated weak areas yet. Keep building variety.</p>
            )}
          </div>
        </Surface>

        <Surface>
          <SectionHeading eyebrow="Recommendations" title="What to do next" />
          <div className="mt-4 space-y-3">
            <ActionCard
              title={topRecommendation.title}
              description={topRecommendation.description}
              cta="Open"
              icon={TrendingUp}
              onClick={() => onNavigate(topRecommendation.route)}
            />
          </div>
        </Surface>
      </div>
    </div>
  );
}
