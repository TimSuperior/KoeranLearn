import { BookMarked, Languages, Loader2, Volume2 } from "lucide-react";
import { useEffect, useState } from "react";
import { AudioPlayer } from "../components/ui";
import { Segmented } from "../components/Segmented";
import { api } from "../lib/api";
import type { AuthUser, GrammarPoint, Vocabulary } from "../types";

type Tab = "grammar" | "vocab";

export function LibraryScreen({ user }: { user: AuthUser }) {
  const searchParams = new URLSearchParams(window.location.search);
  const requestedTab = searchParams.get("tab");
  const requestedGrammarId = searchParams.get("grammar");
  const requestedWordId = searchParams.get("word");
  const [tab, setTab] = useState<Tab>("grammar");
  const [grammar, setGrammar] = useState<GrammarPoint[]>([]);
  const [vocab, setVocab] = useState<Vocabulary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (requestedTab === "words" || requestedTab === "vocab") {
      setTab("vocab");
      return;
    }
    if (requestedTab === "grammar") {
      setTab("grammar");
    }
  }, [requestedTab]);

  useEffect(() => {
    let cancelled = false;
    async function loadLibrary() {
      setLoading(true);
      setError("");
      try {
        const [grammarItems, vocabItems] = await Promise.all([api.grammar(), api.vocab()]);
        if (cancelled) return;
        setGrammar(grammarItems);
        setVocab(vocabItems);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load the library.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void loadLibrary();
    return () => {
      cancelled = true;
    };
  }, []);

  const focusedGrammar = requestedGrammarId ? grammar.find((item) => String(item.id) === requestedGrammarId) : null;
  const focusedWord = requestedWordId ? vocab.find((item) => String(item.id) === requestedWordId) : null;

  return (
    <div className="space-y-4">
      <Segmented value={tab} onChange={setTab} options={[{ value: "grammar", label: "Grammar" }, { value: "vocab", label: "Vocabulary" }]} />

      {loading ? (
        <div className="flex min-h-[240px] items-center justify-center rounded-app border border-line bg-white text-sm text-ink/60">
          <Loader2 size={18} className="mr-2 animate-spin" />
          Loading the library...
        </div>
      ) : null}

      {error ? (
        <div className="rounded-app border border-coral/20 bg-coral/5 p-4 text-sm text-coral">{error}</div>
      ) : null}

      {!loading && !error && tab === "grammar" && focusedGrammar ? (
        <section className="rounded-app border border-sky/30 bg-sky/5 p-4">
          <p className="text-xs font-medium uppercase tracking-normal text-ink/55">Focused grammar</p>
          <h2 className="mt-2 text-xl font-semibold">{focusedGrammar.korean_pattern} · {focusedGrammar.title[user.interface_language]}</h2>
          <p className="mt-3 text-sm leading-6 text-ink/75">{focusedGrammar.explanation[user.interface_language]}</p>
          {focusedGrammar.usage_notes[user.interface_language] ? (
            <p className="mt-3 text-sm text-ink/65">{focusedGrammar.usage_notes[user.interface_language]}</p>
          ) : null}
          {focusedGrammar.common_errors[user.interface_language]?.[0] ? (
            <div className="mt-3 rounded-app border border-coral/20 bg-coral/5 p-3 text-sm text-coral">
              {focusedGrammar.common_errors[user.interface_language][0]}
            </div>
          ) : null}
          {focusedGrammar.transfer_notes[user.interface_language]?.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {focusedGrammar.transfer_notes[user.interface_language].slice(0, 4).map((note) => (
                <span key={note} className="rounded-app border border-line bg-white px-2 py-1 text-xs text-ink/65">{note}</span>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      {!loading && !error && tab === "vocab" && focusedWord ? (
        <section className="rounded-app border border-leaf/30 bg-leaf/5 p-4">
          <p className="text-xs font-medium uppercase tracking-normal text-ink/55">Focused word</p>
          <div className="mt-2 flex items-start justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">{focusedWord.korean}</h2>
              {focusedWord.reading ? <p className="mt-1 text-sm text-ink/55">{focusedWord.reading}</p> : null}
            </div>
            {focusedWord.audio_items.length ? (
              <span className="inline-flex items-center gap-1 rounded-app border border-line bg-white px-2 py-1 text-[11px] text-ink/65">
                <Volume2 size={12} />
                Audio
              </span>
            ) : null}
          </div>
          <p className="mt-3 text-sm leading-6 text-ink/75">{focusedWord.translations[user.interface_language]}</p>
          {focusedWord.usage_notes[user.interface_language] ? (
            <p className="mt-3 text-sm text-ink/65">{focusedWord.usage_notes[user.interface_language]}</p>
          ) : null}
          {focusedWord.notes[user.interface_language] ? (
            <p className="mt-2 text-sm text-ink/60">{focusedWord.notes[user.interface_language]}</p>
          ) : null}
          {focusedWord.audio_items.length ? (
            <div className="mt-4 space-y-3">
              {focusedWord.audio_items.map((item) => (
                <AudioPlayer key={item.id} item={item} label="Pronunciation" language={user.interface_language} />
              ))}
            </div>
          ) : null}
          {focusedWord.audio_locked ? <p className="mt-4 text-sm text-coral">Premium pronunciation audio is locked.</p> : null}
        </section>
      ) : null}

      {!loading && !error && tab === "grammar" ? (
        <div className="grid gap-3">
          {grammar.length ? grammar.map((item) => (
            <article key={item.id} className={`rounded-app border bg-white p-4 ${focusedGrammar?.id === item.id ? "border-sky" : "border-line"}`}>
              <div className="flex gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-app bg-sky/10 text-sky">
                  <BookMarked size={20} />
                </div>
                <div className="min-w-0">
                  <h2 className="font-semibold">{item.korean_pattern} · {item.title[user.interface_language]}</h2>
                  <p className="mt-1 text-sm leading-6 text-ink/70">{item.explanation[user.interface_language]}</p>
                  {item.usage_notes[user.interface_language] ? (
                    <p className="mt-2 text-sm text-ink/60">{item.usage_notes[user.interface_language]}</p>
                  ) : null}
                  {item.common_errors[user.interface_language]?.[0] ? (
                    <p className="mt-2 text-sm text-coral">{item.common_errors[user.interface_language][0]}</p>
                  ) : null}
                </div>
              </div>
            </article>
          )) : (
            <div className="rounded-app border border-line bg-white p-5 text-sm text-ink/60">No grammar notes are published yet.</div>
          )}
        </div>
      ) : null}

      {!loading && !error && tab === "vocab" ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {vocab.length ? vocab.map((item) => (
            <article key={item.id} className={`rounded-app border bg-white p-4 ${focusedWord?.id === item.id ? "border-leaf" : "border-line"}`}>
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-app bg-leaf/10 text-leaf">
                  <Languages size={20} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-semibold">{item.korean}</h2>
                      <p className="text-sm text-ink/55">{item.reading}</p>
                    </div>
                    {item.audio_items.length ? (
                      <span className="inline-flex items-center gap-1 rounded-app border border-line bg-panel px-2 py-1 text-[11px] text-ink/65">
                        <Volume2 size={12} />
                        Audio
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm">{item.translations[user.interface_language]}</p>
                  {item.usage_notes[user.interface_language] ? (
                    <p className="mt-2 text-sm text-ink/60">{item.usage_notes[user.interface_language]}</p>
                  ) : null}
                  <p className="mt-3 text-xs text-ink/55">{item.topic} · {item.difficulty}</p>
                  {item.audio_items.length ? (
                    <div className="mt-3 space-y-3">
                      {item.audio_items.map((audio) => (
                        <AudioPlayer key={audio.id} item={audio} label="Pronunciation" language={user.interface_language} />
                      ))}
                    </div>
                  ) : null}
                  {item.audio_locked ? <p className="mt-3 text-sm text-coral">Premium pronunciation audio is locked.</p> : null}
                </div>
              </div>
            </article>
          )) : (
            <div className="rounded-app border border-line bg-white p-5 text-sm text-ink/60">No vocabulary is published yet.</div>
          )}
        </div>
      ) : null}
    </div>
  );
}
