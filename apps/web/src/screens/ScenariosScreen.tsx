import { Bookmark, Ear, Headphones, Link2, MessageCircleMore, Share2, Star } from "lucide-react";
import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";

import { AudioPlayer, Button, EmptyState, ErrorState, FilterChip, HeroCard, IconButton, LoadingCard, SectionHeading, StatusChip, Surface, ToggleRow } from "../components/ui";
import { useI18n } from "../lib/i18n";
import { track } from "../lib/analytics";
import { api } from "../lib/api";
import { haptic, openInlineShare, shareRoute } from "../lib/telegram";
import type { AppRoute } from "../lib/routes";
import type { AuthUser, Dialogue, Scenario, ScenarioDetail } from "../types";

const topics = ["all", "daily_life", "food", "shopping", "transport", "study", "work", "health"];

export function ScenariosScreen({
  user,
  scenarioSlug,
  initialTopic,
  onNavigate
}: {
  user: AuthUser;
  scenarioSlug?: string;
  initialTopic?: string;
  onNavigate: (route: AppRoute) => void;
}) {
  const { content, topicLabel, ui } = useI18n();
  const [topic, setTopic] = useState(initialTopic || "all");
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [items, setItems] = useState<Scenario[]>([]);
  const [selected, setSelected] = useState<ScenarioDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    api
      .scenarios({
        ...(topic !== "all" ? { topic } : {}),
        ...(deferredQuery ? { q: deferredQuery } : {})
      })
      .then((value) => {
        if (!cancelled) setItems(value);
      })
      .catch(() => {
        if (!cancelled) setError(ui("scenario.load_error", "Could not load scenarios."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [deferredQuery, topic]);

  useEffect(() => {
    if (!scenarioSlug) return;
    void openScenario(scenarioSlug);
  }, [scenarioSlug]);

  async function openScenario(idOrSlug: string | number) {
    const started = await api.startScenario(idOrSlug);
    setSelected(started.scenario);
    track("scenario_opened", {
      telegram_id: user.telegram_id,
      audience_language: user.interface_language,
      properties: { scenario: typeof idOrSlug === "string" ? idOrSlug : started.scenario.slug }
    });
  }

  if (selected) {
    return <DialoguePlayer user={user} scenario={selected} onBack={() => { setSelected(null); onNavigate({ screen: "scenarios" }); }} onNavigate={onNavigate} />;
  }

  return (
    <div className="space-y-4">
      <HeroCard eyebrow={ui("scenario.hero_eyebrow", "Scenario practice")} title={ui("scenario.hero_title", "Real-life Korean dialogues")} description={ui("scenario.hero_description", "Pick a context, hide translations when you want pressure, and switch to listening mode when audio is available.")} />

      <Surface>
        <SectionHeading eyebrow={ui("scenario.filters", "Filters")} title={ui("scenario.filters_title", "Find the right situation")} />
        <input
          value={query}
          onChange={(event) => startTransition(() => setQuery(event.target.value))}
          placeholder={ui("scenario.search_placeholder", "Search by topic or situation")}
          className="mt-4 h-12 w-full rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 text-sm outline-none focus:border-[color:var(--app-accent)]"
        />
        <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
          {topics.map((item) => (
            <FilterChip key={item} active={topic === item} onClick={() => setTopic(item)}>
              {item === "all" ? ui("topic.all", "All") : topicLabel(item)}
            </FilterChip>
          ))}
        </div>
      </Surface>

      {loading ? <LoadingCard label={ui("scenario.loading", "Loading scenarios")} /> : null}
      {error ? <ErrorState description={error} onRetry={() => window.location.reload()} /> : null}

      {!loading && !error && items.length === 0 ? <EmptyState title={ui("scenario.empty_title", "No matching scenarios")} description={ui("scenario.empty_description", "Try a broader topic or clear the search to browse all published dialogues.")} /> : null}

      <div className="grid gap-3">
        {items.map((scenario) => (
          <button
            key={scenario.id}
            type="button"
            onClick={() => openScenario(scenario.slug)}
            className="rounded-[28px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)] p-4 text-left shadow-[0_14px_40px_rgba(15,23,42,0.06)]"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[18px] border border-[color:var(--app-accent)]/20 bg-[color:var(--app-accent)]/10 text-[color:var(--app-accent)]">
                  <MessageCircleMore size={20} />
                </div>
                <div className="min-w-0">
                  <h2 className="text-base font-semibold">{content(scenario.title)}</h2>
                  <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{content(scenario.description)}</p>
                </div>
              </div>
              {scenario.progress?.status === "in_progress" ? <StatusChip tone="accent">{ui("scenario.continue", "Continue")}</StatusChip> : null}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <StatusChip tone="neutral">{topicLabel(scenario.topic)}</StatusChip>
              <StatusChip tone="neutral">{scenario.difficulty}</StatusChip>
              {scenario.context_labels.slice(0, 2).map((label) => (
                <StatusChip key={label} tone="neutral">{label.replaceAll("_", " ")}</StatusChip>
              ))}
              {scenario.is_favorited ? <StatusChip tone="warning">{ui("scenario.saved", "Saved")}</StatusChip> : null}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function DialoguePlayer({
  user,
  scenario,
  onBack,
  onNavigate
}: {
  user: AuthUser;
  scenario: ScenarioDetail;
  onBack: () => void;
  onNavigate: (route: AppRoute) => void;
}) {
  const { content, explanationLanguage, topicLabel, ui } = useI18n();
  const dialogue = useMemo<Dialogue | undefined>(() => scenario.dialogues[0], [scenario]);
  const lines = dialogue?.lines || [];
  const [lineIndex, setLineIndex] = useState(scenario.progress?.current_line_index || 0);
  const [showTranslation, setShowTranslation] = useState(true);
  const [listeningMode, setListeningMode] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [favorite, setFavorite] = useState(scenario.is_favorited);
  const current = lines[lineIndex];
  const currentAudio = current?.audio_items || [];
  const scenarioAudio = scenario.audio_items || [];
  const hasAudio = scenarioAudio.length > 0 || lines.some((line) => (line.audio_items || []).length > 0);
  const showListeningToggle = hasAudio && !scenario.audio_locked;

  async function toggleFavorite() {
    const next = !favorite;
    setFavorite(next);
    await api.favoriteScenario(scenario.slug, next);
    track("scenario_favorited", {
      telegram_id: user.telegram_id,
      audience_language: user.interface_language,
      properties: { scenario_id: scenario.id, favorite: next }
    });
  }

  async function finish(score: number) {
    await api.completeScenario(scenario.slug, score);
    setCompleted(true);
    haptic("success");
    track("scenario_completed", {
      telegram_id: user.telegram_id,
      audience_language: user.interface_language,
      properties: { scenario_id: scenario.id, score }
    });
  }

  function share() {
    const label = `${ui("scenario.hero_title", "Real-life Korean dialogues")}: ${content(scenario.title)}`;
    const shared = shareRoute({ screen: "scenarios", scenario: scenario.slug }, label);
    if (!shared) {
      openInlineShare(`scenario ${scenario.slug}`);
    }
    track("scenario_shared", {
      telegram_id: user.telegram_id,
      audience_language: user.interface_language,
      properties: { scenario_id: scenario.id }
    });
  }

  return (
    <div className="space-y-4">
      <HeroCard eyebrow={topicLabel(scenario.topic)} title={content(scenario.title)} description={content(scenario.description)}>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={onBack}>{ui("scenario.back", "Back")}</Button>
          <IconButton icon={favorite ? Star : Bookmark} label={ui("scenario.save", "Save scenario")} tone={favorite ? "warning" : "neutral"} onClick={toggleFavorite} />
          <IconButton icon={Share2} label={ui("scenario.share", "Share scenario")} tone="neutral" onClick={share} />
          {scenario.audio_locked ? <StatusChip tone="warning">{ui("lesson.premium", "Premium")} audio</StatusChip> : null}
        </div>
      </HeroCard>

      {scenarioAudio.length ? (
        <Surface>
          <SectionHeading eyebrow={ui("scenario.audio", "Scenario audio")} title={ui("scenario.audio_title", "Hear the full setup first")} description={ui("scenario.audio_description", "Use the scenario-level audio before you step through the dialogue.")} />
          <div className="mt-4 space-y-3">
            {scenarioAudio.map((item) => (
              <AudioPlayer key={item.id} item={item} label={ui("scenario.audio", "Scenario audio")} language={explanationLanguage} completed={completed} />
            ))}
          </div>
        </Surface>
      ) : null}

      {scenario.audio_locked ? (
        <Surface className="border-amber-500/20 bg-amber-500/5">
          <SectionHeading eyebrow={ui("lesson.premium", "Premium")} title={ui("scenario.audio_locked_title", "Listening mode is locked")} description={ui("scenario.audio_locked_description", "This scenario includes premium-only audio. Playback and transcript reveal stay hidden until premium access is active.")} />
        </Surface>
      ) : null}
      {scenario.audio_missing ? (
        <Surface className="border-coral/20 bg-coral/5">
          <SectionHeading eyebrow={ui("lesson.audio_issue", "Audio issue")} title={ui("scenario.audio_issue_title", "Some scenario audio is unavailable")} description={ui("scenario.audio_issue_description", "Playback for one or more premium clips is temporarily unavailable. Dialogue study will still work.")} />
        </Surface>
      ) : null}

      <Surface>
        <SectionHeading eyebrow={ui("scenario.player", "Player")} title={`${lineIndex + 1}/${Math.max(lines.length, 1)}`} description={dialogue ? content(dialogue.explanation, ui("scenario.dialogue", "Scenario dialogue")) : ui("scenario.dialogue", "Scenario dialogue")} />
        <div className="mt-4 grid gap-3">
          <ToggleRow title={ui("scenario.show_translation", "Show translation")} description={ui("scenario.show_translation_description", "Hide it when you want more recall pressure.")} checked={showTranslation} onChange={setShowTranslation} />
          {showListeningToggle ? <ToggleRow title={ui("scenario.listening_mode", "Listening mode")} description={ui("scenario.listening_mode_description", "Focus on audio-first playback when lines include sound.")} checked={listeningMode} onChange={setListeningMode} /> : null}
        </div>
      </Surface>

      {current ? (
        <Surface>
          <div className="flex items-center justify-between gap-3">
            <StatusChip tone="neutral">{current.speaker}</StatusChip>
            {currentAudio.length ? <StatusChip tone="success"><Headphones size={12} /> {ui("lesson.listen", "Listen")}</StatusChip> : null}
            {current.audio_locked ? <StatusChip tone="warning">{ui("vocab.audio_locked", "Audio locked")}</StatusChip> : null}
          </div>
          {currentAudio.length && listeningMode ? (
            <div className="mt-4 space-y-3">
              {currentAudio.map((item, index) => (
                <AudioPlayer key={item.id} item={item} label={ui("scenario.current_line", `Current line ${index + 1}`).replace("{count}", String(index + 1))} language={explanationLanguage} completed={completed} />
              ))}
            </div>
          ) : null}
          <p className="mt-4 text-2xl font-semibold leading-relaxed">{current.korean}</p>
          {current.highlighted_expressions?.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {current.highlighted_expressions.map((item) => <StatusChip key={item} tone="accent">{item}</StatusChip>)}
            </div>
          ) : null}
          {showTranslation ? <p className="mt-4 text-sm leading-7 text-[color:var(--app-muted)]">{content(current.translations)}</p> : null}
          {current.notes ? <p className="mt-2 text-sm leading-6 text-[color:var(--app-muted)]">{content(current.notes)}</p> : null}
          {currentAudio.length && !listeningMode ? (
            <div className="mt-4 space-y-3">
              {currentAudio.map((item, index) => (
                <AudioPlayer key={`${item.id}-${index}`} item={item} label={ui("scenario.current_line", `Current line ${index + 1}`).replace("{count}", String(index + 1))} language={explanationLanguage} completed={completed} />
              ))}
            </div>
          ) : null}

          <div className="mt-5 flex items-center justify-between gap-2">
            <Button variant="secondary" onClick={() => setLineIndex((value) => Math.max(0, value - 1))} disabled={lineIndex === 0}>{ui("scenario.previous_line", "Previous")}</Button>
            {lineIndex + 1 < lines.length ? (
              <Button onClick={() => { setLineIndex((value) => value + 1); haptic("soft"); }}>{ui("scenario.next_line", "Next line")}</Button>
            ) : (
              <Button onClick={() => finish(1)}>{ui("scenario.complete", "Complete scenario")}</Button>
            )}
          </div>
        </Surface>
      ) : null}

      {dialogue?.useful_expressions?.length ? (
        <Surface>
          <SectionHeading eyebrow={ui("scenario.useful_expressions", "Useful expressions")} title={ui("scenario.useful_expressions_title", "Keep these chunks")} description={ui("scenario.useful_expressions_description", "These expressions are worth stealing for your own speech.")} />
          <div className="mt-4 grid gap-3">
            {dialogue.useful_expressions.map((item) => (
              <div key={item.korean} className="rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
                <p className="text-base font-semibold">{item.korean}</p>
                <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{content(item.translations)}</p>
              </div>
            ))}
          </div>
        </Surface>
      ) : null}

      {dialogue?.checks?.length ? (
        <Surface>
          <SectionHeading eyebrow={ui("scenario.comprehension", "Comprehension")} title={ui("scenario.comprehension_title", "Quick checks")} description={ui("scenario.comprehension_description", "Reveal the answer only after you commit to an interpretation.")} />
          <div className="mt-4 grid gap-3">
            {dialogue.checks.map((item, index) => (
              <details key={`${item.answer}-${index}`} className="rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
                <summary className="cursor-pointer text-sm font-semibold">{content(item.prompt)}</summary>
                <p className="mt-3 text-sm leading-6 text-[color:var(--app-muted)]">{item.answer}</p>
              </details>
            ))}
          </div>
        </Surface>
      ) : null}

      {(scenario.related_vocab.length || scenario.related_grammar.length) ? (
        <Surface>
          <SectionHeading eyebrow={ui("scenario.related", "Related material")} title={ui("scenario.related_title", "Jump into linked study notes")} description={ui("scenario.related_description", "Open vocabulary or grammar directly from the scenario context.")} />
          <div className="mt-4 grid gap-3">
            {scenario.related_vocab.slice(0, 5).map((item) => (
              <button key={`v-${item.id}`} type="button" onClick={() => onNavigate({ screen: "vocab", vocabId: item.id })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                <div>
                  <p className="font-semibold">{item.korean}</p>
                  <p className="text-sm text-[color:var(--app-muted)]">{content(item.translations)}</p>
                </div>
                <Link2 size={16} className="text-[color:var(--app-accent)]" />
              </button>
            ))}
            {scenario.related_grammar.slice(0, 4).map((item) => (
              <button key={`g-${item.id}`} type="button" onClick={() => onNavigate({ screen: "grammar", grammarId: item.id })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                <div>
                  <p className="font-semibold">{item.korean_pattern}</p>
                  <p className="text-sm text-[color:var(--app-muted)]">{content(item.title)}</p>
                </div>
                <Link2 size={16} className="text-[color:var(--app-accent)]" />
              </button>
            ))}
          </div>
        </Surface>
      ) : null}

      {completed ? (
        <Surface>
          <SectionHeading eyebrow={ui("scenario.done", "Done")} title={ui("scenario.done_title", "Scenario complete")} description={ui("scenario.done_description", "Use the related grammar or vocab next while the dialogue is still fresh.")} />
          <div className="mt-4 flex flex-wrap gap-2">
            <Button onClick={() => onNavigate({ screen: "review", mode: "mixed", size: 5 })}>{ui("scenario.quick_review", "Quick review")}</Button>
            <Button variant="secondary" onClick={() => onNavigate({ screen: "home" })}>{ui("action.back_home", "Back home")}</Button>
          </div>
        </Surface>
      ) : null}
    </div>
  );
}
