import { BookOpen, Clock3, Ear, Flame, GraduationCap, Languages, MessageCircleMore, Repeat2, Sparkles, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ActionCard, Button, EmptyState, ErrorState, HeroCard, MetricCard, SectionHeading, StatusChip, Surface } from "../components/ui";
import { useI18n } from "../lib/i18n";
import { track } from "../lib/analytics";
import { api } from "../lib/api";
import { compactDate, compactTime, interpolate } from "../lib/format";
import { loadDismissedPrompts, saveDismissedPrompts } from "../lib/local-state";
import { checkHomeScreenStatus, maybeAddToHomeScreen } from "../lib/telegram";
import type { AppRoute } from "../lib/routes";
import type { AuthUser, Lesson, Progress, Scenario } from "../types";

type StreakSummary = {
  streak_count: number;
  xp: number;
  due_reviews: number;
  next_milestone: number;
  weekly_activity: Array<{ day_offset: number; active: boolean }>;
};

export function HomeScreen({ user, onNavigate }: { user: AuthUser; onNavigate: (route: AppRoute) => void }) {
  const { content, topicLabel, ui } = useI18n();
  const [progress, setProgress] = useState<Progress | null>(null);
  const [streak, setStreak] = useState<StreakSummary | null>(null);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [homeScreenStatus, setHomeScreenStatus] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState<Record<string, unknown>>(() => loadDismissedPrompts(user.telegram_id));

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    Promise.all([api.progress(user.telegram_id), api.streak(), api.continueLesson(user.telegram_id), api.scenarios()])
      .then(([progressValue, streakValue, lessonValue, scenarioValue]) => {
        if (cancelled) return;
        setProgress(progressValue);
        setStreak(streakValue);
        setLesson(lessonValue);
        setScenarios(scenarioValue);
      })
      .catch(() => {
        if (!cancelled) setError(ui("home.load_error", "Could not load your dashboard."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user.telegram_id]);

  useEffect(() => {
    checkHomeScreenStatus((status) => setHomeScreenStatus(status));
  }, []);

  const listeningCard = useMemo(() => {
    if (!lesson) return null;
    const hasPlayableAudio = lesson.has_audio || lesson.assets.some((asset) => asset.asset_type.toLowerCase().includes("audio")) || lesson.blocks.some((block) => Boolean(block.payload.audio_asset_url || block.payload.audio_url));
    if (!hasPlayableAudio && !lesson.audio_locked) return null;
    return {
      title: lesson.audio_locked ? ui("lesson.listening_locked", "Listening is locked") : ui("home.review_due_open", "Listening practice"),
      description: lesson.audio_locked
        ? ui("lesson.listening_locked_description", "This lesson includes premium-only audio. Upgrade to unlock playback and transcript controls.")
        : ui("lesson.lesson_audio_description", "Use the audio before you answer to tune your ear to the target pattern."),
      route: { screen: "lesson", lessonId: lesson.id } as AppRoute
    };
  }, [lesson, ui]);

  const scenarioRecommendation = useMemo(
    () => scenarios.find((item) => item.progress?.status === "in_progress") || scenarios[0] || null,
    [scenarios]
  );
  const guidedSessions = progress?.review_overview.guided_sessions.slice(0, 3) || [];
  const reviewSchedule = progress?.review_overview.schedule;
  const focusLane = guidedSessions.find((session) => !["due", "mistakes"].includes(session.mode)) || null;

  const dailyLoop = useMemo(() => {
    const warmupMode = progress?.due_reviews ? "due" : progress?.mistake_reviews ? "mistakes" : "mixed";
    const warmupReady = progress?.due_reviews || progress?.mistake_reviews || 0;
    const applyRoute =
      focusLane
        ? ({ screen: "review", mode: focusLane.mode, size: focusLane.size } as AppRoute)
        : scenarioRecommendation
          ? ({ screen: "scenarios", scenario: scenarioRecommendation.slug } as AppRoute)
          : ({ screen: "grammar" } as AppRoute);

    const applyTitle =
      focusLane?.title
      || (scenarioRecommendation ? content(scenarioRecommendation.title, ui("home.apply_real_life_title", "Use it in a real-life scene")) : ui("home.apply_real_life_title", "Use it in a real-life scene"));

    const applyDescription =
      focusLane?.description
      || (scenarioRecommendation
        ? content(scenarioRecommendation.description, ui("scenario.hero_description", "Pick a context, hide translations when you want pressure, and switch to listening mode when audio is available."))
        : ui("home.apply_real_life_description", "Use grammar notes, useful phrases, or a scenario while the lesson is still fresh."));

    return [
      {
        key: "warmup",
        step: "01",
        title: ui("home.warm_up_title", "Warm up"),
        description: warmupReady
          ? interpolate(ui("home.warm_up_description", "{count} review items are ready. Clear the short queue before you push new material."), { count: warmupReady })
          : ui("home.warm_up_empty", "No urgent reviews are waiting, so keep the warm-up compact and move straight into the lesson."),
        badge: warmupReady ? `${warmupReady} ${ui("home.ready_now", "ready")}` : ui("home.clear", "Clear"),
        route: { screen: "review", mode: warmupMode, size: 5, shortcut: "two-minute" } as AppRoute,
        cta: ui("home.two_minute_review", "2-minute review"),
      },
      {
        key: "lesson",
        step: "02",
        title: lesson ? content(lesson.title, ui("home.continue_lesson", "Continue lesson")) : ui("home.continue_lesson", "Continue lesson"),
        description: lesson
          ? interpolate(ui("home.lesson_step_description", "{minutes} minutes, guided notes, drills, and recap."), { minutes: lesson.estimated_minutes })
          : ui("home.lesson_step_empty", "Your next guided lesson is ready. Keep it short and finish one compact step set."),
        badge: lesson ? `${lesson.estimated_minutes} min` : ui("home.next", "Next"),
        route: { screen: "lesson", lessonId: lesson?.id || progress?.current_lesson?.id } as AppRoute,
        cta: ui("home.continue_lesson", "Continue lesson"),
      },
      {
        key: "apply",
        step: "03",
        title: applyTitle,
        description: applyDescription,
        badge: focusLane ? ui("home.review_due_open", "Open review") : scenarioRecommendation ? ui("route.scenarios", "Scenarios") : ui("route.grammar", "Grammar"),
        route: applyRoute,
        cta: focusLane ? ui("home.focus_weak_spot", "Focus weak spot") : scenarioRecommendation ? ui("home.open_scenario", "Open scenario") : ui("home.open_grammar", "Open grammar"),
      },
    ];
  }, [
    content,
    focusLane,
    lesson,
    progress?.current_lesson?.id,
    progress?.due_reviews,
    progress?.mistake_reviews,
    scenarioRecommendation,
    ui,
  ]);

  const addToHomeVisible = homeScreenStatus && ["unknown", "missed"].includes(homeScreenStatus) && !dismissed.home_screen_prompt;

  function rememberDismissed() {
    const next = { ...dismissed, home_screen_prompt: true };
    setDismissed(next);
    saveDismissedPrompts(user.telegram_id, next);
  }

  function navigate(route: AppRoute, eventName: string) {
    track(eventName, { telegram_id: user.telegram_id, audience_language: user.interface_language });
    onNavigate(route);
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <HeroCard title={ui("state.loading", "Loading")} description={ui("subtitle.home", "Serious mobile Korean learning")} />
      </div>
    );
  }

  if (error) {
    return <ErrorState description={error} onRetry={() => window.location.reload()} />;
  }

  if (!progress || !streak) {
    return <EmptyState title={ui("home.no_data_title", "No study data yet")} description={ui("home.no_data_description", "Start your first lesson and this dashboard will turn into your daily control panel.")} action={<Button onClick={() => navigate({ screen: "lesson" }, "home_first_lesson_tapped")}>{ui("home.start_lesson", "Start lesson")}</Button>} />;
  }

  return (
    <div className="space-y-4">
      <HeroCard
        eyebrow={ui("home.today", "Today")}
        title={lesson ? content(lesson.title, ui("home.continue_lesson", "Continue lesson")) : ui("home.continue", "Continue")}
        description={
          lesson
            ? content(lesson.summary, ui("lesson.guided", "Guided lesson"))
            : progress.due_reviews > 0
              ? `${progress.due_reviews} ${ui("home.due_reviews", "Due reviews")}`
              : ui("subtitle.home", "Serious mobile Korean learning")
        }
        action={<StatusChip tone="accent">{progress.current_path ? content(progress.current_path.title, ui("progress.guided_curriculum", "Guided curriculum")) : ui("progress.guided_curriculum", "Guided curriculum")}</StatusChip>}
      >
        <div className="grid gap-3">
          <div className="rounded-[24px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{ui("home.current_lesson", "Current lesson")}</p>
                <p className="mt-2 text-lg font-semibold">{progress.current_lesson ? content(progress.current_lesson.title, ui("home.no_lesson_active", "No lesson active")) : ui("home.no_lesson_active", "No lesson active")}</p>
                {progress.current_lesson?.summary ? <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{content(progress.current_lesson.summary)}</p> : null}
              </div>
              {lesson?.has_audio ? <StatusChip tone="success">{ui("lesson.listen", "Listen")}</StatusChip> : null}
              {lesson?.audio_locked ? <StatusChip tone="warning">{ui("lesson.premium", "Premium")} audio</StatusChip> : null}
            </div>
            <div className="mt-4 h-3 overflow-hidden rounded-full bg-black/6">
              <div className="h-full rounded-full bg-[linear-gradient(90deg,var(--app-accent),#66af86)]" style={{ width: `${progress.current_path?.percent_complete || 0}%` }} />
            </div>
            <div className="mt-2 flex items-center justify-between text-xs text-[color:var(--app-muted)]">
              <span>{progress.current_path?.completed_lessons || 0}/{progress.current_path?.total_lessons || 0} {ui("home.lessons_complete", "lessons complete")}</span>
              <span>{Math.round(progress.current_path?.percent_complete || 0)}%</span>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button onClick={() => navigate({ screen: "lesson", lessonId: lesson?.id || progress.current_lesson?.id }, "home_continue_lesson_tapped")}>{ui("home.continue_lesson", "Continue lesson")}</Button>
              <Button variant="secondary" onClick={() => navigate({ screen: "review", mode: "due", size: 5, shortcut: "two-minute" }, "home_two_minute_review_tapped")}>{ui("home.two_minute_review", "2-minute review")}</Button>
            </div>
          </div>

          {addToHomeVisible ? (
            <div className="rounded-[24px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)] p-4">
              <p className="text-sm font-semibold">{ui("home.keep_close_title", "Keep the app one tap away")}</p>
              <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{ui("home.keep_close_description", "Add Korean Learn to your home screen if you use it daily.")}</p>
              <div className="mt-4 flex gap-2">
                <Button onClick={() => { maybeAddToHomeScreen(); rememberDismissed(); }}>{ui("home.add_to_home", "Add to home screen")}</Button>
                <Button variant="ghost" onClick={rememberDismissed}>{ui("home.not_now", "Not now")}</Button>
              </div>
            </div>
          ) : null}
        </div>
      </HeroCard>

      <div className="grid grid-cols-2 gap-3">
        <MetricCard label={ui("home.xp", "XP")} value={progress.xp} detail={ui("home.xp_detail", "All-time study points")} icon={Sparkles} tone="success" />
        <MetricCard label={ui("home.streak", "Streak")} value={streak.streak_count} detail={interpolate(ui("home.streak_next", "Next {count}"), { count: streak.next_milestone })} icon={Flame} tone="warning" />
        <MetricCard label={ui("home.due_reviews", "Due reviews")} value={progress.due_reviews} detail={ui("home.ready_now", "Ready now")} icon={Repeat2} tone="accent" />
        <MetricCard label={ui("home.completed", "Completed")} value={progress.completed_lessons} detail={ui("home.completed_detail", "Lessons finished")} icon={BookOpen} tone="neutral" />
      </div>

      <Surface>
        <SectionHeading eyebrow={ui("home.daily_loop", "Daily loop")} title={ui("home.daily_loop_title", "Small steps, in order")} description={ui("home.daily_loop_description", "Warm up, finish one compact lesson, then use the pattern in review or a real-life scenario.")} />
        <div className="mt-4 space-y-3">
          {dailyLoop.map((item) => (
            <div key={item.key} className="flex gap-3 rounded-[22px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px] bg-[color:var(--app-accent)] text-sm font-semibold text-[color:var(--app-accent-text)]">
                {item.step}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">{item.title}</p>
                    <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{item.description}</p>
                  </div>
                  <StatusChip tone="neutral">{item.badge}</StatusChip>
                </div>
                <div className="mt-3">
                  <Button variant={item.key === "lesson" ? "primary" : "secondary"} onClick={() => navigate(item.route, `home_${item.key}_loop_tapped`)}>
                    {item.cta}
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Surface>

      {reviewSchedule ? (
        <Surface>
          <SectionHeading eyebrow={ui("home.spaced_repetition", "Spaced repetition")} title={ui("home.spaced_repetition_title", "Review schedule at a glance")} description={ui("home.spaced_repetition_description", "Keep the queue small now and let the next reviews land on schedule instead of piling up.")} />
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
                {ui("home.next_review_slot", "Next scheduled review")}: {compactDate(reviewSchedule.next_review_at, user.interface_language)} {compactTime(reviewSchedule.next_review_at, user.interface_language)}
              </span>
            </div>
          ) : null}
        </Surface>
      ) : null}

      {guidedSessions.length ? (
        <Surface>
          <SectionHeading eyebrow={ui("home.review_now", "Review now")} title={ui("home.attention_first", "What needs attention first")} description={ui("review.center", "Review center")} />
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {guidedSessions.map((session) => (
              <ActionCard
                key={session.mode}
                title={session.title}
                description={`${session.description} ${session.item_count} ${ui("review.items", "items")} ready.`}
                meta={<StatusChip tone={session.tone}>{session.item_count} {ui("home.ready_now", "ready")}</StatusChip>}
                cta={ui("home.review_due_open", "Open review")}
                icon={session.mode === "listening" ? Ear : Repeat2}
                tone={session.tone}
                onClick={() => navigate({ screen: "review", mode: session.mode, size: session.size }, `home_${session.mode}_review_tapped`)}
              />
            ))}
          </div>
        </Surface>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <ActionCard
          title={ui("home.review_due_title", "Due review")}
          description={progress.due_reviews ? interpolate(ui("progress.clear_due_description", "{count} items are waiting. A short review session will improve retention before the next lesson."), { count: progress.due_reviews }) : ui("review.empty_title", "Nothing in this queue")}
          meta={<StatusChip tone={progress.due_reviews ? "accent" : "neutral"}>{progress.due_reviews} {ui("home.due_reviews", "due")}</StatusChip>}
          cta={ui("home.review_due_open", "Open review")}
          icon={Repeat2}
          onClick={() => navigate({ screen: "review", mode: "due", size: 10 }, "home_due_review_tapped")}
        />
        <ActionCard
          title={ui("home.mistakes_title", "Mistakes review")}
          description={progress.mistake_reviews ? interpolate(ui("progress.repair_description", "{count} items need a focused retry."), { count: progress.mistake_reviews }) : ui("home.no_mistake_queue", "No open mistake queue right now.")}
          meta={<StatusChip tone={progress.mistake_reviews ? "danger" : "neutral"}>{progress.mistake_reviews} {ui("home.mistakes_title", "mistakes")}</StatusChip>}
          cta={ui("home.focus_mistakes", "Focus mistakes")}
          icon={TrendingUp}
          tone="danger"
          onClick={() => navigate({ screen: "review", mode: "mistakes", size: 10 }, "home_mistakes_review_tapped")}
        />
        {listeningCard ? (
          <ActionCard
            title={listeningCard.title}
            description={listeningCard.description}
            cta={ui("action.open", "Open")}
            icon={Ear}
            tone={lesson?.audio_locked ? "warning" : "success"}
            onClick={() => navigate(listeningCard.route, "home_listening_tapped")}
          />
        ) : null}
        {scenarioRecommendation ? (
          <ActionCard
            title={content(scenarioRecommendation.title, ui("route.scenarios", "Scenarios"))}
            description={content(scenarioRecommendation.description)}
            meta={
              <>
                <StatusChip tone="neutral">{topicLabel(scenarioRecommendation.topic)}</StatusChip>
                <StatusChip tone={scenarioRecommendation.progress?.status === "in_progress" ? "accent" : "neutral"}>
                  {scenarioRecommendation.progress?.status === "in_progress" ? ui("home.continue", "Continue") : ui("home.recommended", "Recommended")}
                </StatusChip>
              </>
            }
            cta={ui("home.open_scenario", "Open scenario")}
            icon={MessageCircleMore}
            onClick={() => navigate({ screen: "scenarios", scenario: scenarioRecommendation.slug }, "home_scenario_tapped")}
          />
        ) : null}
      </div>

      <div className="grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
        <Surface>
          <SectionHeading eyebrow={ui("home.progress_snapshot", "Progress snapshot")} title={ui("home.recent_progress", "Recent progress")} description={ui("progress.trajectory_description", "A compact view of what is working, what is slipping, and what to do next.")} />
          <div className="mt-4 space-y-3">
            <div className="rounded-[22px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{ui("home.last_completed_lesson", "Last completed lesson")}</p>
              <p className="mt-2 text-base font-semibold">{progress.last_completed_lesson ? content(progress.last_completed_lesson.title, ui("home.no_completed_lesson", "You have not completed a lesson yet.")) : ui("home.no_completed_lesson", "You have not completed a lesson yet.")}</p>
            </div>
            <div className="rounded-[22px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{ui("home.weak_areas", "Weak areas")}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {progress.difficult_topics.length ? (
                  progress.difficult_topics.map((item) => <StatusChip key={item.topic} tone="warning">{topicLabel(item.topic)}</StatusChip>)
                ) : (
                  <span className="text-sm text-[color:var(--app-muted)]">{ui("home.no_weak_spots", "No recurring weak spots yet.")}</span>
                )}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {progress.review_overview.weak_grammar.slice(0, 3).map((item) => <StatusChip key={item.key} tone="warning">{item.label} · {item.mistakes}</StatusChip>)}
                {progress.review_overview.repeated_mistakes.slice(0, 2).map((item) => <StatusChip key={item.review_item_id} tone="danger">{item.mistake_count}x repeat</StatusChip>)}
              </div>
            </div>
          </div>
        </Surface>

        <Surface>
          <SectionHeading eyebrow={ui("home.weekly_habit", "Weekly habit")} title={ui("home.keep_cadence", "Keep the cadence small")} description={ui("progress.habit_description", "Consistency matters more than intensity in the first months.")} />
          <div className="mt-4 grid grid-cols-7 gap-2">
            {streak.weekly_activity.map((item) => (
              <div
                key={item.day_offset}
                className={`flex h-16 items-end justify-center rounded-[18px] border px-2 pb-3 ${
                  item.active
                    ? "border-[color:var(--app-accent)]/20 bg-[color:var(--app-accent)]/10 text-[color:var(--app-accent)]"
                    : "border-[color:var(--app-line)] bg-[color:var(--app-elevated)] text-[color:var(--app-muted)]"
                }`}
              >
                <span className="text-[11px] font-semibold">{item.active ? ui("home.on", "On") : ui("home.off", "Off")}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center justify-between rounded-[22px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">{ui("home.current_streak", "Current streak")}</p>
              <p className="mt-1 text-xl font-semibold">{streak.streak_count} {ui("home.days", "days")}</p>
            </div>
            <Button variant="secondary" onClick={() => navigate({ screen: "progress" }, "home_progress_tapped")}>{ui("home.open_progress", "Open progress")}</Button>
          </div>
        </Surface>
      </div>

      <Surface>
        <SectionHeading eyebrow={ui("home.quick_jump", "Quick jump")} title={ui("home.choose_lane", "Choose a study lane")} description={ui("subtitle.home", "Serious mobile Korean learning")} />
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <ActionCard title={ui("route.vocab", "Vocabulary")} description={ui("vocab.hero_description", "Use bookmarks for your own difficult words, and use review chips to spot what is due now.")} cta={ui("home.open_vocab", "Open vocab")} icon={Languages} onClick={() => navigate({ screen: "vocab" }, "home_vocab_tapped")} />
          <ActionCard title={ui("route.grammar", "Grammar")} description={ui("grammar.hero_description", "Use the grammar view when you want explicit structure, linked scenarios, and a quick route back into practice.")} cta={ui("home.open_grammar", "Open grammar")} icon={GraduationCap} onClick={() => navigate({ screen: "grammar" }, "home_grammar_tapped")} />
          <ActionCard title={ui("route.scenarios", "Scenarios")} description={ui("scenario.hero_description", "Pick a context, hide translations when you want pressure, and switch to listening mode when audio is available.")} cta={ui("home.open_scenarios", "Open scenarios")} icon={MessageCircleMore} onClick={() => navigate({ screen: "scenarios" }, "home_scenarios_tapped")} />
        </div>
      </Surface>
    </div>
  );
}
