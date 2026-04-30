import { useEffect, useId, useRef, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, ChevronRight, Loader2, Pause, Play, RotateCcw } from "lucide-react";

import { useI18n } from "../lib/i18n";
import type { AudioCue, Language } from "../types";

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

type Tone = "accent" | "success" | "warning" | "danger" | "neutral";

const toneMap: Record<Tone, string> = {
  accent: "bg-[color:var(--app-accent)]/10 text-[color:var(--app-accent)] border-[color:var(--app-accent)]/20",
  success: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20",
  warning: "bg-amber-500/12 text-amber-800 border-amber-500/20",
  danger: "bg-[color:var(--app-secondary)]/10 text-[color:var(--app-secondary)] border-[color:var(--app-secondary)]/20",
  neutral: "bg-black/5 text-[color:var(--app-text)]/70 border-[color:var(--app-line)]"
};

export function Surface({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={cn(
        "rounded-[28px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)]/90 p-4 shadow-[0_18px_60px_rgba(15,23,42,0.08)] backdrop-blur-sm",
        className
      )}
    >
      {children}
    </section>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        {eyebrow ? <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[color:var(--app-muted)]">{eyebrow}</p> : null}
        <h2 className="mt-1 text-[1.125rem] font-semibold leading-tight text-[color:var(--app-text)]">{title}</h2>
        {description ? <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function HeroCard({
  eyebrow,
  title,
  description,
  children,
  action
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Surface className="overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(31,122,90,0.16),transparent_46%),radial-gradient(circle_at_bottom_right,rgba(217,107,49,0.14),transparent_36%),color:var(--app-surface)]">
      <SectionHeading eyebrow={eyebrow} title={title} description={description} action={action} />
      {children ? <div className="mt-4">{children}</div> : null}
    </Surface>
  );
}

export function Button({
  children,
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" }) {
  const variants = {
    primary: "bg-[color:var(--app-accent)] text-[color:var(--app-accent-text)] shadow-[0_12px_30px_rgba(31,122,90,0.25)]",
    secondary: "border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] text-[color:var(--app-text)]",
    ghost: "text-[color:var(--app-text)]/75"
  };

  return (
    <button
      {...props}
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-[18px] px-4 text-sm font-semibold transition active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className
      )}
    >
      {children}
    </button>
  );
}

export function IconButton({
  icon: Icon,
  label,
  className,
  tone = "neutral",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { icon: LucideIcon; label: string; tone?: Tone }) {
  return (
    <button
      aria-label={label}
      title={label}
      {...props}
      className={cn("inline-flex h-11 w-11 items-center justify-center rounded-[16px] border", toneMap[tone], className)}
    >
      <Icon size={18} />
    </button>
  );
}

export function StatusChip({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) {
  return <span className={cn("inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold", toneMap[tone])}>{children}</span>;
}

export function FilterChip({
  active,
  children,
  onClick
}: {
  active?: boolean;
  children: ReactNode;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex h-10 items-center rounded-full border px-4 text-sm font-medium transition",
        active
          ? "border-transparent bg-[color:var(--app-text)] text-white shadow-[0_10px_20px_rgba(15,23,42,0.16)]"
          : "border-[color:var(--app-line)] bg-[color:var(--app-elevated)] text-[color:var(--app-text)]/72"
      )}
    >
      {children}
    </button>
  );
}

export function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = "accent"
}: {
  label: string;
  value: string | number;
  detail?: string;
  icon: LucideIcon;
  tone?: Tone;
}) {
  return (
    <Surface className="p-3.5">
      <div className="flex items-start gap-3">
        <div className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px] border", toneMap[tone])}>
          <Icon size={20} />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-[color:var(--app-muted)]">{label}</p>
          <p className="mt-1 text-2xl font-semibold leading-none text-[color:var(--app-text)]">{value}</p>
          {detail ? <p className="mt-1 text-xs text-[color:var(--app-muted)]">{detail}</p> : null}
        </div>
      </div>
    </Surface>
  );
}

export function ActionCard({
  title,
  description,
  meta,
  cta,
  icon: Icon,
  tone = "accent",
  onClick
}: {
  title: string;
  description: string;
  meta?: ReactNode;
  cta?: string;
  icon: LucideIcon;
  tone?: Tone;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-[26px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)] p-4 text-left shadow-[0_12px_32px_rgba(15,23,42,0.06)] transition hover:-translate-y-[1px] active:translate-y-0"
    >
      <div className="flex items-start gap-3">
        <div className={cn("mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px] border", toneMap[tone])}>
          <Icon size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-semibold text-[color:var(--app-text)]">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{description}</p>
          {meta ? <div className="mt-3 flex flex-wrap gap-2">{meta}</div> : null}
          {cta ? (
            <div className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-[color:var(--app-accent)]">
              {cta}
              <ChevronRight size={16} />
            </div>
          ) : null}
        </div>
      </div>
    </button>
  );
}

