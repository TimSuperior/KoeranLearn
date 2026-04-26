import { useEffect, useMemo, useState } from "react";
import { Shell } from "./components/Shell";
import { api } from "./lib/api";
import { track } from "./lib/analytics";
import { t } from "./lib/format";
import { getInitialRoute, routeTitle, serializeRoute, shouldUseFullscreen, type AppRoute } from "./lib/routes";
import { bindTelegramChrome, getTelegramInitData, getTelegramStartParam, initTelegramShell } from "./lib/telegram";
import { AdminScreen } from "./screens/AdminScreen";
import { GrammarScreen } from "./screens/GrammarScreen";
import { HomeScreen } from "./screens/HomeScreen";
import { LearnScreen } from "./screens/LearnScreen";
import { OnboardingScreen } from "./screens/OnboardingScreen";
import { ProgressScreen } from "./screens/ProgressScreen";
import { ReviewScreen } from "./screens/ReviewScreen";
import { ScenariosScreen } from "./screens/ScenariosScreen";
import { SettingsScreen } from "./screens/SettingsScreen";
import { VocabularyScreen } from "./screens/VocabularyScreen";
import type { AuthUser } from "./types";

function screenSubtitle(route: AppRoute): string {
  if (route.screen === "lesson") return "Step-based guided lesson";
  if (route.screen === "review") return "Review center";
  if (route.screen === "scenarios") return "Real-life dialogue practice";
  if (route.screen === "vocab") return "Word bank and review cues";
  if (route.screen === "grammar") return "Patterns, notes, and mistakes";
  if (route.screen === "progress") return "Weekly rhythm and weak areas";
  if (route.screen === "settings") return "Telegram-native preferences";
  if (route.screen === "admin") return "Content operations";
  return "Serious mobile Korean learning";
}

function hasBack(route: AppRoute): boolean {
  return route.screen === "lesson" || route.screen === "settings" || Boolean(route.screen === "scenarios" && route.scenario) || Boolean(route.screen === "vocab" && route.vocabId) || Boolean(route.screen === "grammar" && route.grammarId) || route.screen === "admin";
}

function getBackRoute(route: AppRoute): AppRoute {
  if (route.screen === "scenarios" && route.scenario) return { screen: "scenarios" };
  if (route.screen === "vocab" && route.vocabId) return { screen: "vocab", topic: route.topic, q: route.q };
  if (route.screen === "grammar" && route.grammarId) return { screen: "grammar", topic: route.topic, q: route.q };
  return { screen: "home" };
}

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [route, setRoute] = useState<AppRoute>(() => getInitialRoute(getTelegramStartParam()));
  const [error, setError] = useState("");

  useEffect(() => {
    const cleanupTelegram = initTelegramShell();
    const initialRoute = getInitialRoute(getTelegramStartParam());
    setRoute(initialRoute);
    if (window.location.hash !== serializeRoute(initialRoute)) {
      history.replaceState(null, "", `${window.location.pathname}${window.location.search}${serializeRoute(initialRoute)}`);
    }

    api.auth(getTelegramInitData()).then(setUser).catch((err) => setError(err instanceof Error ? err.message : "Could not initialize Telegram session."));

    const syncFromUrl = () => setRoute(getInitialRoute(getTelegramStartParam()));
    window.addEventListener("hashchange", syncFromUrl);
    window.addEventListener("popstate", syncFromUrl);

    return () => {
      cleanupTelegram?.();
      window.removeEventListener("hashchange", syncFromUrl);
      window.removeEventListener("popstate", syncFromUrl);
    };
  }, []);

  function navigate(nextRoute: AppRoute, options?: { replace?: boolean }) {
    const hash = serializeRoute(nextRoute);
    const url = `${window.location.pathname}${window.location.search}${hash}`;
    if (options?.replace) {
      history.replaceState(null, "", url);
    } else {
      history.pushState(null, "", url);
    }
    setRoute(nextRoute);
  }

  useEffect(() => {
    if (!user) return;
    track("screen_view", {
      telegram_id: user.telegram_id,
      audience_language: user.interface_language,
      properties: { screen: route.screen }
    });

    return bindTelegramChrome({
      route,
      fullscreen: shouldUseFullscreen(route),
      showBack: hasBack(route),
      onBack: () => navigate(getBackRoute(route)),
      showSettings: route.screen !== "settings",
      onSettings: () => navigate({ screen: "settings" }),
      protectFromAccidentalClose: route.screen === "lesson" || route.screen === "review"
    });
  }, [route, user]);

  const title = useMemo(() => {
    if (route.screen === "lesson") return "Lesson player";
    if (route.screen === "review") return route.mode === "mistakes" ? "Mistakes review" : route.mode === "mixed" ? "Mixed quick review" : routeTitle(route);
    return routeTitle(route);
  }, [route]);

  if (error) {
    return (
      <main className="mx-auto max-w-xl px-4 py-8">
        <div className="rounded-[24px] border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <div className="rounded-[24px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)] px-5 py-4 text-sm text-[color:var(--app-muted)]">
          Loading Telegram session...
        </div>
      </main>
    );
  }

  if (!user.is_onboarded) {
    return <OnboardingScreen user={user} onDone={setUser} />;
  }

  return (
    <Shell route={route} title={title} subtitle={screenSubtitle(route)} onNavigate={navigate}>
      {route.screen === "home" ? <HomeScreen user={user} onNavigate={navigate} /> : null}
      {route.screen === "lesson" ? <LearnScreen user={user} lessonId={route.lessonId} onNavigate={navigate} /> : null}
      {route.screen === "review" ? <ReviewScreen user={user} mode={route.mode} size={route.size} onNavigate={navigate} /> : null}
      {route.screen === "scenarios" ? <ScenariosScreen user={user} scenarioSlug={route.scenario} initialTopic={route.topic} onNavigate={navigate} /> : null}
      {route.screen === "vocab" ? <VocabularyScreen user={user} vocabId={route.vocabId} topic={route.topic} q={route.q} onNavigate={navigate} /> : null}
      {route.screen === "grammar" ? <GrammarScreen user={user} grammarId={route.grammarId} topic={route.topic} q={route.q} onNavigate={navigate} /> : null}
      {route.screen === "progress" ? <ProgressScreen user={user} onNavigate={navigate} /> : null}
      {route.screen === "settings" ? <SettingsScreen user={user} /> : null}
      {route.screen === "admin" ? <AdminScreen /> : null}
    </Shell>
  );
}
