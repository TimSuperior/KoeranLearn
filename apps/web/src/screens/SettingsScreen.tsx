import { Bell, Languages, Save, ShieldCheck, Volume2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Button, EmptyState, ErrorState, Field, HeroCard, LoadingCard, SectionHeading, SelectInput, Surface, TextInput, ToggleRow } from "../components/ui";
import { clearPersonalization } from "../lib/local-state";
import { maybeAddToHomeScreen } from "../lib/telegram";
import { api } from "../lib/api";
import type { AuthUser, Language, UserSettings } from "../types";

type AudioPrefs = {
  auto_play_line_audio: boolean;
  prefer_listening_mode: boolean;
};

function loadAudioPrefs(userId: string): AudioPrefs {
  try {
    const raw = localStorage.getItem(`miniapp:audio-prefs:${userId}`);
    return raw ? (JSON.parse(raw) as AudioPrefs) : { auto_play_line_audio: false, prefer_listening_mode: false };
  } catch {
    return { auto_play_line_audio: false, prefer_listening_mode: false };
  }
}

function saveAudioPrefs(userId: string, prefs: AudioPrefs) {
  localStorage.setItem(`miniapp:audio-prefs:${userId}`, JSON.stringify(prefs));
}

export function SettingsScreen({ user }: { user: AuthUser }) {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [audioPrefs, setAudioPrefs] = useState<AudioPrefs>(() => loadAudioPrefs(user.telegram_id));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.settings().then(setSettings).catch((err) => setError(err instanceof Error ? err.message : "Could not load settings."));
  }, []);

  useEffect(() => {
    saveAudioPrefs(user.telegram_id, audioPrefs);
  }, [audioPrefs, user.telegram_id]);

  if (error) {
    return <ErrorState description={error} onRetry={() => window.location.reload()} />;
  }

  if (!settings) {
    return <LoadingCard label="Loading settings" />;
  }

  async function save() {
    setSaving(true);
    setSaved(false);
    try {
      const next = await api.updateSettings(settings as Record<string, unknown>);
      setSettings(next as UserSettings);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save settings.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <HeroCard eyebrow="Settings" title="Personalize the learning product" description="Keep the defaults pragmatic. Only the settings that actually change daily use are surfaced here." />

      <Surface>
        <SectionHeading eyebrow="Language" title="Interface and explanation language" />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label="Interface language">
            <SelectInput value={settings.interface_language} onChange={(event) => setSettings({ ...settings, interface_language: event.target.value as Language })}>
              <option value="en">English</option>
              <option value="ru">Russian</option>
              <option value="uz">Uzbek</option>
            </SelectInput>
          </Field>
          <Field label="Explanation language">
            <SelectInput value={settings.explanation_language} onChange={(event) => setSettings({ ...settings, explanation_language: event.target.value as Language })}>
              <option value="en">English</option>
              <option value="ru">Russian</option>
              <option value="uz">Uzbek</option>
            </SelectInput>
          </Field>
        </div>
      </Surface>

      <Surface>
        <SectionHeading eyebrow="Reminders" title="Study nudge" description="Keep reminders simple: on, time, timezone." />
        <div className="mt-4 grid gap-3">
          <ToggleRow title="Reminders" description="Telegram nudges for study and review." checked={settings.reminders_enabled} onChange={(value) => setSettings({ ...settings, reminders_enabled: value })} />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Reminder time">
              <TextInput type="time" value={settings.reminder_time} onChange={(event) => setSettings({ ...settings, reminder_time: event.target.value })} />
            </Field>
            <Field label="Timezone">
              <TextInput value={settings.timezone} onChange={(event) => setSettings({ ...settings, timezone: event.target.value })} />
            </Field>
          </div>
        </div>
      </Surface>

      <Surface>
        <SectionHeading eyebrow="Learning" title="Difficulty and style" description="Keep these only if they still change the study experience for you." />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label="Learning style">
            <SelectInput value={settings.learning_style} onChange={(event) => setSettings({ ...settings, learning_style: event.target.value })}>
              <option value="mixed">Mixed</option>
              <option value="grammar_first">Grammar first</option>
              <option value="phrase_first">Phrase first</option>
            </SelectInput>
          </Field>
          <Field label="Difficulty">
            <SelectInput value={settings.difficulty} onChange={(event) => setSettings({ ...settings, difficulty: event.target.value })}>
              <option value="easy">Easy</option>
              <option value="normal">Normal</option>
              <option value="hard">Hard</option>
            </SelectInput>
          </Field>
        </div>
      </Surface>

      <Surface>
        <SectionHeading eyebrow="Audio" title="Listening preferences" description="These stay local on this device unless Telegram later offers synced device storage for your setup." />
        <div className="mt-4 grid gap-3">
          <ToggleRow title="Auto-play line audio" description="Useful in scenarios when lines already have recorded audio." checked={audioPrefs.auto_play_line_audio} onChange={(value) => setAudioPrefs({ ...audioPrefs, auto_play_line_audio: value })} />
          <ToggleRow title="Prefer listening mode" description="Open scenario lines with translation hidden and audio first." checked={audioPrefs.prefer_listening_mode} onChange={(value) => setAudioPrefs({ ...audioPrefs, prefer_listening_mode: value })} />
        </div>
      </Surface>

      <Surface>
        <SectionHeading eyebrow="Session" title="Account and local visibility" description="A practical privacy note instead of fake controls." />
        <div className="mt-4 grid gap-3">
          <div className="rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
            <p className="text-sm font-semibold">Telegram session</p>
            <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">Signed in as `{user.telegram_id}` inside the Mini App. Learning state is tied to this Telegram account.</p>
          </div>
          <div className="rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
            <p className="text-sm font-semibold">Local personalization</p>
            <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">Bookmarks, difficult-word flags, and audio preferences are currently stored on this device.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => {
                  clearPersonalization(user.telegram_id);
                  localStorage.removeItem(`miniapp:audio-prefs:${user.telegram_id}`);
                  setAudioPrefs({ auto_play_line_audio: false, prefer_listening_mode: false });
                }}
              >
                Clear local personalization
              </Button>
              <Button variant="ghost" onClick={() => maybeAddToHomeScreen()}>Add to home screen</Button>
            </div>
          </div>
        </div>
      </Surface>

      <div className="flex flex-wrap gap-2">
        <Button onClick={save} disabled={saving}>
          <Save size={16} />
          {saving ? "Saving..." : saved ? "Saved" : "Save settings"}
        </Button>
      </div>
    </div>
  );
}
