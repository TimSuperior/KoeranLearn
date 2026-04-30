import { useEffect, useMemo, useState } from "react";
import { Shell } from "./components/Shell";
import { api } from "./lib/api";
import { track } from "./lib/analytics";
import { getInitialRoute, routeTitle, serializeRoute, shouldUseFullscreen, type AppRoute } from "./lib/routes";
import { I18nProvider, useI18n } from "./lib/i18n";
import { bindTelegramChrome, getTelegramInitData, getTelegramLanguage, getTelegramStartParam, initTelegramShell } from "./lib/telegram";
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
import type { AuthUser, Language } from "./types";

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
  const bootstrapLanguage = useMemo<Language>(() => getTelegramLanguage(), []);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [route, setRoute] = useState<AppRoute>(() => getInitialRoute(getTelegramStartParam()));
  const [initFailed, setInitFailed] = useState(false);

  useEffect(() => {
    const cleanupTelegram = initTelegramShell();
    const initialRoute = getInitialRoute(getTelegramStartParam());
    setRoute(initialRoute);
    if (window.location.hash !== serializeRoute(initialRoute)) {
      history.replaceState(null, "", `${window.location.pathname}${window.location.search}${serializeRoute(initialRoute)}`);
    }

    api.auth(getTelegramInitData()).then(setUser).catch(() => setInitFailed(true));

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

  const i18nUser = user || buildBootstrapUser(bootstrapLanguage);

  return (
    <I18nProvider user={i18nUser}>
      <AppFrame user={user} route={route} onNavigate={navigate} onUserChange={setUser} initFailed={initFailed} />
    </I18nProvider>
  );
}

function buildBootstrapUser(language: Language): AuthUser {
  return {
    telegram_id: "",
    interface_language: language,
    explanation_language: language,
    is_onboarded: false,
    is_premium: false,
    access_token: "",
    token_type: "bearer",
    expires_in: 0,
  };
}

function AppFrame({
  user,
  route,
  onNavigate,
  onUserChange,
  initFailed,
}: {
  user: AuthUser | null;
  route: AppRoute;
  onNavigate: (route: AppRoute, options?: { replace?: boolean }) => void;
  onUserChange: (user: AuthUser) => void;
  initFailed: boolean;
}) {
  const { ui } = useI18n();

  if (initFailed) {
    return (
      <main className="mx-auto max-w-xl px-4 py-8">
        <div className="rounded-[24px] border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {ui("error.init_session", "Could not initialize Telegram session.")}
        </div>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <div className="rounded-[24px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)] px-5 py-4 text-sm text-[color:var(--app-muted)]">
          {ui("loading.session", "Loading Telegram session...")}
        </div>
      </main>
    );
  }

  return <LocalizedApp user={user} route={route} onNavigate={onNavigate} onUserChange={onUserChange} />;
}

function LocalizedApp({
  user,
  route,
  onNavigate,
  onUserChange,
}: {
  user: AuthUser;
  route: AppRoute;
  onNavigate: (route: AppRoute, options?: { replace?: boolean }) => void;
  onUserChange: (user: AuthUser) => void;
}) {
  const { ui } = useI18n();

  const subtitle =
    route.screen === "lesson" ? ui("subtitle.lesson", "Step-based guided lesson")
      : route.screen === "review" ? ui("subtitle.review", "Review center")
      : route.screen === "scenarios" ? ui("subtitle.scenarios", "Real-life dialogue practice")
      : route.screen === "vocab" ? ui("subtitle.vocab", "Word bank and review cues")
      : route.screen === "grammar" ? ui("subtitle.grammar", "Patterns, notes, and mistakes")
      : route.screen === "progress" ? ui("subtitle.progress", "Weekly rhythm and weak areas")
      : route.screen === "settings" ? ui("subtitle.settings", "Telegram-native preferences")
      : route.screen === "admin" ? ui("subtitle.admin", "Content operations")
      : ui("subtitle.home", "Serious mobile Korean learning");

  const title = useMemo(() => {
    if (route.screen === "lesson") return ui("route.lesson", "Lesson");
    if (route.screen === "review") return ui("route.review", "Review");
    if (route.screen === "scenarios") return ui("route.scenarios", "Scenarios");
    if (route.screen === "vocab") return ui("route.vocab", "Vocabulary");
    if (route.screen === "grammar") return ui("route.grammar", "Grammar");
    if (route.screen === "progress") return ui("route.progress", "Progress");
    if (route.screen === "settings") return ui("route.settings", "Settings");
    if (route.screen === "admin") return ui("route.admin", "Admin");
    return ui("route.home", routeTitle(route));
  }, [route, ui]);

  if (!user.is_onboarded) {
    return <OnboardingScreen user={user} onDone={onUserChange} />;
  }

  return (
    <Shell route={route} title={title} subtitle={subtitle} onNavigate={onNavigate}>
      {route.screen === "home" ? <HomeScreen user={user} onNavigate={onNavigate} /> : null}
      {route.screen === "lesson" ? <LearnScreen user={user} lessonId={route.lessonId} onNavigate={onNavigate} /> : null}
      {route.screen === "review" ? <ReviewScreen user={user} mode={route.mode} size={route.size} onNavigate={onNavigate} /> : null}
      {route.screen === "scenarios" ? <ScenariosScreen user={user} scenarioSlug={route.scenario} initialTopic={route.topic} onNavigate={onNavigate} /> : null}
      {route.screen === "vocab" ? <VocabularyScreen user={user} vocabId={route.vocabId} topic={route.topic} q={route.q} onNavigate={onNavigate} /> : null}
      {route.screen === "grammar" ? <GrammarScreen user={user} grammarId={route.grammarId} topic={route.topic} q={route.q} onNavigate={onNavigate} /> : null}
      {route.screen === "progress" ? <ProgressScreen user={user} onNavigate={onNavigate} /> : null}
      {route.screen === "settings" ? <SettingsScreen user={user} onUserChange={onUserChange} /> : null}
      {route.screen === "admin" ? <AdminScreen user={user} /> : null}
    </Shell>
  );
}
