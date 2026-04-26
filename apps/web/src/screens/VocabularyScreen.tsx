import { Bookmark, BookmarkCheck, Ear, Flag, Link2, Search, Star } from "lucide-react";
import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import { AudioPlayer, Button, EmptyState, ErrorState, FilterChip, HeroCard, IconButton, LoadingCard, SectionHeading, StatusChip, Surface } from "../components/ui";
import { track } from "../lib/analytics";
import { t, topicLabel } from "../lib/format";
import { loadWordFlags, saveWordFlags } from "../lib/local-state";
import type { AppRoute } from "../lib/routes";
import { api } from "../lib/api";
import type { AuthUser, ReviewItem, Vocabulary } from "../types";

export function VocabularyScreen({
  user,
  vocabId,
  topic,
  q,
  onNavigate
}: {
  user: AuthUser;
  vocabId?: number;
  topic?: string;
  q?: string;
  onNavigate: (route: AppRoute) => void;
}) {
  const [items, setItems] = useState<Vocabulary[]>([]);
  const [detail, setDetail] = useState<Vocabulary | null>(null);
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState(q || "");
  const deferredSearch = useDeferredValue(search);
  const [activeTopic, setActiveTopic] = useState(topic || "all");
  const [flags, setFlags] = useState<Record<string, { bookmarked?: boolean; difficult?: boolean }>>(() => loadWordFlags(user.telegram_id));

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    Promise.all([api.vocab(), api.reviewQueue(user.telegram_id, false, 80)])
      .then(([vocabItems, reviewQueue]) => {
        if (cancelled) return;
        setItems(vocabItems);
        setReviewItems(reviewQueue.filter((item) => item.item_type === "vocabulary"));
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load vocabulary.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user.telegram_id]);

  useEffect(() => {
    if (!vocabId) {
      setDetail(null);
      return;
    }
    api.vocabDetail(vocabId).then(setDetail).catch(() => undefined);
  }, [vocabId]);

  const reviewMap = useMemo(() => {
    const map = new Map<number, ReviewItem>();
    reviewItems.forEach((item) => map.set(item.item_id, item));
    return map;
  }, [reviewItems]);

  const topics = useMemo(() => ["all", ...Array.from(new Set(items.map((item) => item.topic))).sort()], [items]);

  const filtered = useMemo(() => {
    return items.filter((item) => {
      const matchesTopic = activeTopic === "all" || item.topic === activeTopic;
      const haystack = `${item.korean} ${item.reading || ""} ${Object.values(item.translations).join(" ")} ${item.tags.join(" ")}`.toLowerCase();
      const matchesSearch = !deferredSearch || haystack.includes(deferredSearch.toLowerCase());
      return matchesTopic && matchesSearch;
    });
  }, [activeTopic, deferredSearch, items]);

  function updateWordFlag(id: number, patch: { bookmarked?: boolean; difficult?: boolean }) {
    const next = { ...flags, [String(id)]: { ...flags[String(id)], ...patch } };
    setFlags(next);
    saveWordFlags(user.telegram_id, next);
  }

  function openWord(id: number) {
    onNavigate({ screen: "vocab", vocabId: id, topic: activeTopic !== "all" ? activeTopic : undefined, q: search || undefined });
  }

  if (loading) {
    return <LoadingCard label="Loading vocabulary" />;
  }

  if (error) {
    return <ErrorState description={error} onRetry={() => window.location.reload()} />;
  }

  return (
    <div className="space-y-4">
      <HeroCard eyebrow="Vocabulary" title="Search by topic and review pressure" description="Use bookmarks for your own difficult words, and use review chips to spot what is due now." />

      {detail ? (
        <Surface>
          <SectionHeading
            eyebrow={topicLabel(detail.topic)}
            title={detail.korean}
            description={detail.reading || t(detail.translations, user.interface_language)}
            action={
              <div className="flex gap-2">
                <IconButton
                  icon={flags[String(detail.id)]?.bookmarked ? BookmarkCheck : Bookmark}
                  label="Bookmark"
                  tone={flags[String(detail.id)]?.bookmarked ? "warning" : "neutral"}
                  onClick={() => {
                    const next = !flags[String(detail.id)]?.bookmarked;
                    updateWordFlag(detail.id, { bookmarked: next });
                    track("vocab_bookmark_toggled", {
                      telegram_id: user.telegram_id,
                      audience_language: user.interface_language,
                      properties: { vocab_id: detail.id, bookmarked: next }
                    });
                  }}
                />
                <IconButton
                  icon={flags[String(detail.id)]?.difficult ? Star : Flag}
                  label="Mark difficult"
                  tone={flags[String(detail.id)]?.difficult ? "danger" : "neutral"}
                  onClick={() => {
                    const next = !flags[String(detail.id)]?.difficult;
                    updateWordFlag(detail.id, { difficult: next });
                    track("vocab_difficult_toggled", {
                      telegram_id: user.telegram_id,
                      audience_language: user.interface_language,
                      properties: { vocab_id: detail.id, difficult: next }
                    });
                  }}
                />
              </div>
            }
          />
          <div className="mt-4 flex flex-wrap gap-2">
            {detail.tags.slice(0, 4).map((tag) => <StatusChip key={tag} tone="neutral">{tag}</StatusChip>)}
            {reviewMap.get(detail.id) ? <StatusChip tone={reviewMap.get(detail.id)?.mistake_count ? "danger" : "accent"}>{reviewMap.get(detail.id)?.mastery_status}</StatusChip> : null}
            {detail.audio_locked ? <StatusChip tone="warning">Premium audio</StatusChip> : null}
          </div>
          {detail.audio_items.length ? (
            <div className="mt-4 space-y-3">
              {detail.audio_items.map((item) => (
                <AudioPlayer key={item.id} item={item} label="Pronunciation" language={user.interface_language} />
              ))}
            </div>
          ) : null}
          {detail.audio_locked ? <p className="mt-4 text-sm text-[color:var(--app-secondary)]">Premium pronunciation audio is locked for this item.</p> : null}
          {detail.usage_notes[user.interface_language] ? <p className="mt-4 text-sm leading-7 text-[color:var(--app-muted)]">{detail.usage_notes[user.interface_language]}</p> : null}
          {detail.notes[user.interface_language] ? <p className="mt-2 text-sm leading-7 text-[color:var(--app-muted)]">{detail.notes[user.interface_language]}</p> : null}

          {detail.example_sentences.length ? (
            <div className="mt-5">
              <SectionHeading eyebrow="Examples" title="See the word in context" />
              <div className="mt-3 grid gap-3">
                {detail.example_sentences.slice(0, 3).map((sentence) => (
                  <div key={sentence.id} className="rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
                    <p className="text-base font-semibold">{sentence.korean}</p>
                    <p className="mt-2 text-sm leading-6 text-[color:var(--app-muted)]">{t(sentence.translations, user.interface_language)}</p>
                    {sentence.explanation?.[user.interface_language] ? <p className="mt-2 text-sm leading-6 text-[color:var(--app-muted)]">{t(sentence.explanation, user.interface_language)}</p> : null}
                    {sentence.audio_items.length ? (
                      <div className="mt-3 space-y-3">
                        {sentence.audio_items.map((item) => (
                          <AudioPlayer key={item.id} item={item} label="Example audio" language={user.interface_language} />
                        ))}
                      </div>
                    ) : null}
                    {sentence.audio_locked ? <p className="mt-3 text-sm text-[color:var(--app-secondary)]">Premium example audio is locked.</p> : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {detail.related_scenarios?.length || detail.related_lessons?.length ? (
            <div className="mt-5 grid gap-3">
              {detail.related_lessons?.slice(0, 2).map((lesson) => (
                <button key={`lesson-${lesson.id}`} type="button" onClick={() => onNavigate({ screen: "lesson", lessonId: lesson.id })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                  <div>
                    <p className="font-semibold">{t(lesson.title, user.interface_language)}</p>
                    <p className="text-sm text-[color:var(--app-muted)]">{t(lesson.summary, user.interface_language)}</p>
                  </div>
                  <Link2 size={16} className="text-[color:var(--app-accent)]" />
                </button>
              ))}
              {detail.related_scenarios?.slice(0, 2).map((scenario) => (
                <button key={`scenario-${scenario.id}`} type="button" onClick={() => onNavigate({ screen: "scenarios", scenario: scenario.slug })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                  <div>
                    <p className="font-semibold">{t(scenario.title, user.interface_language)}</p>
                    <p className="text-sm text-[color:var(--app-muted)]">{t(scenario.description, user.interface_language)}</p>
                  </div>
                  <Link2 size={16} className="text-[color:var(--app-accent)]" />
                </button>
              ))}
            </div>
          ) : null}
        </Surface>
      ) : null}

      <Surface>
        <SectionHeading eyebrow="Filters" title="Topic, tag, review state" />
        <div className="mt-4 flex items-center gap-2 rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4">
          <Search size={16} className="text-[color:var(--app-muted)]" />
          <input
            value={search}
            onChange={(event) => startTransition(() => setSearch(event.target.value))}
            placeholder="Search Korean, reading, or translation"
            className="h-12 w-full bg-transparent text-sm outline-none"
          />
        </div>
        <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
          {topics.map((item) => (
            <FilterChip key={item} active={item === activeTopic} onClick={() => setActiveTopic(item)}>
              {item === "all" ? "All" : topicLabel(item)}
            </FilterChip>
          ))}
        </div>
      </Surface>

      {filtered.length === 0 ? <EmptyState title="No matching words" description="Try another topic or a broader search." /> : null}

      <div className="grid gap-3">
        {filtered.map((item) => {
          const state = reviewMap.get(item.id);
          const wordFlags = flags[String(item.id)] || {};
          return (
            <button key={item.id} type="button" onClick={() => openWord(item.id)} className="rounded-[24px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)] p-4 text-left shadow-[0_12px_32px_rgba(15,23,42,0.06)]">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-semibold">{item.korean}</h2>
                    {item.audio_items.length ? <Ear size={16} className="text-[color:var(--app-accent)]" /> : null}
                    {item.audio_locked ? <StatusChip tone="warning">Audio locked</StatusChip> : null}
                  </div>
                  {item.reading ? <p className="mt-1 text-sm text-[color:var(--app-muted)]">{item.reading}</p> : null}
                  <p className="mt-2 text-sm leading-6 text-[color:var(--app-muted)]">{t(item.translations, user.interface_language)}</p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  {wordFlags.bookmarked ? <StatusChip tone="warning">Saved</StatusChip> : null}
                  {wordFlags.difficult ? <StatusChip tone="danger">Difficult</StatusChip> : null}
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <StatusChip tone="neutral">{topicLabel(item.topic)}</StatusChip>
                <StatusChip tone="neutral">{item.difficulty}</StatusChip>
                {state ? <StatusChip tone={state.mistake_count ? "danger" : "accent"}>{state.mastery_status}</StatusChip> : null}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