export function EmptyState({
  title,
  description,
  action
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Surface className="py-8 text-center">
      <p className="text-base font-semibold text-[color:var(--app-text)]">{title}</p>
      <p className="mx-auto mt-2 max-w-[24rem] text-sm leading-6 text-[color:var(--app-muted)]">{description}</p>
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </Surface>
  );
}

export function ErrorState({
  title,
  description,
  onRetry
}: {
  title?: string;
  description: string;
  onRetry?: () => void;
}) {
  const { ui } = useI18n();
  return (
    <Surface className="border-[color:var(--app-secondary)]/20 bg-[color:var(--app-secondary)]/5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[16px] border border-[color:var(--app-secondary)]/20 bg-[color:var(--app-secondary)]/10 text-[color:var(--app-secondary)]">
          <AlertTriangle size={18} />
        </div>
        <div className="min-w-0">
          <p className="font-semibold text-[color:var(--app-text)]">{title || ui("state.error_title", "Something went wrong")}</p>
          <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{description}</p>
          {onRetry ? (
            <Button className="mt-4" variant="secondary" onClick={onRetry}>
              {ui("action.retry", "Retry")}
            </Button>
          ) : null}
        </div>
      </div>
    </Surface>
  );
}

export function LoadingCard({ label }: { label?: string }) {
  const { ui } = useI18n();
  return (
    <Surface className="animate-pulse">
      <div className="flex items-center gap-3">
        <Loader2 size={18} className="animate-spin text-[color:var(--app-accent)]" />
        <span className="text-sm text-[color:var(--app-muted)]">{label || ui("state.loading", "Loading")}</span>
      </div>
    </Surface>
  );
}

function formatAudioTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const whole = Math.floor(seconds);
  const minutes = Math.floor(whole / 60);
  const remainder = whole % 60;
  return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

function cueTranscript(item?: AudioCue, language?: Language) {
  if (!item?.transcript) return "";
  const transcript = item.transcript as Record<string, string>;
  return transcript[language || "en"] || transcript.en || transcript.ru || transcript.uz || Object.values(transcript)[0] || "";
}

