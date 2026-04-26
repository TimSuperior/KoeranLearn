import { BookOpen, Ear, Flame, GraduationCap, Languages, MessageCircleMore, Repeat2, Sparkles, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ActionCard, Button, EmptyState, ErrorState, HeroCard, MetricCard, SectionHeading, StatusChip, Surface } from "../components/ui";
import { track } from "../lib/analytics";
import { t, topicLabel } from "../lib/format";
import { loadDismissedPrompts, saveDismissedPrompts } from "../lib/local-state";
import type { AppRoute } from "../lib/routes";
import { api } from "../lib/api";
import { checkHomeScreenStatus, maybeAddToHomeScreen } from "../lib/telegram";
import type { AuthUser, Lesson, Progress, Scenario } from "../types";

type StreakSummary = {
  streak_count: number;
  xp: number;
  due_reviews: number;
  next_milestone: number;
  weekly_activity: Array<{ day_offset: number; active: boolean }>;
};

export function HomeScreen({ user, onNavigate }: { user: AuthUser; onNavigate: (route: AppRoute) => void }) {
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
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load your dashboard.");
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
      title: lesson.audio_locked ? "Premium listening" : "Listening practice",
      description: lesson.audio_locked
        ? "This lesson includes premium-only listening. Open it to see the locked audio state or upgrade for playback."
        : "This lesson already includes audio-linked blocks and prompts. Use it as your short listening pass today.",
      route: { screen: "lesson", lessonId: lesson.id } as AppRoute
    };
  }, [lesson]);

  const scenarioRecommendation = useMemo(
    () => scenarios.find((item) => item.progress?.status === "in_progress") || scenarios[0] || null,
    [scenarios]
  );

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
        <HeroCard title="Loading your dashboard" description="Pulling the next lesson, review queues, and habit summary." />
      </div>
    );
  }

  if (error) {
    return <ErrorState description={error} onRetry={() => window.location.reload()} />;
  }

  if (!progress || !streak) {
    return <EmptyState title="No study data yet" description="Start your first lesson and this dashboard will turn into your daily control panel." action={<Button onClick={() => navigate({ screen: "lesson" }, "home_first_lesson_tapped")}>Start lesson</Button>} />;
  }

  return (
    <div className="space-y-4">
      <HeroCard
        eyebrow="Today"
        title={lesson ? t(lesson.title, user.interface_language, "Continue your lesson") : "Your next move is ready"}
        description={
          lesson
            ? t(lesson.summary, user.interface_language, "Continue the guided lesson to keep momentum.")
            : progress.due_reviews > 0
              ? `${progress.due_reviews} reviews are due before they start slipping.`
              : "Your dashboard is clear. Use a scenario or vocabulary pass to keep the streak intact."
        }
        action={<StatusChip tone="accent">{progress.current_path ? t(progress.current_path.title, user.interface_language) : "Guided path"}</StatusChip>}
      >
        <div className="grid gap-3">
          <div className="rounded-[24px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">Current lesson</p>
                <p className="mt-2 text-lg font-semibold">{progress.current_lesson ? t(progress.current_lesson.title, user.interface_language) : "No lesson active"}</p>
                {progress.current_lesson?.summary ? <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{t(progress.current_lesson.summary, user.interface_language)}</p> : null}
              </div>
              {lesson?.has_audio ? <StatusChip tone="success">Audio</StatusChip> : null}
              {lesson?.audio_locked ? <StatusChip tone="warning">Premium audio</StatusChip> : null}
            </div>
            <div className="mt-4 h-3 overflow-hidden rounded-full bg-black/6">
              <div className="h-full rounded-full bg-[linear-gradient(90deg,var(--app-accent),#66af86)]" style={{ width: `${progress.current_path?.percent_complete || 0}%` }} />
            </div>
            <div className="mt-2 flex items-center justify-between text-xs text-[color:var(--app-muted)]">
              <span>{progress.current_path?.completed_lessons || 0}/{progress.current_path?.total_lessons || 0} lessons</span>
              <span>{Math.round(progress.current_path?.percent_complete || 0)}%</span>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button onClick={() => navigate({ screen: "lesson", lessonId: lesson?.id || progress.current_lesson?.id }, "home_continue_lesson_tapped")}>Continue lesson</Button>
              <Button variant="secondary" onClick={() => navigate({ screen: "review", mode: "due", size: 5, shortcut: "two-minute" }, "home_two_minute_review_tapped")}>2-minute review</Button>
            </div>
          </div>

          {addToHomeVisible ? (
            <div className="rounded-[24px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)] p-4">
              <p className="text-sm font-semibold">Keep the app one tap away</p>
              <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">Add Korean Learn to your home screen if you use it daily. It fits best as a repeat-study product.</p>
              <div className="mt-4 flex gap-2">
                <Button onClick={() => { maybeAddToHomeScreen(); rememberDismissed(); }}>Add to home screen</Button>
                <Button variant="ghost" onClick={rememberDismissed}>Not now</Button>
              </div>
            </div>
          ) : null}
        </div>
      </HeroCard>

      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="XP" value={progress.xp} detail="All-time study points" icon={Sparkles} tone="success" />
        <MetricCard label="Streak" value={streak.streak_count} detail={`Next ${streak.next_milestone}`} icon={Flame} tone="warning" />
        <MetricCard label="Due reviews" value={progress.due_reviews} detail="Ready now" icon={Repeat2} tone="accent" />
        <MetricCard label="Completed" value={progress.completed_lessons} detail="Lessons finished" icon={BookOpen} tone="neutral" />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <ActionCard
          title="Due review"
          description={progress.due_reviews ? `${progress.due_reviews} items are due right now.` : "Your due queue is clear. This is a good moment to keep moving in the curriculum."}
          meta={<StatusChip tone={progress.due_reviews ? "accent" : "neutral"}>{progress.due_reviews} due</StatusChip>}
          cta="Open review"
          icon={Repeat2}
          onClick={() => navigate({ screen: "review", mode: "due", size: 10 }, "home_due_review_tapped")}
        />
        <ActionCard
          title="Mistakes review"
          description={progress.mistake_reviews ? `${progress.mistake_reviews} recent misses need another pass.` : "No open mistake queue right now."}
          meta={<StatusChip tone={progress.mistake_reviews ? "danger" : "neutral"}>{progress.mistake_reviews} mistakes</StatusChip>}
          cta="Focus mistakes"
          icon={TrendingUp}
          tone="danger"
          onClick={() => navigate({ screen: "review", mode: "mistakes", size: 10 }, "home_mistakes_review_tapped")}
        />
        {listeningCard ? (
          <ActionCard
            title={listeningCard.title}
            description={listeningCard.description}
            cta={lesson?.audio_locked ? "Open locked lesson" : "Open audio lesson"}
            icon={Ear}
            tone={lesson?.audio_locked ? "warning" : "success"}
            onClick={() => navigate(listeningCard.route, "home_listening_tapped")}
          />
        ) : null}
        {scenarioRecommendation ? (
          <ActionCard
            title={t(scenarioRecommendation.title, user.interface_language, "Scenario recommendation")}
            description={t(scenarioRecommendation.description, user.interface_language, "Short real-life dialogue practice")}
            meta={
              <>
                <StatusChip tone="neutral">{topicLabel(scenarioRecommendation.topic)}</StatusChip>
                <StatusChip tone={scenarioRecommendation.progress?.status === "in_progress" ? "accent" : "neutral"}>
                  {scenarioRecommendation.progress?.status === "in_progress" ? "Continue" : "Recommended"}
                </StatusChip>
              </>
            }
            cta="Open scenario"
            icon={MessageCircleMore}
            onClick={() => navigate({ screen: "scenarios", scenario: scenarioRecommendation.slug }, "home_scenario_tapped")}
          />
        ) : null}
      </div>

      <div className="grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
        <Surface>
          <SectionHeading eyebrow="Progress snapshot" title="Recent progress" description="A quick look at what you finished and where you are slowing down." />
          <div className="mt-4 space-y-3">
            <div className="rounded-[22px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">Last completed lesson</p>
              <p className="mt-2 text-base font-semibold">{progress.last_completed_lesson ? t(progress.last_completed_lesson.title, user.interface_language) : "You have not completed a lesson yet."}</p>
            </div>
            <div className="rounded-[22px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">Weak areas</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {progress.difficult_topics.length ? (
                  progress.difficult_topics.map((item) => <StatusChip key={item.topic} tone="warning">{topicLabel(item.topic)}</StatusChip>)
                ) : (
                  <span className="text-sm text-[color:var(--app-muted)]">No recurring weak spots yet.</span>
                )}
              </div>
            </div>
          </div>
        </Surface>

        <Surface>
          <SectionHeading eyebrow="Weekly habit" title="Keep the cadence small" description="Serious progress in Telegram comes from short, repeated wins." />
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
                <span className="text-[11px] font-semibold">{item.active ? "On" : "Off"}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center justify-between rounded-[22px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-muted)]">Current streak</p>
              <p className="mt-1 text-xl font-semibold">{streak.streak_count} days</p>
            </div>
            <Button variant="secondary" onClick={() => navigate({ screen: "progress" }, "home_progress_tapped")}>Open progress</Button>
          </div>
        </Surface>
      </div>

      <Surface>
        <SectionHeading eyebrow="Quick jump" title="Choose a study lane" description="Jump straight into the material you need right now." />
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <ActionCard title="Vocabulary" description="Search words, check review state, and bookmark difficult items." cta="Open vocab" icon={Languages} onClick={() => navigate({ screen: "vocab" }, "home_vocab_tapped")} />
          <ActionCard title="Grammar" description="Read localized explanations and revisit common mistakes." cta="Open grammar" icon={GraduationCap} onClick={() => navigate({ screen: "grammar" }, "home_grammar_tapped")} />
          <ActionCard title="Scenarios" description="Practice short dialogues with translation and listening controls." cta="Open scenarios" icon={MessageCircleMore} onClick={() => navigate({ screen: "scenarios" }, "home_scenarios_tapped")} />
        </div>
      </Surface>
    </div>
  );
}
