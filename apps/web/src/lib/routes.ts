export type ReviewMode = "due" | "mistakes" | "vocab" | "grammar" | "mixed" | "listening";

export type AppRoute =
  | { screen: "home" }
  | { screen: "lesson"; lessonId?: number }
  | { screen: "review"; mode?: ReviewMode; size?: number; shortcut?: "two-minute" }
  | { screen: "scenarios"; scenario?: string; topic?: string }
  | { screen: "vocab"; vocabId?: number; topic?: string; q?: string }
  | { screen: "grammar"; grammarId?: number; topic?: string; q?: string }
  | { screen: "progress" }
  | { screen: "settings" }
  | { screen: "admin" };

const defaultRoute: AppRoute = { screen: "home" };

function parsePositiveInt(value: string | null): number | undefined {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

function parseRouteSegments(hash: string): AppRoute | null {
  const trimmed = hash.replace(/^#/, "").trim();
  if (!trimmed) return null;
  const [rawPath = "/", rawQuery = ""] = trimmed.split("?");
  const search = new URLSearchParams(rawQuery);
  const segments = rawPath.split("/").filter(Boolean);
  const [screen = "home", idOrSlug] = segments;

  if (screen === "home") return { screen: "home" };
  if (screen === "lesson") return { screen: "lesson", lessonId: parsePositiveInt(idOrSlug) };
  if (screen === "review") {
    const mode = search.get("mode") as ReviewMode | null;
    const size = parsePositiveInt(search.get("size"));
    const shortcut = search.get("shortcut") === "two-minute" ? "two-minute" : undefined;
    return { screen: "review", mode: mode || "due", size, shortcut };
  }
  if (screen === "scenarios") return { screen: "scenarios", scenario: idOrSlug, topic: search.get("topic") || undefined };
  if (screen === "vocab") {
    return { screen: "vocab", vocabId: parsePositiveInt(idOrSlug), topic: search.get("topic") || undefined, q: search.get("q") || undefined };
  }
  if (screen === "grammar") {
    return { screen: "grammar", grammarId: parsePositiveInt(idOrSlug), topic: search.get("topic") || undefined, q: search.get("q") || undefined };
  }
  if (screen === "progress") return { screen: "progress" };
  if (screen === "settings") return { screen: "settings" };
  if (screen === "admin") return { screen: "admin" };
  return null;
}

function parseStartParam(startParam?: string | null): AppRoute | null {
  if (!startParam) return null;
  if (startParam.startsWith("lesson_")) return { screen: "lesson", lessonId: parsePositiveInt(startParam.split("_", 2)[1] || null) };
  if (startParam.startsWith("scenario_")) return { screen: "scenarios", scenario: startParam.slice("scenario_".length) };
  if (startParam.startsWith("grammar_")) return { screen: "grammar", grammarId: parsePositiveInt(startParam.split("_", 2)[1] || null) };
  if (startParam.startsWith("word_")) return { screen: "vocab", vocabId: parsePositiveInt(startParam.split("_", 2)[1] || null) };
  if (startParam === "review" || startParam === "review_due") return { screen: "review", mode: "due" };
  if (startParam === "review_mistakes") return { screen: "review", mode: "mistakes" };
  if (startParam === "quiz" || startParam === "quiz_mixed") return { screen: "review", mode: "mixed", shortcut: "two-minute", size: 5 };
  if (startParam === "settings" || startParam === "screen_settings") return { screen: "settings" };
  if (startParam === "dialogue" || startParam === "screen_scenarios") return { screen: "scenarios" };
  if (startParam === "progress" || startParam === "screen_progress") return { screen: "progress" };
  if (startParam === "grammar" || startParam === "screen_grammar") return { screen: "grammar" };
  if (startParam === "vocab" || startParam === "words" || startParam === "screen_vocab") return { screen: "vocab" };
  if (startParam === "library" || startParam === "screen_library") return { screen: "vocab" };
  if (startParam === "admin" || startParam === "screen_admin") return { screen: "admin" };
  if (startParam === "screen_home" || startParam === "home") return { screen: "home" };
  return null;
}

function parseLegacySearch(searchValue: string): AppRoute | null {
  const search = new URLSearchParams(searchValue);
  const screen = search.get("screen");
  const lessonId = parsePositiveInt(search.get("lesson"));
  const scenario = search.get("scenario") || undefined;
  const grammarId = parsePositiveInt(search.get("grammar"));
  const vocabId = parsePositiveInt(search.get("word"));
  const tab = search.get("tab");

  if (lessonId) return { screen: "lesson", lessonId };
  if (scenario) return { screen: "scenarios", scenario };
  if (grammarId) return { screen: "grammar", grammarId };
  if (vocabId) return { screen: "vocab", vocabId };

  if (screen === "review") return { screen: "review", mode: "due" };
  if (screen === "scenarios") return { screen: "scenarios" };
  if (screen === "settings") return { screen: "settings" };
  if (screen === "admin") return { screen: "admin" };
  if (screen === "library") {
    if (tab === "grammar") return { screen: "grammar" };
    return { screen: "vocab" };
  }
  if (screen === "learn") return { screen: "lesson" };
  if (screen === "progress") return { screen: "progress" };
  return null;
}

export function getInitialRoute(startParam?: string | null): AppRoute {
  return parseRouteSegments(window.location.hash) || parseStartParam(startParam) || parseLegacySearch(window.location.search) || defaultRoute;
}

export function serializeRoute(route: AppRoute): string {
  const params = new URLSearchParams();
  let path = "/home";

  if (route.screen === "lesson") {
    path = route.lessonId ? `/lesson/${route.lessonId}` : "/lesson";
  }

  if (route.screen === "review") {
    path = "/review";
    if (route.mode && route.mode !== "due") params.set("mode", route.mode);
    if (route.size) params.set("size", String(route.size));
    if (route.shortcut) params.set("shortcut", route.shortcut);
  }

  if (route.screen === "scenarios") {
    path = route.scenario ? `/scenarios/${encodeURIComponent(route.scenario)}` : "/scenarios";
    if (route.topic) params.set("topic", route.topic);
  }

  if (route.screen === "vocab") {
    path = route.vocabId ? `/vocab/${route.vocabId}` : "/vocab";
    if (route.topic) params.set("topic", route.topic);
    if (route.q) params.set("q", route.q);
  }

  if (route.screen === "grammar") {
    path = route.grammarId ? `/grammar/${route.grammarId}` : "/grammar";
    if (route.topic) params.set("topic", route.topic);
    if (route.q) params.set("q", route.q);
  }

  if (route.screen === "progress") path = "/progress";
  if (route.screen === "settings") path = "/settings";
  if (route.screen === "admin") path = "/admin";

  const query = params.toString();
  return `#${path}${query ? `?${query}` : ""}`;
}

export function routeTitle(route: AppRoute): string {
  if (route.screen === "lesson") return "Lesson";
  if (route.screen === "review") return "Review";
  if (route.screen === "scenarios") return "Scenarios";
  if (route.screen === "vocab") return "Vocabulary";
  if (route.screen === "grammar") return "Grammar";
  if (route.screen === "progress") return "Progress";
  if (route.screen === "settings") return "Settings";
  if (route.screen === "admin") return "Admin";
  return "Home";
}

export function buildStartParam(route: AppRoute): string {
  if (route.screen === "lesson" && route.lessonId) return `lesson_${route.lessonId}`;
  if (route.screen === "scenarios" && route.scenario) return `scenario_${route.scenario}`;
  if (route.screen === "grammar" && route.grammarId) return `grammar_${route.grammarId}`;
  if (route.screen === "vocab" && route.vocabId) return `word_${route.vocabId}`;
  if (route.screen === "review" && route.mode === "mistakes") return "review_mistakes";
  if (route.screen === "review") return "review_due";
  if (route.screen === "progress") return "progress";
  if (route.screen === "settings") return "settings";
  if (route.screen === "grammar") return "grammar";
  if (route.screen === "vocab") return "vocab";
  if (route.screen === "scenarios") return "dialogue";
  if (route.screen === "admin") return "admin";
  return "screen_home";
}

export function shouldUseFullscreen(route: AppRoute): boolean {
  return route.screen === "lesson" || route.screen === "review" || route.screen === "scenarios";
}

export function navSection(route: AppRoute): "home" | "review" | "library" | "scenarios" | "progress" {
  if (route.screen === "review") return "review";
  if (route.screen === "scenarios") return "scenarios";
  if (route.screen === "vocab" || route.screen === "grammar") return "library";
  if (route.screen === "progress") return "progress";
  return "home";
}
