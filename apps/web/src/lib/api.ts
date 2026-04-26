import type {
  AuthUser,
  GrammarPoint,
  Lesson,
  Path,
  Progress,
  QuizSession,
  ReviewItem,
  Scenario,
  ScenarioDetail,
  StudyPlan,
  UserSettings,
  Vocabulary
} from "../types";
import type {
  AdminEntityKey,
  AdminFilters,
  AdminListResponse,
  AdminRow,
  DashboardSummary,
  ExportResponse,
  ImportResult,
  PreviewResponse,
  RelationOptionsMap,
  ValidationResult
} from "../admin/types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
let accessToken = localStorage.getItem("accessToken") || "";

function setAccessToken(token: string) {
  accessToken = token;
  localStorage.setItem("accessToken", token);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(init?.headers || {})
    }
  });
  if (response.status === 401 && !path.startsWith("/api/auth/")) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request<T>(path, init);
    }
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

async function refreshAccessToken(): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!response.ok) return false;
  const token = await response.json() as { access_token: string };
  setAccessToken(token.access_token);
  return true;
}

export const api = {
  setAccessToken,
  async auth(initData: string) {
    const user = await request<AuthUser>("/api/auth/telegram-webapp", {
      method: "POST",
      body: JSON.stringify({ init_data: initData })
    });
    setAccessToken(user.access_token);
    return user;
  },
  completeOnboarding(telegramId: string, payload: Record<string, unknown>) {
    return request<AuthUser>("/api/onboarding/complete", {
      method: "POST",
      body: JSON.stringify({ telegram_id: telegramId, ...payload })
    });
  },
  progress(telegramId: string) {
    return request<Progress>(`/api/progress/${telegramId}`);
  },
  paths() {
    return request<Path[]>("/api/paths");
  },
  switchPath(pathId: number) {
    return request(`/api/paths/${pathId}/switch`, { method: "POST" });
  },
  continueLesson(telegramId: string) {
    return request<Lesson | null>(`/api/lessons/continue/${telegramId}`);
  },
  startLesson(telegramId: string, lessonId: number) {
    return request<Lesson>(`/api/lessons/${lessonId}/start`, {
      method: "POST",
      body: JSON.stringify({ telegram_id: telegramId })
    });
  },
  submitExercise(telegramId: string, lessonId: number | null | undefined, exerciseId: number, answer: unknown) {
    return request<{ is_correct: boolean; expected: unknown; explanation: Record<string, string>; lesson_completed: boolean; xp_awarded: number }>(
      `/api/exercises/${exerciseId}/submit`,
      {
        method: "POST",
        body: JSON.stringify({ telegram_id: telegramId, lesson_id: lessonId, answer })
      }
    );
  },
  reviewQueue(telegramId: string, mistakesOnly = false, limit = 20) {
    return request<ReviewItem[]>(`/api/review/queue/${telegramId}?mistakes_only=${mistakesOnly ? "true" : "false"}&limit=${limit}`);
  },
  submitReview(telegramId: string, reviewItemId: number, isCorrect: boolean, quality: number) {
    return request(`/api/review/${reviewItemId}/submit`, {
      method: "POST",
      body: JSON.stringify({ telegram_id: telegramId, is_correct: isCorrect, quality, answer: {} })
    });
  },
  grammar() {
    return request<GrammarPoint[]>("/api/grammar");
  },
  grammarDetail(grammarId: number) {
    return request<GrammarPoint>(`/api/grammar/${grammarId}`);
  },
  vocab() {
    return request<Vocabulary[]>("/api/vocab");
  },
  vocabDetail(vocabId: number) {
    return request<Vocabulary>(`/api/vocab/${vocabId}`);
  },
  correctWriting(telegramId: string, text: string, targetRegister: string) {
    return request<{ corrected_text: string; natural_text: string; feedback: Record<string, unknown>; provider: string; remaining_daily_quota: number }>(
      "/api/writing/correct",
      {
        method: "POST",
        body: JSON.stringify({ telegram_id: telegramId, text, target_register: targetRegister, include_translation: true })
      }
    );
  },
  premiumCatalog() {
    return request<Array<{ id: number; title: Record<string, string>; description: Record<string, string>; price_minor: number; currency: string }>>(
      "/api/premium/catalog"
    );
  },
  premiumAccess(telegramId: string) {
    return request<{ is_premium: boolean; limits: Record<string, number> }>(`/api/premium/access/${telegramId}`);
  },
  reminders(telegramId: string) {
    return request<{ enabled: boolean; reminder_time: string; timezone: string; quiet_hours: Record<string, string> }>(`/api/reminders/${telegramId}`);
  },
  updateReminders(telegramId: string, payload: Record<string, unknown>) {
    return request(`/api/reminders/${telegramId}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    });
  },
  settings() {
    return request<UserSettings>("/api/settings");
  },
  updateSettings(payload: Record<string, unknown>) {
    return request("/api/settings", {
      method: "PUT",
      body: JSON.stringify(payload)
    });
  },
  plan() {
    return request<StudyPlan>("/api/plan/current");
  },
  streak() {
    return request<{ streak_count: number; xp: number; due_reviews: number; next_milestone: number; weekly_activity: Array<{ day_offset: number; active: boolean }> }>(
      "/api/streak"
    );
  },
  quizStart(payload: { topic?: string; limit?: number; mistakes_only?: boolean }) {
    return request<QuizSession>("/api/quiz/start", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  scenarios(params: Record<string, string> = {}) {
    const search = new URLSearchParams(params).toString();
    return request<Scenario[]>(`/api/scenarios${search ? `?${search}` : ""}`);
  },
  scenarioDetail(idOrSlug: string | number) {
    return request<ScenarioDetail>(`/api/scenarios/${idOrSlug}`);
  },
  startScenario(idOrSlug: string | number) {
    return request<{ scenario: ScenarioDetail; progress: Record<string, unknown> }>(`/api/scenarios/${idOrSlug}/start`, { method: "POST" });
  },
  completeScenario(idOrSlug: string | number, comprehensionScore = 1) {
    return request(`/api/scenarios/${idOrSlug}/complete`, {
      method: "POST",
      body: JSON.stringify({ comprehension_score: comprehensionScore })
    });
  },
  favoriteScenario(idOrSlug: string | number, favorite: boolean) {
    return request(`/api/scenarios/${idOrSlug}/favorite`, {
      method: "POST",
      body: JSON.stringify({ favorite })
    });
  },
  trackEvent(payload: { event_name: string; telegram_id?: string; audience_language?: string; properties?: Record<string, unknown> }) {
    return request<{ id: number; event_name: string }>("/api/analytics/events", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  adminLogin(email: string, password: string) {
    return request<{ access_token: string; expires_in: number }>("/api/auth/admin/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    }).then((token) => {
      localStorage.setItem("adminAccessToken", token.access_token);
      return token;
    });
  },
  async adminUploadMedia(token: string, file: File, folder = "audio") {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("folder", folder);
    const response = await fetch(`${API_BASE_URL}/api/admin/media/upload`, {
      method: "POST",
      credentials: "include",
      headers: { Authorization: `Bearer ${token}` },
      body: formData
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || response.statusText);
    }
    return response.json() as Promise<{ url: string; filename: string; content_type: string }>;
  },
  adminUploadAudioAsset(
    token: string,
    file: File,
    options: { audioAssetId?: number; attachmentRole?: string } = {},
    onProgress?: (percent: number) => void
  ) {
    return new Promise<AdminRow>((resolve, reject) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("attachment_role", options.attachmentRole || "general");
      if (options.audioAssetId) {
        formData.append("audio_asset_id", String(options.audioAssetId));
      }
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE_URL}/api/admin/content/audio-assets/upload`);
      xhr.withCredentials = true;
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };
      xhr.onerror = () => reject(new Error("Upload failed."));
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText) as AdminRow);
          return;
        }
        reject(new Error(xhr.responseText || xhr.statusText || "Upload failed."));
      };
      xhr.send(formData);
    });
  },
  adminOverview(token: string) {
    return request<Record<string, number>>("/api/admin/overview", {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminLessons(token: string) {
    return request<Lesson[]>("/api/admin/lessons", {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminUpdateLesson(token: string, lessonId: number, payload: Record<string, unknown>) {
    return request<Lesson>(`/api/admin/lessons/${lessonId}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
  },
  adminContent(token: string, entity: string) {
    return request<{ items: Array<Record<string, unknown>>; total: number }>(`/api/admin/content/${entity}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminUpdateContent(token: string, entity: string, id: number, data: Record<string, unknown>) {
    const payload = ("data" in data || "relation_ids" in data || "children" in data) ? data : { data };
    return request<AdminRow>(`/api/admin/content/${entity}/${id}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
  },
  adminDuplicateContent(token: string, entity: string, id: number) {
    return request<AdminRow>(`/api/admin/content/${entity}/${id}/duplicate`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminDashboard(token: string) {
    return request<DashboardSummary>("/api/admin/content/dashboard", {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminContentOptions(token: string) {
    return request<{ options: RelationOptionsMap }>("/api/admin/content/options", {
      headers: { Authorization: `Bearer ${token}` }
    }).then((response) => response.options);
  },
  adminContentList(token: string, entity: AdminEntityKey, filters: Partial<AdminFilters>) {
    const search = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) search.set(key, String(value));
    });
    return request<AdminListResponse>(`/api/admin/content/${entity}?${search.toString()}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminContentDetail(token: string, entity: AdminEntityKey, id: number) {
    return request<AdminRow>(`/api/admin/content/${entity}/${id}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminCreateContent(token: string, entity: AdminEntityKey, payload: Record<string, unknown>) {
    return request<AdminRow>(`/api/admin/content/${entity}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
  },
  adminDeleteContent(token: string, entity: AdminEntityKey, id: number) {
    return request<{ ok: boolean }>(`/api/admin/content/${entity}/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminPublishContent(token: string, entity: AdminEntityKey, id: number) {
    return request<AdminRow>(`/api/admin/content/${entity}/${id}/publish`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminUnpublishContent(token: string, entity: AdminEntityKey, id: number) {
    return request<AdminRow>(`/api/admin/content/${entity}/${id}/unpublish`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminValidateContent(token: string, entity: AdminEntityKey, payload: Record<string, unknown>) {
    return request<ValidationResult>(`/api/admin/content/validation/${entity}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
  },
  adminValidateSavedContent(token: string, entity: AdminEntityKey, id: number) {
    return request<ValidationResult>(`/api/admin/content/validation/${entity}/${id}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminPreviewContent(token: string, entity: AdminEntityKey, id: number, viewerAccess: "free" | "premium") {
    return request<PreviewResponse>(`/api/admin/content/preview/${entity}/${id}?viewer_access=${viewerAccess}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminBulkContentState(token: string, payload: { entity: AdminEntityKey; ids: number[]; status?: string; access_state?: string }) {
    return request<{ updated: number }>("/api/admin/content/status/bulk", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
  },
  adminReorderContent(token: string, entity: AdminEntityKey, order: number[]) {
    return request<{ ok: boolean }>(`/api/admin/content/${entity}/reorder`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ order })
    });
  },
  adminExportContent(token: string, entity: AdminEntityKey, format: "json" | "csv") {
    return request<ExportResponse>(`/api/admin/content/export/${entity}?format=${format}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminTemplateContent(token: string, entity: AdminEntityKey, format: "json" | "csv") {
    return request<ExportResponse>(`/api/admin/content/templates/${entity}?format=${format}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  },
  adminImportContent(token: string, entity: AdminEntityKey, payload: { format: "json" | "csv"; content: string; dry_run: boolean; conflict_strategy: string }) {
    return request<ImportResult>(`/api/admin/content/import/${entity}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
  }
};
