type JsonValue = Record<string, unknown>;

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function loadLessonResume(userId: string, lessonId: number): number {
  return readJson<number>(`miniapp:lesson-resume:${userId}:${lessonId}`, 0);
}

export function saveLessonResume(userId: string, lessonId: number, stepIndex: number) {
  writeJson(`miniapp:lesson-resume:${userId}:${lessonId}`, stepIndex);
}

export function clearLessonResume(userId: string, lessonId: number) {
  localStorage.removeItem(`miniapp:lesson-resume:${userId}:${lessonId}`);
}

export function loadWordFlags(userId: string): Record<string, { bookmarked?: boolean; difficult?: boolean }> {
  return readJson<Record<string, { bookmarked?: boolean; difficult?: boolean }>>(`miniapp:word-flags:${userId}`, {});
}

export function saveWordFlags(userId: string, value: Record<string, { bookmarked?: boolean; difficult?: boolean }>) {
  writeJson(`miniapp:word-flags:${userId}`, value);
}

export function loadDismissedPrompts(userId: string): JsonValue {
  return readJson<JsonValue>(`miniapp:dismissed:${userId}`, {});
}

export function saveDismissedPrompts(userId: string, value: JsonValue) {
  writeJson(`miniapp:dismissed:${userId}`, value);
}

export function clearPersonalization(userId: string) {
  const prefixes = [
    `miniapp:word-flags:${userId}`,
    `miniapp:dismissed:${userId}`
  ];
  prefixes.forEach((key) => localStorage.removeItem(key));
}
