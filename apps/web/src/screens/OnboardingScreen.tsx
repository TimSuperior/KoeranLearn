import { CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { api } from "../lib/api";
import type { AuthUser, Language } from "../types";

export function OnboardingScreen({ user, onDone }: { user: AuthUser; onDone: (user: AuthUser) => void }) {
  const [interfaceLanguage, setInterfaceLanguage] = useState<Language>(user.interface_language || "en");
  const [level, setLevel] = useState("complete_beginner");
  const [dailyMinutes, setDailyMinutes] = useState(5);
  const [learningStyle, setLearningStyle] = useState("mixed");
  const [saving, setSaving] = useState(false);

  async function submit() {
    setSaving(true);
    const updated = await api.completeOnboarding(user.telegram_id, {
      interface_language: interfaceLanguage,
      goal: "korean_from_zero",
      level,
      daily_minutes: dailyMinutes,
      learning_style: learningStyle,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Seoul",
      reminder_time: "19:00"
    });
    onDone({ ...user, ...updated });
  }

  return (
    <main className="mx-auto min-h-screen max-w-2xl px-4 py-5">
      <div className="mb-5">
        <h1 className="text-2xl font-semibold">KoreanLearn</h1>
        <p className="mt-1 text-sm text-ink/65">One free guided Korean curriculum in Telegram-sized sessions.</p>
      </div>
      <div className="space-y-4">
        <Choice
          title="Interface language"
          value={interfaceLanguage}
          onChange={(value) => setInterfaceLanguage(value as Language)}
          options={[
            ["ru", "Russian"],
            ["uz", "Uzbek"],
            ["en", "English"]
          ]}
        />
        <Choice
          title="Level"
          value={level}
          onChange={setLevel}
          options={[
            ["complete_beginner", "Complete beginner"],
            ["knows_hangul", "Knows Hangul"],
            ["knows_basics", "Knows basics"]
          ]}
        />
        <Choice
          title="Daily time"
          value={String(dailyMinutes)}
          onChange={(value) => setDailyMinutes(Number(value))}
          options={[
            ["5", "5 min"],
            ["10", "10 min"],
            ["20", "20 min"],
            ["30", "30 min"]
          ]}
        />
        <Choice
          title="Learning style"
          value={learningStyle}
          onChange={setLearningStyle}
          options={[
            ["grammar_first", "Grammar-first"],
            ["mixed", "Mixed"],
            ["phrase_first", "Phrase-first"]
          ]}
        />
      </div>
      <button
        type="button"
        onClick={submit}
        disabled={saving}
        className="mt-5 flex h-12 w-full items-center justify-center gap-2 rounded-app bg-leaf px-4 font-medium text-white disabled:opacity-60"
      >
        <CheckCircle2 size={19} />
        Start curriculum
      </button>
    </main>
  );
}

function Choice({ title, value, options, onChange }: { title: string; value: string; options: string[][]; onChange: (value: string) => void }) {
  return (
    <section className="rounded-app border border-line bg-white p-4">
      <h2 className="mb-3 text-sm font-semibold">{title}</h2>
      <div className="grid gap-2 sm:grid-cols-2">
        {options.map(([optionValue, label]) => (
          <button
            key={optionValue}
            type="button"
            onClick={() => onChange(optionValue)}
            className={`min-h-11 rounded-app border px-3 py-2 text-left text-sm ${value === optionValue ? "border-leaf bg-leaf/10 text-leaf" : "border-line bg-panel text-ink"}`}
          >
            {label}
          </button>
        ))}
      </div>
    </section>
  );
}
