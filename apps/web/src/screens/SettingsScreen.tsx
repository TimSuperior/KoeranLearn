import { useEffect, useState } from "react";

import { Button, ErrorState, Field, HeroCard, LoadingCard, SectionHeading, SelectInput, Surface, TextInput, ToggleRow } from "../components/ui";
import { useI18n } from "../lib/i18n";
import { api } from "../lib/api";
import { interpolate } from "../lib/format";
import { clearPersonalization } from "../lib/local-state";
import { maybeAddToHomeScreen } from "../lib/telegram";
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

export function SettingsScreen({ user, onUserChange }: { user: AuthUser; onUserChange: (user: AuthUser) => void }) {
  const { ui } = useI18n();
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [audioPrefs, setAudioPrefs] = useState<AudioPrefs>(() => loadAudioPrefs(user.telegram_id));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.settings().then(setSettings).catch(() => setError(ui("settings.load_error", "Could not load settings.")));
  }, [ui]);

  useEffect(() => {
    saveAudioPrefs(user.telegram_id, audioPrefs);
  }, [audioPrefs, user.telegram_id]);

  if (error) {
    return <ErrorState description={error} onRetry={() => window.location.reload()} />;
  }

  if (!settings) {
    return <LoadingCard label={ui("settings.loading", "Loading settings")} />;
  }

  async function save() {
    setSaving(true);
    setSaved(false);
    try {
      const next = (await api.updateSettings(settings as Record<string, unknown>)) as UserSettings;
      setSettings(next);
      onUserChange({
        ...user,
        interface_language: next.interface_language,
        explanation_language: next.explanation_language,
      });
      setSaved(true);
    } catch {
      setError(ui("settings.save_error", "Could not save settings."));
    } finally {
      setSaving(false);
    }
  }

  function languageOption(language: Language) {
    return ui(`language.${language}`, language.toUpperCase());
  }

  return (
    <div className="space-y-4">
      <HeroCard
        eyebrow={ui("settings.hero_eyebrow", "Settings")}
        title={ui("settings.hero_title", "Personalize the learning product")}
        description={ui("settings.hero_description", "Keep the defaults pragmatic. Only the settings that actually change daily use are surfaced here.")}
      />

      <Surface>
        <SectionHeading eyebrow={ui("settings.language_eyebrow", "Language")} title={ui("settings.language_title", "Interface and explanation language")} />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label={ui("settings.interface_language", "Interface language")}>
            <SelectInput value={settings.interface_language} onChange={(event) => setSettings({ ...settings, interface_language: event.target.value as Language })}>
              <option value="en">{languageOption("en")}</option>
              <option value="ru">{languageOption("ru")}</option>
              <option value="uz">{languageOption("uz")}</option>
            </SelectInput>
          </Field>
          <Field label={ui("settings.explanation_language", "Explanation language")}>
            <SelectInput value={settings.explanation_language} onChange={(event) => setSettings({ ...settings, explanation_language: event.target.value as Language })}>
              <option value="en">{languageOption("en")}</option>
              <option value="ru">{languageOption("ru")}</option>
              <option value="uz">{languageOption("uz")}</option>
            </SelectInput>
          </Field>
        </div>
      </Surface>

      <Surface>
        <SectionHeading
          eyebrow={ui("settings.reminders_eyebrow", "Reminders")}
          title={ui("settings.reminders_title", "Study nudge")}
          description={ui("settings.reminders_description", "Keep reminders simple: on, time, timezone.")}
        />
        <div className="mt-4 grid gap-3">
          <ToggleRow
            title={ui("settings.reminders_toggle", "Reminders")}
            description={ui("settings.reminders_toggle_description", "Telegram nudges for study and review.")}
            checked={settings.reminders_enabled}
            onChange={(value) => setSettings({ ...settings, reminders_enabled: value })}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={ui("settings.reminder_time", "Reminder time")}>
              <TextInput type="time" value={settings.reminder_time} onChange={(event) => setSettings({ ...settings, reminder_time: event.target.value })} />
            </Field>
            <Field label={ui("settings.timezone", "Timezone")}>
              <TextInput value={settings.timezone} onChange={(event) => setSettings({ ...settings, timezone: event.target.value })} />
            </Field>
          </div>
        </div>
      </Surface>

      <Surface>
        <SectionHeading
          eyebrow={ui("settings.learning_eyebrow", "Learning")}
          title={ui("settings.learning_title", "Difficulty and style")}
          description={ui("settings.learning_description", "Keep these only if they still change the study experience for you.")}
        />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label={ui("settings.learning_style", "Learning style")}>
            <SelectInput value={settings.learning_style} onChange={(event) => setSettings({ ...settings, learning_style: event.target.value })}>
              <option value="mixed">{ui("style.mixed", "Mixed")}</option>
              <option value="grammar_first">{ui("style.grammar_first", "Grammar first")}</option>
              <option value="phrase_first">{ui("style.phrase_first", "Phrase first")}</option>
            </SelectInput>
          </Field>
          <Field label={ui("settings.difficulty", "Difficulty")}>
            <SelectInput value={settings.difficulty} onChange={(event) => setSettings({ ...settings, difficulty: event.target.value })}>
              <option value="easy">{ui("difficulty.easy", "Easy")}</option>
              <option value="normal">{ui("difficulty.normal", "Normal")}</option>
              <option value="hard">{ui("difficulty.hard", "Hard")}</option>
            </SelectInput>
          </Field>
        </div>
      </Surface>

      <Surface>
        <SectionHeading
          eyebrow={ui("settings.audio_eyebrow", "Audio")}
          title={ui("settings.audio_title", "Listening preferences")}
          description={ui("settings.audio_description", "These stay local on this device unless Telegram later offers synced device storage for your setup.")}
        />
        <div className="mt-4 grid gap-3">
          <ToggleRow
            title={ui("settings.auto_play", "Auto-play line audio")}
            description={ui("settings.auto_play_description", "Useful in scenarios when lines already have recorded audio.")}
            checked={audioPrefs.auto_play_line_audio}
            onChange={(value) => setAudioPrefs({ ...audioPrefs, auto_play_line_audio: value })}
          />
          <ToggleRow
            title={ui("settings.prefer_listening", "Prefer listening mode")}
            description={ui("settings.prefer_listening_description", "Open scenario lines with translation hidden and audio first.")}
            checked={audioPrefs.prefer_listening_mode}
            onChange={(value) => setAudioPrefs({ ...audioPrefs, prefer_listening_mode: value })}
          />
        </div>
      </Surface>

      <Surface>
        <SectionHeading
          eyebrow={ui("settings.session_eyebrow", "Session")}
          title={ui("settings.session_title", "Account and local visibility")}
          description={ui("settings.session_description", "A practical privacy note instead of fake controls.")}
        />
        <div className="mt-4 grid gap-3">
          <div className="rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
            <p className="text-sm font-semibold">{ui("settings.telegram_session", "Telegram session")}</p>
            <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">
              {interpolate(ui("settings.telegram_session_description", "Signed in as `{id}` inside the Mini App. Learning state is tied to this Telegram account."), { id: user.telegram_id })}
            </p>
          </div>
          <div className="rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
            <p className="text-sm font-semibold">{ui("settings.local_personalization", "Local personalization")}</p>
            <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{ui("settings.local_personalization_description", "Bookmarks, difficult-word flags, and audio preferences are currently stored on this device.")}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => {
                  clearPersonalization(user.telegram_id);
                  localStorage.removeItem(`miniapp:audio-prefs:${user.telegram_id}`);
                  setAudioPrefs({ auto_play_line_audio: false, prefer_listening_mode: false });
                }}
              >
                {ui("settings.clear_local", "Clear local personalization")}
              </Button>
              <Button variant="ghost" onClick={() => maybeAddToHomeScreen()}>
                {ui("settings.add_home", "Add to home screen")}
              </Button>
            </div>
          </div>
        </div>
      </Surface>

      <div className="flex flex-wrap gap-2">
        <Button onClick={save} disabled={saving}>
          {saving ? ui("action.save", "Save") : saved ? ui("action.saved", "Saved") : ui("settings.save", "Save settings")}
        </Button>
      </div>
    </div>
  );
}
