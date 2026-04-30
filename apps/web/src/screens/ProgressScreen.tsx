import { ArrowRight, BookOpenCheck, Flame, Repeat2, Sparkles, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";

import { ActionCard, Button, EmptyState, ErrorState, LoadingCard, MetricCard, SectionHeading, StatusChip, Surface } from "../components/ui";
import { useI18n } from "../lib/i18n";
import { api } from "../lib/api";
import { interpolate } from "../lib/format";
import type { AppRoute } from "../lib/routes";
import type { AuthUser, Progress, Scenario } from "../types";

type StreakSummary = {
  streak_count: number;
  xp: number;
  due_reviews: number;
  next_milestone: number;
  weekly_activity: Array<{ day_offset: number; active: boolean }>;
};

export function ProgressScreen({ user, onNavigate }: { user: AuthUser; onNavigate: (route: AppRoute) => void }) {
  const { content, topicLabel, ui } = useI18n();
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
      .catch(() => {
        if (!cancelled) setError(ui("progress.load_error", "Could not load progress."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user.telegram_id]);

  const guidedSessions = progress?.review_overview.guided_sessions.slice(0, 3) || [];
  const activeScenario = scenarios.find((scenario) => scenario.progress?.status === "in_progress");
  const topRecommendation = guidedSessions[0]
    ? {
        title: guidedSessions[0].title,
        description: `${guidedSessions[0].description} ${guidedSessions[0].item_count} ${ui("review.items", "items")} ready.`,
        route: { screen: "review", mode: guidedSessions[0].mode, size: guidedSessions[0].size } as AppRoute
      }
    : (progress?.due_reviews || 0) > 0
      ? {
          title: ui("progress.clear_due_title", "Clear your due reviews"),
          description: interpolate(ui("progress.clear_due_description", "{count} items are waiting. A short review session will improve retention before the next lesson."), {
            count: progress?.due_reviews || 0
          }),
          route: { screen: "review", mode: "due", size: 10 } as AppRoute
        }
      : (progress?.mistake_reviews || 0) > 0
        ? {
            title: ui("progress.repair_title", "Repair recent mistakes"),
            description: interpolate(ui("progress.repair_description", "{count} items need a focused retry."), {
              count: progress?.mistake_reviews || 0
            }),
            route: { screen: "review", mode: "mistakes", size: 10 } as AppRoute
          }
        : activeScenario
          ? {
              title: ui("progress.finish_scenario_title", "Finish your active scenario"),
              description: ui("progress.finish_scenario_description", "Keep reading and listening momentum with the scenario you already started."),
              route: { screen: "scenarios", scenario: activeScenario.slug } as AppRoute
            }
          : {
              title: ui("progress.continue_path_title", "Continue the guided path"),
              description: ui("progress.continue_path_description", "Your lesson track is ready. Push the next lesson forward while your streak is warm."),
              route: { screen: "lesson" } as AppRoute
            };

  if (loading) {
    return (
      <div className="space-y-4">
        <LoadingCard label={ui("progress.loading", "Loading progress")} />
        <div className="grid grid-cols-2 gap-3">
          <LoadingCard label={ui("progress.overview", "Overview")} />
          <LoadingCard label={ui("progress.review_health", "Review health")} />
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorState description={error} onRetry={() => window.location.reload()} />;
  }

  if (!progress || !streak) {
    return <EmptyState title={ui("progress.no_data_title", "No progress yet")} description={ui("progress.no_data_description", "Complete your first lesson and your learning stats will appear here.")} />;
  }

  const reviewHealth =
    progress.due_reviews === 0
      ? ui("progress.review_health_healthy", "Healthy")
      : progress.due_reviews <= 10
        ? ui("progress.review_health_manageable", "Manageable")
        : ui("progress.review_health_attention", "Needs attention");

  return (
    <div className="space-y-4">
      <Surface>
        <SectionHeading eyebrow={ui("progress.overview", "Overview")} title={ui("progress.trajectory", "Your learning trajectory")} description={ui("progress.trajectory_description", "A compact view of what is working, what is slipping, and what to do next.")} />
        <div className="mt-4 grid grid-cols-2 gap-3">
          <MetricCard label={ui("home.completed", "Completed")} value={progress.completed_lessons} detail={ui("home.completed_detail", "Lessons finished")} icon={BookOpenCheck} tone="accent" />
          <MetricCard label={ui("home.streak", "Streak")} value={streak.streak_count} detail={interpolate(ui("home.streak_next", "Next {count}"), { count: streak.next_milestone })} icon={Flame} tone="warning" />
          <MetricCard label={ui("home.xp", "XP")} value={progress.xp} detail={ui("home.xp_detail", "All-time study points")} icon={Sparkles} tone="success" />
          <MetricCard label={ui("progress.review_health", "Review health")} value={reviewHealth} detail={`${progress.due_reviews} ${ui("route.review", "Review")} • ${progress.mistake_reviews} ${ui("home.mistakes_title", "Mistakes")}`} icon={Repeat2} tone="neutral" />
        </div>
      </Surface>

      {guidedSessions.length ? (
        <Surface>
          <SectionHeading eyebrow={ui("home.review_now", "Review now")} title={ui("home.attention_first", "What needs attention first")} description={ui("review.center", "Review center")} />
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {guidedSessions.map((session) => (
              <ActionCard
                key={session.mode}
                title={session.title}
                description={`${session.description} ${session.item_count} ${ui("review.items", "items")} ready.`}
                cta={ui("home.review_due_open", "Open review")}
                icon={TrendingUp}
                tone={session.tone}
                onClick={() => onNavigate({ screen: "review", mode: session.mode, size: session.size })}
              />
            ))}
          </div>
        </Surface>
      ) : null}

      <Surface>
        <SectionHeading
          eyebrow={ui("progress.path", "Path")}
          title={progress.current_path ? content(progress.current_path.title, ui("progress.current_path", "Current path")) : ui("progress.current_path", "Current path")}
          description={progress.current_module ? content(progress.current_module.title, ui("progress.guided_curriculum", "Guided curriculum")) : ui("progress.guided_curriculum", "Guided curriculum")}
        />
        <div className="mt-4 h-3 overflow-hidden rounded-full bg-black/6">
          <div className="h-full rounded-full bg-[linear-gradient(90deg,var(--app-accent),#4ca483)]" style={{ width: `${progress.current_path?.percent_complete || 0}%` }} />
        </div>
        <div className="mt-3 flex items-center justify-between text-sm text-[color:var(--app-muted)]">
          <span>{progress.current_path?.completed_lessons || 0}/{progress.current_path?.total_lessons || 0} {ui("progress.complete_lessons", "lessons complete")}</span>
          <span>{Math.round(progress.current_path?.percent_complete || 0)}%</span>
        </div>
        <div className="mt-4 rounded-[22px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--app-muted)]">{ui("progress.current_lesson", "Current lesson")}</p>
          <p className="mt-2 text-base font-semibold">{progress.current_lesson ? content(progress.current_lesson.title, ui("home.no_lesson_active", "No lesson active")) : ui("home.no_lesson_active", "No lesson active")}</p>
          {progress.current_lesson?.summary ? <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{content(progress.current_lesson.summary)}</p> : null}
          <div className="mt-4">
            <Button onClick={() => onNavigate({ screen: "lesson", lessonId: progress.current_lesson?.id })}>
              {ui("progress.continue_lesson", "Continue lesson")}
              <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      </Surface>

      <Surface>
        <SectionHeading eyebrow={ui("progress.habit", "Habit")} title={ui("progress.weekly_rhythm", "Weekly study rhythm")} description={ui("progress.habit_description", "Consistency matters more than intensity in the first months.")} />
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
              <span className="text-xs font-semibold">{item.active ? ui("home.on", "On") : ui("home.off", "Off")}</span>
            </div>
          ))}
        </div>
      </Surface>

      <div className="grid gap-4 md:grid-cols-2">
        <Surface>
          <SectionHeading eyebrow={ui("progress.weak_areas", "Weak areas")} title={ui("progress.weak_areas_title", "Topics that need extra touchpoints")} />
          <div className="mt-4 flex flex-wrap gap-2">
            {progress.difficult_topics.length ? (
              progress.difficult_topics.map((item) => <StatusChip key={item.topic} tone="warning">{topicLabel(item.topic)}</StatusChip>)
            ) : (
              <p className="text-sm leading-6 text-[color:var(--app-muted)]">{ui("progress.no_weak_areas", "No repeated weak areas yet. Keep building variety.")}</p>
            )}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {progress.review_overview.weak_grammar.slice(0, 4).map((item) => <StatusChip key={item.key} tone="warning">{item.label} · {item.mistakes}</StatusChip>)}
            {progress.review_overview.repeated_mistakes.slice(0, 3).map((item) => <StatusChip key={item.review_item_id} tone="danger">{item.mistake_count}x repeat</StatusChip>)}
          </div>
        </Surface>

        <Surface>
          <SectionHeading eyebrow={ui("progress.recommendations", "Recommendations")} title={ui("progress.next", "What to do next")} />
          <div className="mt-4 space-y-3">
            <ActionCard title={topRecommendation.title} description={topRecommendation.description} cta={ui("action.open", "Open")} icon={TrendingUp} onClick={() => onNavigate(topRecommendation.route)} />
          </div>
        </Surface>
      </div>
    </div>
  );
}
