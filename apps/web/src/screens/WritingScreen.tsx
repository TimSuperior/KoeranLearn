import { Send } from "lucide-react";
import { useState } from "react";
import { api } from "../lib/api";
import type { AuthUser } from "../types";

export function WritingScreen({ user }: { user: AuthUser }) {
  const [text, setText] = useState("저는학생이에요");
  const [register, setRegister] = useState("polite_informal");
  const [result, setResult] = useState<{ corrected_text: string; natural_text: string; feedback: Record<string, unknown>; provider: string; remaining_daily_quota: number } | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    setResult(await api.correctWriting(user.telegram_id, text, register));
    setBusy(false);
  }

  return (
    <div className="space-y-4">
      <section className="rounded-app border border-line bg-white p-4">
        <textarea
          className="min-h-28 w-full resize-y rounded-app border border-line bg-panel p-3 outline-none focus:border-leaf"
          value={text}
          onChange={(event) => setText(event.target.value)}
          maxLength={500}
        />
        <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto]">
          <select className="h-11 rounded-app border border-line bg-panel px-3" value={register} onChange={(event) => setRegister(event.target.value)}>
            <option value="polite_informal">Polite informal</option>
            <option value="formal_polite">Formal polite</option>
            <option value="casual">Casual</option>
            <option value="honorific">Honorific</option>
          </select>
          <button className="flex h-11 items-center justify-center gap-2 rounded-app bg-leaf px-4 font-medium text-white disabled:opacity-60" type="button" onClick={submit} disabled={busy}>
            <Send size={18} />
            Correct
          </button>
        </div>
      </section>

      {result ? (
        <section className="rounded-app border border-line bg-white p-4">
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <p className="text-xs font-medium uppercase tracking-normal text-ink/55">Corrected</p>
              <p className="mt-1 text-lg font-semibold">{result.corrected_text}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-normal text-ink/55">Natural</p>
              <p className="mt-1 text-lg font-semibold">{result.natural_text}</p>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            {Array.isArray(result.feedback.issues)
              ? result.feedback.issues.map((issue: { type: string; message: string }, index: number) => (
                  <div key={`${issue.type}-${index}`} className="rounded-app bg-panel p-3 text-sm">
                    <span className="font-medium">{issue.type}:</span> {issue.message}
                  </div>
                ))
              : null}
          </div>
          <p className="mt-3 text-xs text-ink/55">Provider: {result.provider} · remaining today {result.remaining_daily_quota}</p>
        </section>
      ) : null}
    </div>
  );
}
