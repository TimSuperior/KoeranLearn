import { ArrowRight, BookOpenCheck, GraduationCap, Search } from "lucide-react";
import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import { AudioPlayer, Button, EmptyState, ErrorState, FilterChip, HeroCard, LoadingCard, SectionHeading, StatusChip, Surface } from "../components/ui";
import { t, topicLabel } from "../lib/format";
import type { AppRoute } from "../lib/routes";
import { api } from "../lib/api";
import type { AuthUser, GrammarPoint, ReviewItem } from "../types";

export function GrammarScreen({
  user,
  grammarId,
  topic,
  q,
  onNavigate
}: {
  user: AuthUser;
  grammarId?: number;
  topic?: string;
  q?: string;
  onNavigate: (route: AppRoute) => void;
}) {
  const [items, setItems] = useState<GrammarPoint[]>([]);
  const [detail, setDetail] = useState<GrammarPoint | null>(null);
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState(q || "");
  const deferredSearch = useDeferredValue(search);
  const [activeTopic, setActiveTopic] = useState(topic || "all");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    Promise.all([api.grammar(), api.reviewQueue(user.telegram_id, false, 80)])
      .then(([grammarItems, reviewQueue]) => {
        if (cancelled) return;
        setItems(grammarItems);
        setReviewItems(reviewQueue.filter((item) => item.item_type === "grammar"));
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load grammar.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [user.telegram_id]);

  useEffect(() => {
    if (!grammarId) {
      setDetail(null);
      return;
    }
    api.grammarDetail(grammarId).then(setDetail).catch(() => undefined);
  }, [grammarId]);

  const topics = useMemo(() => ["all", ...Array.from(new Set(items.map((item) => item.category))).sort()], [items]);
  const reviewMap = useMemo(() => {
    const map = new Map<number, ReviewItem>();
    reviewItems.forEach((item) => map.set(item.item_id, item));
    return map;
  }, [reviewItems]);

  const filtered = useMemo(() => {
    return items.filter((item) => {
      const matchesTopic = activeTopic === "all" || item.category === activeTopic;
      const haystack = `${item.korean_pattern} ${Object.values(item.title).join(" ")} ${Object.values(item.explanation).join(" ")} ${item.tags.join(" ")}`.toLowerCase();
      const matchesSearch = !deferredSearch || haystack.includes(deferredSearch.toLowerCase());
      return matchesTopic && matchesSearch;
    });
  }, [activeTopic, deferredSearch, items]);

  if (loading) {
    return <LoadingCard label="Loading grammar" />;
  }

  if (error) {
    return <ErrorState description={error} onRetry={() => window.location.reload()} />;
  }

  return (
    <div className="space-y-4">
      <HeroCard eyebrow="Grammar" title="Localized explanations and common transfer mistakes" description="Use the grammar view when you want explicit structure, linked scenarios, and a quick route back into practice." />

      {detail ? (
        <Surface>
          <SectionHeading
            eyebrow={topicLabel(detail.category)}
            title={`${detail.korean_pattern} • ${t(detail.title, user.interface_language)}`}
            description={t(detail.explanation, user.interface_language)}
            action={reviewMap.get(detail.id) ? <StatusChip tone={reviewMap.get(detail.id)?.mistake_count ? "danger" : "accent"}>{reviewMap.get(detail.id)?.mastery_status}</StatusChip> : null}
          />
          {detail.usage_notes[user.interface_language] ? <p className="mt-4 text-sm leading-7 text-[color:var(--app-muted)]">{detail.usage_notes[user.interface_language]}</p> : null}

          {detail.common_errors[user.interface_language]?.length ? (
            <div className="mt-5 rounded-[22px] border border-[color:var(--app-secondary)]/20 bg-[color:var(--app-secondary)]/6 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--app-secondary)]">Common mistakes</p>
              <div className="mt-3 space-y-2">
                {detail.common_errors[user.interface_language].slice(0, 3).map((item) => (
                  <p key={item} className="text-sm leading-6 text-[color:var(--app-text)]">{item}</p>
                ))}
              </div>
            </div>
          ) : null}

          {detail.transfer_notes[user.interface_language]?.length ? (
            <div className="mt-5">
              <SectionHeading eyebrow="Transfer notes" title="Bridge from your learner language" />
              <div className="mt-3 flex flex-wrap gap-2">
                {detail.transfer_notes[user.interface_language].slice(0, 5).map((item) => <StatusChip key={item} tone="neutral">{item}</StatusChip>)}
              </div>
            </div>
          ) : null}

          {detail.example_sentences?.length ? (
            <div className="mt-5">
              <SectionHeading eyebrow="Examples" title="Hear and compare the pattern in use" />
              <div className="mt-3 grid gap-3">
                {detail.example_sentences.slice(0, 4).map((sentence) => (
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

          {detail.related_lessons?.length || detail.related_scenarios?.length ? (
            <div className="mt-5 grid gap-3">
              {detail.related_lessons?.slice(0, 2).map((lesson) => (
                <button key={`lesson-${lesson.id}`} type="button" onClick={() => onNavigate({ screen: "lesson", lessonId: lesson.id })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                  <div>
                    <p className="font-semibold">{t(lesson.title, user.interface_language)}</p>
                    <p className="text-sm text-[color:var(--app-muted)]">{t(lesson.summary, user.interface_language)}</p>
                  </div>
                  <ArrowRight size={16} className="text-[color:var(--app-accent)]" />
                </button>
              ))}
              {detail.related_scenarios?.slice(0, 2).map((scenario) => (
                <button key={`scenario-${scenario.id}`} type="button" onClick={() => onNavigate({ screen: "scenarios", scenario: scenario.slug })} className="flex items-center justify-between rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 py-3 text-left">
                  <div>
                    <p className="font-semibold">{t(scenario.title, user.interface_language)}</p>
                    <p className="text-sm text-[color:var(--app-muted)]">{t(scenario.description, user.interface_language)}</p>
                  </div>
                  <ArrowRight size={16} className="text-[color:var(--app-accent)]" />
                </button>
              ))}
            </div>
          ) : null}

          <div className="mt-5 flex flex-wrap gap-2">
            <Button onClick={() => onNavigate({ screen: "review", mode: "grammar", size: 5 })}>Quick grammar review</Button>
            <Button variant="secondary" onClick={() => onNavigate({ screen: "review", mode: "mixed", size: 5 })}>Mixed practice</Button>
          </div>
        </Surface>
      ) : null}

      <Surface>
        <SectionHeading eyebrow="Filters" title="Category and pattern search" />
        <div className="mt-4 flex items-center gap-2 rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4">
          <Search size={16} className="text-[color:var(--app-muted)]" />
          <input
            value={search}
            onChange={(event) => startTransition(() => setSearch(event.target.value))}
            placeholder="Search pattern or explanation"
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

      {filtered.length === 0 ? <EmptyState title="No matching grammar points" description="Try another category or a broader search." /> : null}

      <div className="grid gap-3">
        {filtered.map((item) => {
          const state = reviewMap.get(item.id);
          return (
            <button key={item.id} type="button" onClick={() => onNavigate({ screen: "grammar", grammarId: item.id, topic: activeTopic !== "all" ? activeTopic : undefined, q: search || undefined })} className="rounded-[24px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)] p-4 text-left shadow-[0_12px_32px_rgba(15,23,42,0.06)]">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px] border border-[color:var(--app-accent)]/20 bg-[color:var(--app-accent)]/10 text-[color:var(--app-accent)]">
                  <GraduationCap size={20} />
                </div>
                <div className="min-w-0">
                  <h2 className="text-base font-semibold">{item.korean_pattern} • {t(item.title, user.interface_language)}</h2>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--app-muted)]">{t(item.explanation, user.interface_language)}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <StatusChip tone="neutral">{topicLabel(item.category)}</StatusChip>
                    <StatusChip tone="neutral">{item.difficulty}</StatusChip>
                    {state ? <StatusChip tone={state.mistake_count ? "danger" : "accent"}>{state.mastery_status}</StatusChip> : null}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