export function AudioPlayer({
  src,
  label,
  item,
  language = "en",
  completed = false
}: {
  src?: string;
  label?: string;
  item?: AudioCue;
  language?: Language;
  completed?: boolean;
}) {
  const { ui } = useI18n();
  const playbackUrl = item?.playback_url || src;
  const transcript = cueTranscript(item, language);
  const transcriptMode = item?.transcript_mode || "toggle";
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(item?.duration_seconds || 0);
  const [currentTime, setCurrentTime] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [transcriptOpen, setTranscriptOpen] = useState(transcriptMode === "always");
  const scrubId = useId();

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    function onPlay() {
      setIsPlaying(true);
      setLoading(false);
    }

    function onPause() {
      setIsPlaying(false);
    }

    function onLoadedMetadata() {
      const current = audioRef.current;
      setDuration(current?.duration || item?.duration_seconds || 0);
      setError("");
    }

    function onTimeUpdate() {
      const current = audioRef.current;
      setCurrentTime(current?.currentTime || 0);
    }

    function onWaiting() {
      setLoading(true);
    }

    function onCanPlay() {
      const current = audioRef.current;
      setLoading(false);
      setDuration(current?.duration || item?.duration_seconds || 0);
    }

    function onEnded() {
      setIsPlaying(false);
      setLoading(false);
    }

    function onError() {
      setIsPlaying(false);
      setLoading(false);
      setError(ui("audio.unavailable", "Audio is unavailable right now."));
    }

    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onPause);
    audio.addEventListener("loadedmetadata", onLoadedMetadata);
    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("waiting", onWaiting);
    audio.addEventListener("canplay", onCanPlay);
    audio.addEventListener("ended", onEnded);
    audio.addEventListener("error", onError);

    return () => {
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onPause);
      audio.removeEventListener("loadedmetadata", onLoadedMetadata);
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("waiting", onWaiting);
      audio.removeEventListener("canplay", onCanPlay);
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("error", onError);
    };
  }, [item?.duration_seconds]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.pause();
    audio.currentTime = 0;
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(item?.duration_seconds || 0);
    setError("");
    setLoading(false);
    setTranscriptOpen(transcriptMode === "always");
  }, [playbackUrl, item?.duration_seconds, transcriptMode]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.playbackRate = speed;
    }
  }, [speed]);

  if (!playbackUrl) return null;

  const transcriptLocked = transcriptMode === "after_complete" || transcriptMode === "after_completion";
  const transcriptVisible = transcriptMode === "always" || (transcriptOpen && (!transcriptLocked || completed));

  async function togglePlayback() {
    const audio = audioRef.current;
    if (!audio) return;
    setError("");
    if (audio.paused) {
      setLoading(true);
      try {
        await audio.play();
      } catch {
        setLoading(false);
        setError(ui("audio.blocked", "Playback was blocked."));
      }
      return;
    }
    audio.pause();
  }

  function replayFromStart() {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = 0;
    setCurrentTime(0);
    if (audio.paused) {
      void togglePlayback();
    }
  }

  return (
    <div className="rounded-[20px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-3">
      {label ? <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-[color:var(--app-muted)]">{label}</p> : null}
      <audio ref={audioRef} preload="none" className="hidden" src={playbackUrl}>
        {ui("audio.unsupported", "Your browser does not support audio playback.")}
      </audio>
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Button type="button" className="min-h-10 px-3" onClick={togglePlayback}>
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
            {isPlaying ? ui("audio.pause", "Pause") : ui("audio.play", "Play")}
          </Button>
          <Button type="button" variant="secondary" className="min-h-10 px-3" onClick={replayFromStart}>
            <RotateCcw size={16} />
            {ui("audio.replay", "Replay")}
          </Button>
          <select
            className="h-10 rounded-[16px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)] px-3 text-sm"
            value={speed}
            onChange={(event) => {
              const next = Number(event.target.value);
              setSpeed(next);
              if (audioRef.current) {
                audioRef.current.playbackRate = next;
              }
            }}
          >
            {[0.75, 1, 1.25, 1.5].map((option) => (
              <option key={option} value={option}>
                {option}x
              </option>
            ))}
          </select>
          {loading ? <span className="text-xs text-[color:var(--app-muted)]">{ui("audio.loading", "Loading...")}</span> : null}
        </div>
        <div className="space-y-1">
          <label htmlFor={scrubId} className="sr-only">
            {ui("audio.seek", "Seek audio")}
          </label>
          <input
            id={scrubId}
            type="range"
            min={0}
            max={Math.max(duration, 0)}
            step={0.1}
            value={Math.min(currentTime, Math.max(duration, 0))}
            onChange={(event) => {
              const next = Number(event.target.value);
              setCurrentTime(next);
              if (audioRef.current) {
                audioRef.current.currentTime = next;
              }
            }}
            className="w-full accent-[color:var(--app-accent)]"
          />
          <div className="flex items-center justify-between text-xs text-[color:var(--app-muted)]">
            <span>{formatAudioTime(currentTime)}</span>
            <span>{formatAudioTime(duration)}</span>
          </div>
        </div>
        {error ? <p className="text-sm text-[color:var(--app-secondary)]">{error}</p> : null}
        {transcript ? (
          <div className="rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)] p-3">
            {transcriptMode !== "always" ? (
              <button
                type="button"
                onClick={() => setTranscriptOpen((current) => !current)}
                className="text-sm font-semibold text-[color:var(--app-accent)]"
                disabled={transcriptLocked && !completed}
              >
                {transcriptVisible
                  ? ui("audio.transcript.hide", "Hide transcript")
                  : transcriptLocked && !completed
                    ? ui("audio.transcript.locked", "Transcript unlocks after completion")
                    : ui("audio.transcript.reveal", "Reveal transcript")}
              </button>
            ) : null}
            {transcriptVisible ? <p className="mt-2 text-sm leading-6 text-[color:var(--app-muted)]">{transcript}</p> : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-[color:var(--app-text)]">{label}</span>
        {hint ? <span className="text-xs text-[color:var(--app-muted)]">{hint}</span> : null}
      </div>
      <div className="mt-2">{children}</div>
    </label>
  );
}

const fieldBase =
  "h-12 w-full rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] px-4 text-sm text-[color:var(--app-text)] outline-none transition placeholder:text-[color:var(--app-muted)] focus:border-[color:var(--app-accent)]";

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn(fieldBase, props.className)} />;
}

export function SelectInput(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cn(fieldBase, props.className)} />;
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cn("min-h-28 w-full rounded-[18px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4 text-sm text-[color:var(--app-text)] outline-none focus:border-[color:var(--app-accent)]", props.className)} />;
}

export function ToggleRow({
  title,
  description,
  checked,
  onChange
}: {
  title: string;
  description?: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-4 rounded-[22px] border border-[color:var(--app-line)] bg-[color:var(--app-elevated)] p-4">
      <div className="min-w-0">
        <p className="text-sm font-semibold text-[color:var(--app-text)]">{title}</p>
        {description ? <p className="mt-1 text-sm leading-6 text-[color:var(--app-muted)]">{description}</p> : null}
      </div>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={cn(
          "relative h-8 w-14 shrink-0 rounded-full transition",
          checked ? "bg-[color:var(--app-accent)]" : "bg-black/10"
        )}
      >
        <span
          className={cn(
            "absolute top-1 h-6 w-6 rounded-full bg-white shadow transition",
            checked ? "left-7" : "left-1"
          )}
        />
      </button>
    </label>
  );
}
