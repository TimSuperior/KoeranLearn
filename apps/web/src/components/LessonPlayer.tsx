import { BookOpenCheck, ChevronLeft, ChevronRight, Ear, GraduationCap, Languages, MessageCircleMore, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useI18n } from "../lib/i18n";
import { track } from "../lib/analytics";
import { api } from "../lib/api";
import { interpolate } from "../lib/format";
import { clearLessonResume, loadLessonResume, saveLessonResume } from "../lib/local-state";
import type { AppRoute } from "../lib/routes";
import type { AudioCue, AuthUser, ExerciseFeedback, Lesson, LessonAsset, LessonBlock } from "../types";
import { ExerciseFeedbackCard } from "./exercises/ExerciseFeedbackCard";
import { ExerciseRenderer } from "./exercises/ExerciseRenderer";
import { AudioPlayer, Button, EmptyState, HeroCard, SectionHeading, StatusChip, Surface } from "./ui";

type Step =
  | { kind: "overview" }
  | { kind: "block"; block: LessonBlock }
  | { kind: "exercise"; exerciseIndex: number };

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
  const { content, explanationLanguage, ui } = useI18n();
  const [stepIndex, setStepIndex] = useState(0);
  const [feedback, setFeedback] = useState<ExerciseFeedback | null>(null);
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
    return <EmptyState title={ui("lesson.no_active_title", "No active lesson")} description={ui("lesson.no_active_description", "The next guided lesson will appear here as soon as it is unlocked.")} action={<Button onClick={() => onNavigate({ screen: "home" })}>{ui("action.back_home", "Back home")}</Button>} />;
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
    if (!feedback) {
      setStepIndex((current) => Math.min(current + 1, steps.length - 1));
      return;
    }

    if (feedback.lesson_completed) {
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

    if (feedback.is_correct) {
      setFeedback(null);
      setStepIndex((current) => Math.min(current + 1, steps.length - 1));
      return;
    }
    setFeedback(null);
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
          <HeroCard eyebrow={moduleTitle || ui("lesson.guided", "Guided lesson")} title={content(currentLesson.title, ui("route.lesson", "Lesson"))} description={content(currentLesson.summary, ui("lesson.guided", "Guided lesson"))}>
            <div className="flex flex-wrap gap-2">
              <StatusChip tone="accent">{currentLesson.estimated_minutes} min</StatusChip>
              <StatusChip tone="neutral">{currentLesson.difficulty}</StatusChip>
              <StatusChip tone="neutral">{currentLesson.politeness_level.replaceAll("_", " ")}</StatusChip>
              {currentLesson.has_audio ? <StatusChip tone="success">{ui("lesson.listen", "Listen")}</StatusChip> : null}
              {lockedLessonAudio ? <StatusChip tone="warning">{ui("lesson.premium", "Premium")} audio</StatusChip> : null}
            </div>
            {currentLesson.korean_text ? <p className="mt-4 text-2xl font-semibold leading-relaxed text-[color:var(--app-text)]">{currentLesson.korean_text}</p> : null}
            <p className="mt-4 text-sm leading-7 text-[color:var(--app-muted)]">{content(currentLesson.explanation)}</p>
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
              <SectionHeading eyebrow={ui("lesson.listen", "Listen")} title={ui("lesson.lesson_audio", "Lesson audio")} description={ui("lesson.lesson_audio_description", "Use the audio before you answer to tune your ear to the target pattern.")} />
              <div className="mt-4 space-y-3">
                {lessonAudio.map((asset) => (
                  <AudioPlayer
                    key={asset.id}
                    src={asset.url}
                    label={assetLabel(asset)}
                    language={explanationLanguage}
                    completed={complete}
                  />
                ))}
              </div>
            </Surface>
          ) : null}
          {lockedLessonAudio ? (
            <Surface className="border-amber-500/20 bg-amber-500/5">
              <SectionHeading eyebrow={ui("lesson.premium", "Premium")} title={ui("lesson.listening_locked", "Listening is locked")} description={ui("lesson.listening_locked_description", "This lesson includes premium-only audio. Upgrade to unlock playback and transcript controls.")} />
            </Surface>
          ) : null}
          {currentLesson.audio_missing ? (
            <Surface className="border-coral/20 bg-coral/5">
              <SectionHeading eyebrow={ui("lesson.audio_issue", "Audio issue")} title={ui("lesson.audio_issue", "Audio issue")} description={ui("lesson.audio_issue_description", "Playback for one or more premium clips is temporarily unavailable. The rest of the lesson will keep working.")} />
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
          <SectionHeading eyebrow={activeStep.block.block_type.replaceAll("_", " ")} title={content(activeStep.block.title, activeStep.block.block_type.replaceAll("_", " "))} description={content(activeStep.block.body)} />
          {audioItems.length ? (
            <div className="mt-4 space-y-3">
              {audioItems.map((item) => (
                <AudioPlayer key={item.id} item={item} label={ui("lesson.audio_prompt", "Audio prompt")} language={explanationLanguage} completed={complete} />
              ))}
            </div>
          ) : null}
          {!audioItems.length && audio.length ? (
            <div className="mt-4 space-y-3">
              {audio.map((src, index) => (
                <AudioPlayer key={`${src}-${index}`} src={src} label={ui("lesson.audio_prompt", "Audio prompt")} language={explanationLanguage} completed={complete} />
              ))}
            </div>
          ) : null}
          {audioLocked ? <p className="mt-4 text-sm text-[color:var(--app-secondary)]">{ui("lesson.listening_locked_description", "This lesson includes premium-only audio. Upgrade to unlock playback and transcript controls.")}</p> : null}
          {activeStep.block.payload.audio_missing ? <p className="mt-4 text-sm text-coral">{ui("lesson.audio_issue_description", "Playback for one or more premium clips is temporarily unavailable. The rest of the lesson will keep working.")}</p> : null}
          {activeStep.block.block_type === "scenario_link" && activeStep.block.payload.scenario_id ? (
            <div className="mt-4">
              <Button variant="secondary" onClick={() => onNavigate({ screen: "scenarios" })}>{ui("lesson.open_related_scenario", "Open related scenario")}</Button>
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
            <SectionHeading eyebrow={ui("lesson.listen_first", "Listen first")} title={ui("lesson.audio_cue", "Audio cue")} description={ui("lesson.audio_cue_description", "Replay the prompt before answering if you want a listening-first pass.")} />
            <div className="mt-4 space-y-3">
              {exerciseAudioItems.map((item, index) => (
                <AudioPlayer key={item.id} item={item} label={`${ui("exercise.prompt", "Exercise prompt")} ${index + 1}`} language={explanationLanguage} completed={Boolean(feedback?.is_correct)} />
              ))}
            </div>
          </Surface>
        ) : null}
        {!exerciseAudioItems.length && exerciseAudio.length ? (
          <Surface>
            <SectionHeading eyebrow={ui("lesson.listen_first", "Listen first")} title={ui("lesson.audio_cue", "Audio cue")} description={ui("lesson.audio_cue_description", "Replay the prompt before answering if you want a listening-first pass.")} />
            <div className="mt-4 space-y-3">
              {exerciseAudio.map((src, index) => (
                <AudioPlayer key={`${src}-${index}`} src={src} label={`${ui("exercise.prompt", "Exercise prompt")} ${index + 1}`} language={explanationLanguage} completed={Boolean(feedback?.is_correct)} />
              ))}
            </div>
          </Surface>
        ) : null}
        {exerciseAudioLocked ? (
          <Surface className="border-amber-500/20 bg-amber-500/5">
            <SectionHeading eyebrow={ui("lesson.premium", "Premium")} title={ui("lesson.prompt_locked", "Listening prompt locked")} description={ui("lesson.prompt_locked_description", "Upgrade to unlock this listening exercise.")} />
          </Surface>
        ) : null}
        {currentExercise?.payload.audio_missing ? (
          <Surface className="border-coral/20 bg-coral/5">
            <SectionHeading eyebrow={ui("lesson.audio_issue", "Audio issue")} title={ui("lesson.prompt_unavailable", "Prompt unavailable")} description={ui("lesson.prompt_unavailable_description", "This premium listening clip is temporarily unavailable, so the rest of the lesson continues without playback.")} />
          </Surface>
        ) : null}

        {currentExercise ? <ExerciseRenderer exercise={currentExercise} language={explanationLanguage} onSubmit={submit} disabled={busy || Boolean(feedback)} /> : null}

        {feedback && currentExercise ? (
          <ExerciseFeedbackCard
            exercise={currentExercise}
            feedback={feedback}
            language={explanationLanguage}
            nextLabel={feedback.lesson_completed ? ui("lesson.see_recap", "See recap") : feedback.is_correct ? ui("lesson.next_step", "Next step") : ui("feedback.try_again", "Try again")}
            onContinue={nextStep}
          />
        ) : null}
      </div>
    );
  }

  if (complete) {
    return (
      <div className="space-y-4">
        <HeroCard eyebrow={moduleTitle || ui("lesson.complete", "Lesson complete")} title={content(currentLesson.title, ui("lesson.complete", "Lesson complete"))} description={ui("lesson.complete_description", "You finished the lesson. Save the key patterns now while recall is fresh.")}>
          <div className="grid gap-3 sm:grid-cols-2">
            <Surface className="p-4">
              <div className="flex items-center gap-3">
                <BookOpenCheck size={20} className="text-[color:var(--app-accent)]" />
                <div>
                  <p className="text-sm font-semibold">{ui("lesson.recap", "Lesson recap")}</p>
                  <p className="text-sm leading-6 text-[color:var(--app-muted)]">{content(currentLesson.explanation)}</p>
                </div>
              </div>
            </Surface>
            <Surface className="p-4">
              <div className="flex items-center gap-3">
                <Sparkles size={20} className="text-[color:var(--app-accent)]" />
                <div>
                  <p className="text-sm font-semibold">{interpolate(ui("lesson.learning_targets", "{count} learning targets"), { count: currentLesson.objectives.length })}</p>
                  <p className="text-sm leading-6 text-[color:var(--app-muted)]">{ui("lesson.use_review_next", "Use review next to lock them in.")}</p>
                </div>
              </div>
            </Surface>
          </div>
        </HeroCard>

        {(currentLesson.related_vocabulary.length || currentLesson.related_grammar.length || currentLesson.related_scenarios.length) ? (
          <Surface>
            <SectionHeading eyebrow={ui("lesson.linked_references", "Linked references")} title={ui("lesson.continue_connected", "Continue with connected material")} description={ui("lesson.continue_connected", "Continue with connected material")} />
            <div className="mt-4 grid gap-3">
              {currentLesson.related_vocabulary.slice(0, 4).map((item) => (
                <button key={`v-${item.id}`} type="button" onClick={() => onNavigate({ screen: "vocab", vocabId: item.id })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                  <div>
                    <p className="font-semibold">{item.korean}</p>
                    <p className="text-sm text-[color:var(--app-muted)]">{content(item.translations)}</p>
                  </div>
                  <Languages size={18} className="text-[color:var(--app-accent)]" />
                </button>
              ))}
              {currentLesson.related_grammar.slice(0, 3).map((item) => (
                <button key={`g-${item.id}`} type="button" onClick={() => onNavigate({ screen: "grammar", grammarId: item.id })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                  <div>
                    <p className="font-semibold">{item.korean_pattern}</p>
                    <p className="text-sm text-[color:var(--app-muted)]">{content(item.title)}</p>
                  </div>
                  <GraduationCap size={18} className="text-[color:var(--app-accent)]" />
                </button>
              ))}
              {currentLesson.related_scenarios.slice(0, 2).map((item) => (
                <button key={`s-${item.id}`} type="button" onClick={() => onNavigate({ screen: "scenarios", scenario: item.slug })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                  <div>
                    <p className="font-semibold">{content(item.title)}</p>
                    <p className="text-sm text-[color:var(--app-muted)]">{content(item.description)}</p>
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
            {ui("action.back_home", "Back home")}
          </Button>
          <Button variant="secondary" onClick={() => onNavigate({ screen: "review", mode: "due", size: 5 })}>{ui("lesson.review_now", "Review now")}</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Surface>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--app-muted)]">{moduleTitle || ui("lesson.guided", "Guided lesson")}</p>
            <h2 className="mt-2 text-xl font-semibold">{content(currentLesson.title, ui("route.lesson", "Lesson"))}</h2>
            <p className="mt-1 text-sm text-[color:var(--app-muted)]">{interpolate(ui("lesson.steps", "{current}/{total} steps"), { current: progressValue, total: progressTotal })} • {currentLesson.estimated_minutes} min</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {currentLesson.has_audio ? <StatusChip tone="success"><Ear size={12} /> {ui("lesson.listen", "Listen")}</StatusChip> : null}
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
            {ui("action.previous", "Previous")}
          </Button>
          {activeStep?.kind !== "exercise" ? (
            <Button onClick={nextStep}>
              {ui("action.next", "Next")}
              <ChevronRight size={16} />
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
