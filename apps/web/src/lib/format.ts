import type { Language, Localized } from "../types";

const topicLabels: Record<string, string> = {
  daily_life: "Daily life",
  food: "Food",
  shopping: "Shopping",
  transport: "Transport",
  study: "Study",
  work: "Work",
  health: "Health",
  grammar: "Grammar",
  vocabulary: "Vocabulary",
  general: "General"
};

export function t(text: Partial<Localized> | undefined, language: Language, fallback = ""): string {
  return text?.[language] || text?.en || fallback;
}

export function humanize(value: string | null | undefined): string {
  if (!value) return "";
  return value.replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

export function topicLabel(value: string | null | undefined): string {
  if (!value) return "General";
  return topicLabels[value] || humanize(value);
}

export function compactDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date);
}

export function compactTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
}

export function sentenceList(items: string[], empty = "Nothing here yet."): string {
  return items.filter(Boolean).join(" • ") || empty;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
