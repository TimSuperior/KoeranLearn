import { Bookmark, Check, Ear, Eye, EyeOff, Headphones, Link2, MessageCircleMore, PlayCircle, Share2, Star } from "lucide-react";
import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import { AudioPlayer, Button, EmptyState, ErrorState, FilterChip, HeroCard, IconButton, LoadingCard, SectionHeading, StatusChip, Surface, ToggleRow } from "../components/ui";
import { track } from "../lib/analytics";
import { t, topicLabel } from "../lib/format";
import type { AppRoute } from "../lib/routes";
import { api } from "../lib/api";
import { haptic, openInlineShare, shareRoute } from "../lib/telegram";
import type { AudioCue, AuthUser, Dialogue, DialogueLine, Scenario, ScenarioDetail } from "../types";

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
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load scenarios.");
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
      <HeroCard eyebrow="Scenario practice" title="Real-life Korean dialogues" description="Pick a context, hide translations when you want pressure, and switch to listening mode when audio is available." />

      <Surface>
        <SectionHeading eyebrow="Filters" title="Find the right situation" />
        <input
          value={query}
          onChange={(event) => startTransition(() => setQuery(event.target.value))}
          placeholder="Search by topic or situation"
          className="mt-4 h-12 w-full rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 text-sm outline-none focus:border-[color:var(--app-accent)]"
        />
        <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
          {topics.map((item) => (
            <FilterChip key={item} active={topic === item} onClick={() => setTopic(item)}>
              {item === "all" ? "All" : topicLabel(item)}
            </FilterChip>
          ))}
        </div>
      </Surface>

      {loading ? <LoadingCard label="Loading scenarios" /> : null}
      {error ? <ErrorState description={error} onRetry={() => window.location.reload()} /> : null}

      {!loading && !error && items.length === 0 ? (
        <EmptyState title="No matching scenarios" description="Try a broader topic or clear the search to browse all published dialogues." />
      ) : null}

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
                  <h2 className="text-base font-semibold">{t(scenario.title, user.interface_language)}</h2>
                  <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{t(scenario.description, user.interface_language)}</p>
                </div>
              </div>
              {scenario.progress?.status === "in_progress" ? <StatusChip tone="accent">Continue</StatusChip> : null}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <StatusChip tone="neutral">{topicLabel(scenario.topic)}</StatusChip>
              <StatusChip tone="neutral">{scenario.difficulty}</StatusChip>
              {scenario.context_labels.slice(0, 2).map((label) => (
                <StatusChip key={label} tone="neutral">{label.replaceAll("_", " ")}</StatusChip>
              ))}
              {scenario.is_favorited ? <StatusChip tone="warning">Saved</StatusChip> : null}
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
    const label = `Practice this Korean scenario: ${t(scenario.title, user.interface_language)}`;
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
      <HeroCard eyebrow={topicLabel(scenario.topic)} title={t(scenario.title, user.interface_language)} description={t(scenario.description, user.interface_language)}>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={onBack}>Back</Button>
          <IconButton icon={favorite ? Star : Bookmark} label="Save scenario" tone={favorite ? "warning" : "neutral"} onClick={toggleFavorite} />
          <IconButton icon={Share2} label="Share scenario" tone="neutral" onClick={share} />
          {scenario.audio_locked ? <StatusChip tone="warning">Premium audio</StatusChip> : null}
        </div>
      </HeroCard>

      {scenarioAudio.length ? (
        <Surface>
          <SectionHeading eyebrow="Scenario audio" title="Hear the full setup first" description="Use the scenario-level audio before you step through the dialogue." />
          <div className="mt-4 space-y-3">
            {scenarioAudio.map((item) => (
              <AudioPlayer key={item.id} item={item} label="Scenario track" language={user.interface_language} completed={completed} />
            ))}
          </div>
        </Surface>
      ) : null}

      {scenario.audio_locked ? (
        <Surface className="border-amber-500/20 bg-amber-500/5">
          <SectionHeading eyebrow="Premium" title="Listening mode is locked" description="This scenario includes premium-only audio. Playback and transcript reveal stay hidden until premium access is active." />
        </Surface>
      ) : null}
      {scenario.audio_missing ? (
        <Surface className="border-coral/20 bg-coral/5">
          <SectionHeading eyebrow="Audio issue" title="Some scenario audio is unavailable" description="Playback for one or more premium clips is temporarily unavailable. Dialogue study will still work." />
        </Surface>
      ) : null}

      <Surface>
        <SectionHeading eyebrow="Player" title={`${lineIndex + 1}/${Math.max(lines.length, 1)} lines`} description={dialogue ? t(dialogue.explanation, user.interface_language) : "Scenario dialogue"} />
        <div className="mt-4 grid gap-3">
          <ToggleRow title="Show translation" description="Hide it when you want more recall pressure." checked={showTranslation} onChange={setShowTranslation} />
          {showListeningToggle ? <ToggleRow title="Listening mode" description="Focus on audio-first playback when lines include sound." checked={listeningMode} onChange={setListeningMode} /> : null}
        </div>
      </Surface>

      {current ? (
        <Surface>
          <div className="flex items-center justify-between gap-3">
            <StatusChip tone="neutral">{current.speaker}</StatusChip>
            {currentAudio.length ? <StatusChip tone="success"><Headphones size={12} /> Audio</StatusChip> : null}
            {current.audio_locked ? <StatusChip tone="warning">Locked</StatusChip> : null}
          </div>
          {currentAudio.length && listeningMode ? (
            <div className="mt-4 space-y-3">
              {currentAudio.map((item, index) => (
                <AudioPlayer key={item.id} item={item} label={`Current line ${index + 1}`} language={user.interface_language} completed={completed} />
              ))}
            </div>
          ) : null}
          <p className="mt-4 text-2xl font-semibold leading-relaxed">{current.korean}</p>
          {current.highlighted_expressions?.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {current.highlighted_expressions.map((item) => <StatusChip key={item} tone="accent">{item}</StatusChip>)}
            </div>
          ) : null}
          {showTranslation ? <p className="mt-4 text-sm leading-7 text-[color:var(--app-muted)]">{t(current.translations, user.interface_language)}</p> : null}
          {current.notes ? <p className="mt-2 text-sm leading-6 text-[color:var(--app-muted)]">{t(current.notes, user.interface_language)}</p> : null}
          {currentAudio.length && !listeningMode ? (
            <div className="mt-4 space-y-3">
              {currentAudio.map((item, index) => (
                <AudioPlayer key={`${item.id}-${index}`} item={item} label={`Current line ${index + 1}`} language={user.interface_language} completed={completed} />
              ))}
            </div>
          ) : null}

          <div className="mt-5 flex items-center justify-between gap-2">
            <Button variant="secondary" onClick={() => setLineIndex((value) => Math.max(0, value - 1))} disabled={lineIndex === 0}>Previous</Button>
            {lineIndex + 1 < lines.length ? (
              <Button onClick={() => { setLineIndex((value) => value + 1); haptic("soft"); }}>Next line</Button>
            ) : (
              <Button onClick={() => finish(1)}>Complete scenario</Button>
            )}
          </div>
        </Surface>
      ) : null}

      {dialogue?.useful_expressions?.length ? (
        <Surface>
          <SectionHeading eyebrow="Useful expressions" title="Keep these chunks" description="These expressions are worth stealing for your own speech." />
          <div className="mt-4 grid gap-3">
            {dialogue.useful_expressions.map((item) => (
              <div key={item.korean} className="rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
                <p className="text-base font-semibold">{item.korean}</p>
                <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{t(item.translations, user.interface_language)}</p>
              </div>
            ))}
          </div>
        </Surface>
      ) : null}

      {dialogue?.checks?.length ? (
        <Surface>
          <SectionHeading eyebrow="Comprehension" title="Quick checks" description="Reveal the answer only after you commit to an interpretation." />
          <div className="mt-4 grid gap-3">
            {dialogue.checks.map((item, index) => (
              <details key={`${item.answer}-${index}`} className="rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
                <summary className="cursor-pointer text-sm font-semibold">{t(item.prompt, user.interface_language)}</summary>
                <p className="mt-3 text-sm leading-6 text-[color:var(--app-muted)]">{item.answer}</p>
              </details>
            ))}
          </div>
        </Surface>
      ) : null}

      {(scenario.related_vocab.length || scenario.related_grammar.length) ? (
        <Surface>
          <SectionHeading eyebrow="Related material" title="Jump into linked study notes" description="Open vocabulary or grammar directly from the scenario context." />
          <div className="mt-4 grid gap-3">
            {scenario.related_vocab.slice(0, 5).map((item) => (
              <button key={`v-${item.id}`} type="button" onClick={() => onNavigate({ screen: "vocab", vocabId: item.id })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                <div>
                  <p className="font-semibold">{item.korean}</p>
                  <p className="text-sm text-[color:var(--app-muted)]">{t(item.translations, user.interface_language)}</p>
                </div>
                <Link2 size={16} className="text-[color:var(--app-accent)]" />
              </button>
            ))}
            {scenario.related_grammar.slice(0, 4).map((item) => (
              <button key={`g-${item.id}`} type="button" onClick={() => onNavigate({ screen: "grammar", grammarId: item.id })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                <div>
                  <p className="font-semibold">{item.korean_pattern}</p>
                  <p className="text-sm text-[color:var(--app-muted)]">{t(item.title, user.interface_language)}</p>
                </div>
                <Link2 size={16} className="text-[color:var(--app-accent)]" />
              </button>
            ))}
          </div>
        </Surface>
      ) : null}

      {completed ? (
        <Surface>
          <SectionHeading eyebrow="Done" title="Scenario complete" description="Use the related grammar or vocab next while the dialogue is still fresh." />
          <div className="mt-4 flex flex-wrap gap-2">
            <Button onClick={() => onNavigate({ screen: "review", mode: "mixed", size: 5 })}>Quick review</Button>
            <Button variant="secondary" onClick={() => onNavigate({ screen: "home" })}>Back home</Button>
          </div>
        </Surface>
      ) : null}
    </div>
  );
}
