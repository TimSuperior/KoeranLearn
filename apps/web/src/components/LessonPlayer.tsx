import { BookOpenCheck, ChevronLeft, ChevronRight, Ear, GraduationCap, Languages, MessageCircleMore, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { AudioPlayer, Button, EmptyState, HeroCard, SectionHeading, StatusChip, Surface } from "./ui";
import { track } from "../lib/analytics";
import { t } from "../lib/format";
import { clearLessonResume, loadLessonResume, saveLessonResume } from "../lib/local-state";
import type { AppRoute } from "../lib/routes";
import { api } from "../lib/api";
import type { AudioCue, AuthUser, Language, Lesson, LessonAsset, LessonBlock } from "../types";
import { ExerciseRenderer } from "./exercises/ExerciseRenderer";

type Step =
  | { kind: "overview" }
  | { kind: "block"; block: LessonBlock }
  | { kind: "exercise"; exerciseIndex: number };

type Feedback = {
  is_correct: boolean;
  expected: unknown;
  explanation: Record<string, string>;
  lesson_completed: boolean;
  xp_awarded: number;
};

function blockAudioSources(block: LessonBlock): string[] {
  return [block.payload.audio_asset_url, block.payload.audio_url].filter(Boolean).map(String);
}

function payloadAudioItems(payload: Record<string, unknown> | undefined): AudioCue[] {
  return Array.isArray(payload?.audio_items) ? (payload.audio_items as AudioCue[]) : [];
}

function assetLabel(asset: LessonAsset): string {
  return String(asset.metadata_json.label || asset.asset_type).replaceAll("_", " ");
}

export function LessonPlayer({
  user,
  lesson,
  onNavigate,
  onCompleted,
  moduleTitle
}: {
  user: AuthUser;
  lesson: Lesson | null;
  onNavigate: (route: AppRoute) => void;
  onCompleted: () => void;
  moduleTitle?: string;
}) {
  const [stepIndex, setStepIndex] = useState(0);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [busy, setBusy] = useState(false);
  const [complete, setComplete] = useState(false);

  const visibleBlocks = useMemo(() => [...(lesson?.blocks || [])].filter((block) => block.status !== "archived").sort((a, b) => a.order_index - b.order_index), [lesson?.blocks]);
  const exercises = useMemo(() => [...(lesson?.exercises || [])].sort((a, b) => a.order_index - b.order_index), [lesson?.exercises]);
  const steps = useMemo<Step[]>(() => [{ kind: "overview" }, ...visibleBlocks.map((block) => ({ kind: "block", block } as Step)), ...exercises.map((_, exerciseIndex) => ({ kind: "exercise", exerciseIndex } as Step))], [exercises, visibleBlocks]);
  const activeStep = steps[stepIndex];
  const currentExercise = activeStep?.kind === "exercise" ? exercises[activeStep.exerciseIndex] : null;
  const lessonAudio = (lesson?.assets || []).filter((asset) => asset.asset_type.toLowerCase().includes("audio"));
  const progressTotal = steps.length + 1;
  const progressValue = complete ? progressTotal : stepIndex + 1;

  useEffect(() => {
    if (!lesson) return;
    const resumeIndex = loadLessonResume(user.telegram_id, lesson.id);
    setStepIndex(Math.min(Math.max(0, resumeIndex), Math.max(steps.length - 1, 0)));
    setFeedback(null);
    setBusy(false);
    setComplete(false);
  }, [lesson?.id, steps.length, user.telegram_id]);

  useEffect(() => {
    if (!lesson || complete) return;
    saveLessonResume(user.telegram_id, lesson.id, stepIndex);
  }, [complete, lesson, stepIndex, user.telegram_id]);

  if (!lesson) {
    return <EmptyState title="No active lesson" description="The next guided lesson will appear here as soon as it is unlocked." action={<Button onClick={() => onNavigate({ screen: "home" })}>Back home</Button>} />;
  }

  const currentLesson = lesson;
  const lockedLessonAudio = currentLesson.audio_locked && currentLesson.has_premium_audio;

  async function submit(answer: unknown) {
    if (!currentExercise) return;
    setBusy(true);
    try {
      const response = await api.submitExercise(user.telegram_id, currentLesson.id, currentExercise.id, answer);
      setFeedback(response);
      track("lesson_answer_submitted", {
        telegram_id: user.telegram_id,
        audience_language: user.interface_language,
        properties: { lesson_id: currentLesson.id, exercise_id: currentExercise.id, correct: response.is_correct }
      });
    } finally {
      setBusy(false);
    }
  }

  function nextStep() {
    if (feedback?.lesson_completed) {
      clearLessonResume(user.telegram_id, currentLesson.id);
      setComplete(true);
      setFeedback(null);
      track("lesson_recap_opened", {
        telegram_id: user.telegram_id,
        audience_language: user.interface_language,
        properties: { lesson_id: currentLesson.id }
      });
      return;
    }

    if (feedback?.is_correct) {
      setFeedback(null);
      setStepIndex((current) => Math.min(current + 1, steps.length - 1));
      return;
    }

    if (!feedback) {
      setStepIndex((current) => Math.min(current + 1, steps.length - 1));
    }
  }

  function previousStep() {
    setFeedback(null);
    setStepIndex((current) => Math.max(0, current - 1));
  }

  function renderStep() {
    if (!activeStep) return null;

    if (activeStep.kind === "overview") {
      return (
        <div className="space-y-4">
          <HeroCard eyebrow={moduleTitle || "Guided lesson"} title={t(currentLesson.title, user.interface_language, "Lesson")} description={t(currentLesson.summary, user.interface_language, "Guided Korean lesson")}>
            <div className="flex flex-wrap gap-2">
              <StatusChip tone="accent">{currentLesson.estimated_minutes} min</StatusChip>
              <StatusChip tone="neutral">{currentLesson.difficulty}</StatusChip>
              <StatusChip tone="neutral">{currentLesson.politeness_level.replaceAll("_", " ")}</StatusChip>
              {currentLesson.has_audio ? <StatusChip tone="success">Audio</StatusChip> : null}
              {lockedLessonAudio ? <StatusChip tone="warning">Premium audio</StatusChip> : null}
            </div>
            {currentLesson.korean_text ? <p className="mt-4 text-2xl font-semibold leading-relaxed text-[color:var(--app-text)]">{currentLesson.korean_text}</p> : null}
            <p className="mt-4 text-sm leading-7 text-[color:var(--app-muted)]">{t(currentLesson.explanation, user.interface_language)}</p>
            {currentLesson.objectives.length ? (
              <div className="mt-4 grid gap-2">
                {currentLesson.objectives.map((objective) => (
                  <div key={objective} className="rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-sm text-[color:var(--app-text)]">
                    {objective}
                  </div>
                ))}
              </div>
            ) : null}
          </HeroCard>

          {lessonAudio.length ? (
            <Surface>
              <SectionHeading eyebrow="Listen" title="Lesson audio" description="Use the audio before you answer to tune your ear to the target pattern." />
              <div className="mt-4 space-y-3">
                {lessonAudio.map((asset) => (
                  <AudioPlayer
                    key={asset.id}
                    src={asset.url}
                    label={assetLabel(asset)}
                    language={user.interface_language}
                    completed={complete}
                  />
                ))}
              </div>
            </Surface>
          ) : null}
          {lockedLessonAudio ? (
            <Surface className="border-amber-500/20 bg-amber-500/5">
              <SectionHeading eyebrow="Premium" title="Listening is locked" description="This lesson includes premium-only audio. Upgrade to unlock playback and transcript controls." />
            </Surface>
          ) : null}
          {currentLesson.audio_missing ? (
            <Surface className="border-coral/20 bg-coral/5">
              <SectionHeading eyebrow="Audio issue" title="Some lesson audio is unavailable" description="Playback for one or more premium clips is temporarily unavailable. The rest of the lesson will keep working." />
            </Surface>
          ) : null}
        </div>
      );
    }

    if (activeStep.kind === "block") {
      const audio = blockAudioSources(activeStep.block);
      const audioItems = payloadAudioItems(activeStep.block.payload);
      const audioLocked = Boolean(activeStep.block.payload.audio_locked);
      return (
        <Surface>
          <SectionHeading eyebrow={activeStep.block.block_type.replaceAll("_", " ")} title={t(activeStep.block.title, user.interface_language, activeStep.block.block_type.replaceAll("_", " "))} description={t(activeStep.block.body, user.interface_language)} />
          {audioItems.length ? (
            <div className="mt-4 space-y-3">
              {audioItems.map((item) => (
                <AudioPlayer key={item.id} item={item} label="Audio prompt" language={user.interface_language} completed={complete} />
              ))}
            </div>
          ) : null}
          {!audioItems.length && audio.length ? (
            <div className="mt-4 space-y-3">
              {audio.map((src, index) => (
                <AudioPlayer key={`${src}-${index}`} src={src} label="Audio prompt" language={user.interface_language} completed={complete} />
              ))}
            </div>
          ) : null}
          {audioLocked ? <p className="mt-4 text-sm text-[color:var(--app-secondary)]">Premium audio is locked for this block.</p> : null}
          {activeStep.block.payload.audio_missing ? <p className="mt-4 text-sm text-coral">This premium audio item is currently unavailable.</p> : null}
          {activeStep.block.block_type === "scenario_link" && activeStep.block.payload.scenario_id ? (
            <div className="mt-4">
              <Button variant="secondary" onClick={() => onNavigate({ screen: "scenarios" })}>Open related scenario</Button>
            </div>
          ) : null}
        </Surface>
      );
    }

    const exerciseAudio = [currentExercise?.payload.audio_asset_url, currentExercise?.payload.audio_url].filter(Boolean).map(String);
    const exerciseAudioItems = payloadAudioItems(currentExercise?.payload as Record<string, unknown> | undefined);
    const exerciseAudioLocked = Boolean(currentExercise?.payload.audio_locked);
    return (
      <div className="space-y-4">
        {exerciseAudioItems.length ? (
          <Surface>
            <SectionHeading eyebrow="Listen first" title="Audio cue" description="Replay the prompt before answering if you want a listening-first pass." />
            <div className="mt-4 space-y-3">
              {exerciseAudioItems.map((item, index) => (
                <AudioPlayer key={item.id} item={item} label={`Prompt ${index + 1}`} language={user.interface_language} completed={Boolean(feedback?.is_correct)} />
              ))}
            </div>
          </Surface>
        ) : null}
        {!exerciseAudioItems.length && exerciseAudio.length ? (
          <Surface>
            <SectionHeading eyebrow="Listen first" title="Audio cue" description="Replay the prompt before answering if you want a listening-first pass." />
            <div className="mt-4 space-y-3">
              {exerciseAudio.map((src, index) => (
                <AudioPlayer key={`${src}-${index}`} src={src} label={`Prompt ${index + 1}`} language={user.interface_language} completed={Boolean(feedback?.is_correct)} />
              ))}
            </div>
          </Surface>
        ) : null}
        {exerciseAudioLocked ? (
          <Surface className="border-amber-500/20 bg-amber-500/5">
            <SectionHeading eyebrow="Premium" title="Listening prompt locked" description="Upgrade to unlock this listening exercise." />
          </Surface>
        ) : null}
        {currentExercise?.payload.audio_missing ? (
          <Surface className="border-coral/20 bg-coral/5">
            <SectionHeading eyebrow="Audio issue" title="Prompt unavailable" description="This premium listening clip is temporarily unavailable, so the rest of the lesson continues without playback." />
          </Surface>
        ) : null}

        {currentExercise ? <ExerciseRenderer exercise={currentExercise} language={user.interface_language} onSubmit={submit} disabled={busy || Boolean(feedback)} /> : null}

        {feedback ? (
          <Surface className={feedback.is_correct ? "border-emerald-500/20 bg-emerald-500/5" : "border-[color:var(--app-secondary)]/20 bg-[color:var(--app-secondary)]/5"}>
            <SectionHeading
              eyebrow={feedback.is_correct ? "Feedback" : "Try again"}
              title={feedback.is_correct ? "Correct" : "Not quite yet"}
              description={t(feedback.explanation, user.interface_language, feedback.is_correct ? "Good job." : "Review the explanation and try one more time.")}
            />
            {!feedback.is_correct ? (
              <p className="mt-4 rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-sm text-[color:var(--app-text)]">
                Expected: {JSON.stringify(feedback.expected)}
              </p>
            ) : null}
            <div className="mt-4 flex items-center justify-between gap-3">
              <StatusChip tone={feedback.is_correct ? "success" : "warning"}>{feedback.xp_awarded} XP</StatusChip>
              <Button onClick={nextStep}>{feedback.lesson_completed ? "See recap" : feedback.is_correct ? "Next step" : "Try again"}</Button>
            </div>
          </Surface>
        ) : null}
      </div>
    );
  }

  if (complete) {
    return (
      <div className="space-y-4">
        <HeroCard eyebrow={moduleTitle || "Lesson complete"} title={t(currentLesson.title, user.interface_language, "Lesson complete")} description="You finished the lesson. Save the key patterns now while recall is fresh.">
          <div className="grid gap-3 sm:grid-cols-2">
            <Surface className="p-4">
              <div className="flex items-center gap-3">
                <BookOpenCheck size={20} className="text-[color:var(--app-accent)]" />
                <div>
                  <p className="text-sm font-semibold">Lesson recap</p>
                  <p className="text-sm leading-6 text-[color:var(--app-muted)]">{t(currentLesson.explanation, user.interface_language)}</p>
                </div>
              </div>
            </Surface>
            <Surface className="p-4">
              <div className="flex items-center gap-3">
                <Sparkles size={20} className="text-[color:var(--app-accent)]" />
                <div>
                  <p className="text-sm font-semibold">{currentLesson.objectives.length} learning targets</p>
                  <p className="text-sm leading-6 text-[color:var(--app-muted)]">Use review next to lock them in.</p>
                </div>
              </div>
            </Surface>
          </div>
        </HeroCard>

        {(currentLesson.related_vocabulary.length || currentLesson.related_grammar.length || currentLesson.related_scenarios.length) ? (
          <Surface>
            <SectionHeading eyebrow="Linked references" title="Continue with connected material" description="Jump straight from the lesson into the vocabulary, grammar, or scenario that reinforces it." />
            <div className="mt-4 grid gap-3">
              {currentLesson.related_vocabulary.slice(0, 4).map((item) => (
                <button key={`v-${item.id}`} type="button" onClick={() => onNavigate({ screen: "vocab", vocabId: item.id })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                  <div>
                    <p className="font-semibold">{item.korean}</p>
                    <p className="text-sm text-[color:var(--app-muted)]">{t(item.translations, user.interface_language)}</p>
                  </div>
                  <Languages size={18} className="text-[color:var(--app-accent)]" />
                </button>
              ))}
              {currentLesson.related_grammar.slice(0, 3).map((item) => (
                <button key={`g-${item.id}`} type="button" onClick={() => onNavigate({ screen: "grammar", grammarId: item.id })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                  <div>
                    <p className="font-semibold">{item.korean_pattern}</p>
                    <p className="text-sm text-[color:var(--app-muted)]">{t(item.title, user.interface_language)}</p>
                  </div>
                  <GraduationCap size={18} className="text-[color:var(--app-accent)]" />
                </button>
              ))}
              {currentLesson.related_scenarios.slice(0, 2).map((item) => (
                <button key={`s-${item.id}`} type="button" onClick={() => onNavigate({ screen: "scenarios", scenario: item.slug })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                  <div>
                    <p className="font-semibold">{t(item.title, user.interface_language)}</p>
                    <p className="text-sm text-[color:var(--app-muted)]">{t(item.description, user.interface_language)}</p>
                  </div>
                  <MessageCircleMore size={18} className="text-[color:var(--app-accent)]" />
                </button>
              ))}
            </div>
          </Surface>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Button
            onClick={() => {
              track("lesson_recap_finished", {
                telegram_id: user.telegram_id,
                audience_language: user.interface_language,
                properties: { lesson_id: currentLesson.id }
              });
              onCompleted();
              onNavigate({ screen: "home" });
            }}
          >
            Back home
          </Button>
          <Button variant="secondary" onClick={() => onNavigate({ screen: "review", mode: "due", size: 5 })}>Review now</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Surface>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--app-muted)]">{moduleTitle || "Guided lesson"}</p>
            <h2 className="mt-2 text-xl font-semibold">{t(currentLesson.title, user.interface_language, "Lesson")}</h2>
            <p className="mt-1 text-sm text-[color:var(--app-muted)]">{progressValue}/{progressTotal} steps • {currentLesson.estimated_minutes} min</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {currentLesson.has_audio ? <StatusChip tone="success"><Ear size={12} /> Audio</StatusChip> : null}
            <StatusChip tone="neutral">{currentLesson.difficulty}</StatusChip>
          </div>
        </div>
        <div className="mt-4 h-3 overflow-hidden rounded-full bg-black/6">
          <div className="h-full rounded-full bg-[linear-gradient(90deg,var(--app-accent),#53b08c)]" style={{ width: `${(progressValue / progressTotal) * 100}%` }} />
        </div>
      </Surface>

      {renderStep()}

      {!feedback && !complete ? (
        <div className="flex items-center justify-between gap-2">
          <Button variant="secondary" disabled={stepIndex === 0} onClick={previousStep}>
            <ChevronLeft size={16} />
            Previous
          </Button>
          {activeStep?.kind !== "exercise" ? (
            <Button onClick={nextStep}>
              Next
              <ChevronRight size={16} />
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
