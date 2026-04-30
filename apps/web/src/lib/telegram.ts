import type { AppRoute } from "./routes";

type Insets = {
  top?: number;
  right?: number;
  bottom?: number;
  left?: number;
};

type TelegramThemeParams = {
  bg_color?: string;
  secondary_bg_color?: string;
  bottom_bar_bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  header_bg_color?: string;
  accent_text_color?: string;
  destructive_text_color?: string;
  section_bg_color?: string;
  section_header_text_color?: string;
  subtitle_text_color?: string;
  section_separator_color?: string;
};

type ClickableControl = {
  isVisible?: boolean;
  show?: () => void;
  hide?: () => void;
  onClick?: (handler: () => void) => void;
  offClick?: (handler: () => void) => void;
};

type TelegramUser = {
  language_code?: string;
};

export type TelegramWebApp = {
  initData?: string;
  initDataUnsafe?: { start_param?: string; user?: TelegramUser };
  version?: string;
  colorScheme?: "light" | "dark";
  themeParams?: TelegramThemeParams;
  safeAreaInset?: Insets;
  contentSafeAreaInset?: Insets;
  ready?: () => void;
  expand?: () => void;
  requestFullscreen?: () => void;
  exitFullscreen?: () => void;
  setHeaderColor?: (color: string) => void;
  setBackgroundColor?: (color: string) => void;
  setBottomBarColor?: (color: string) => void;
  enableClosingConfirmation?: () => void;
  disableClosingConfirmation?: () => void;
  enableVerticalSwipes?: () => void;
  disableVerticalSwipes?: () => void;
  openTelegramLink?: (url: string) => void;
  openLink?: (url: string, options?: Record<string, unknown>) => void;
  switchInlineQuery?: (query: string, chooseChatTypes?: string[]) => void;
  addToHomeScreen?: () => void;
  checkHomeScreenStatus?: (callback?: (status: string) => void) => void;
  showAlert?: (message: string) => void;
  isVersionAtLeast?: (version: string) => boolean;
  BackButton?: ClickableControl;
  SettingsButton?: ClickableControl;
  HapticFeedback?: {
    impactOccurred?: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
    notificationOccurred?: (type: "error" | "success" | "warning") => void;
  };
  onEvent?: (eventType: string, handler: (...args: unknown[]) => void) => void;
  offEvent?: (eventType: string, handler: (...args: unknown[]) => void) => void;
};

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}

const fallbackTheme = {
  bg: "#f4f0e6",
  surface: "#fffaf1",
  elevated: "#ffffff",
  text: "#122027",
  muted: "#667882",
  line: "rgba(18, 32, 39, 0.10)",
  accent: "#1f7a5a",
  accentText: "#ffffff",
  secondary: "#d96b31",
  warning: "#c27b1f",
  chip: "rgba(31, 122, 90, 0.10)"
};

export function getTelegramWebApp(): TelegramWebApp | null {
  return window.Telegram?.WebApp || null;
}

export function getTelegramInitData(): string {
  const initData = getTelegramWebApp()?.initData;
  return initData && initData.length > 0 ? initData : "dev:10001";
}

export function getTelegramStartParam(): string | null {
  const fromInit = getTelegramWebApp()?.initDataUnsafe?.start_param;
  if (fromInit) return fromInit;
  return new URLSearchParams(window.location.search).get("tgWebAppStartParam");
}

function normalizeLanguageCode(language: string | null | undefined): "ru" | "uz" | "en" {
  const value = String(language || "").toLowerCase();
  if (value.startsWith("ru")) return "ru";
  if (value.startsWith("uz")) return "uz";
  return "en";
}

export function getTelegramLanguage(): "ru" | "uz" | "en" {
  const fromTelegram = getTelegramWebApp()?.initDataUnsafe?.user?.language_code;
  if (fromTelegram) return normalizeLanguageCode(fromTelegram);
  if (typeof navigator !== "undefined") {
    return normalizeLanguageCode(navigator.languages?.[0] || navigator.language);
  }
  return "en";
}

function applyInsets(prefix: string, insets?: Insets) {
  const root = document.documentElement;
  root.style.setProperty(`--${prefix}-top`, `${insets?.top ?? 0}px`);
  root.style.setProperty(`--${prefix}-right`, `${insets?.right ?? 0}px`);
  root.style.setProperty(`--${prefix}-bottom`, `${insets?.bottom ?? 0}px`);
  root.style.setProperty(`--${prefix}-left`, `${insets?.left ?? 0}px`);
}

function applyTheme(theme?: TelegramThemeParams) {
  const root = document.documentElement;
  root.style.setProperty("--app-bg", theme?.bg_color || fallbackTheme.bg);
  root.style.setProperty("--app-surface", theme?.section_bg_color || theme?.secondary_bg_color || fallbackTheme.surface);
  root.style.setProperty("--app-elevated", theme?.secondary_bg_color || fallbackTheme.elevated);
  root.style.setProperty("--app-text", theme?.text_color || fallbackTheme.text);
  root.style.setProperty("--app-muted", theme?.subtitle_text_color || theme?.hint_color || fallbackTheme.muted);
  root.style.setProperty("--app-line", theme?.section_separator_color || fallbackTheme.line);
  root.style.setProperty("--app-accent", theme?.button_color || theme?.accent_text_color || fallbackTheme.accent);
  root.style.setProperty("--app-accent-text", theme?.button_text_color || fallbackTheme.accentText);
  root.style.setProperty("--app-secondary", theme?.destructive_text_color || fallbackTheme.secondary);
  root.style.setProperty("--app-warning", fallbackTheme.warning);
  root.style.setProperty("--app-chip", fallbackTheme.chip);
}

function syncEnvironment(webApp: TelegramWebApp | null) {
  applyTheme(webApp?.themeParams);
  applyInsets("tg-safe-area", webApp?.safeAreaInset);
  applyInsets("tg-content-safe-area", webApp?.contentSafeAreaInset);
  document.documentElement.dataset.tgColorScheme = webApp?.colorScheme || "light";
}

export function initTelegramShell() {
  const webApp = getTelegramWebApp();
  webApp?.ready?.();
  webApp?.expand?.();
  syncEnvironment(webApp);

  if (webApp?.themeParams?.header_bg_color) {
    webApp.setHeaderColor?.(webApp.themeParams.header_bg_color);
  }
  if (webApp?.themeParams?.bg_color) {
    webApp.setBackgroundColor?.(webApp.themeParams.bg_color);
  }
  if (webApp?.themeParams?.bottom_bar_bg_color) {
    webApp.setBottomBarColor?.(webApp.themeParams.bottom_bar_bg_color);
  }

  const sync = () => syncEnvironment(webApp);
  webApp?.onEvent?.("themeChanged", sync);
  webApp?.onEvent?.("safeAreaChanged", sync);
  webApp?.onEvent?.("contentSafeAreaChanged", sync);

  return () => {
    webApp?.offEvent?.("themeChanged", sync);
    webApp?.offEvent?.("safeAreaChanged", sync);
    webApp?.offEvent?.("contentSafeAreaChanged", sync);
  };
}

export function bindTelegramChrome(options: {
  route: AppRoute;
  fullscreen?: boolean;
  showBack?: boolean;
  onBack?: () => void;
  showSettings?: boolean;
  onSettings?: () => void;
  protectFromAccidentalClose?: boolean;
}) {
  const webApp = getTelegramWebApp();
  if (!webApp) return () => undefined;

  if (options.fullscreen) {
    webApp.requestFullscreen?.();
  } else {
    webApp.exitFullscreen?.();
  }

  if (options.protectFromAccidentalClose) {
    webApp.enableClosingConfirmation?.();
  } else {
    webApp.disableClosingConfirmation?.();
  }

  const backHandler = () => options.onBack?.();
  if (options.showBack) {
    webApp.BackButton?.show?.();
    webApp.BackButton?.onClick?.(backHandler);
  } else {
    webApp.BackButton?.hide?.();
  }

  const settingsHandler = () => options.onSettings?.();
  if (options.showSettings) {
    webApp.SettingsButton?.show?.();
    webApp.SettingsButton?.onClick?.(settingsHandler);
  } else {
    webApp.SettingsButton?.hide?.();
  }

  return () => {
    webApp.BackButton?.offClick?.(backHandler);
    webApp.SettingsButton?.offClick?.(settingsHandler);
  };
}

export function miniAppDirectLink(startParam: string, mode: "fullscreen" | "compact" | "normal" = "fullscreen"): string | null {
  const botUsername = import.meta.env.VITE_TELEGRAM_BOT_USERNAME as string | undefined;
  const shortName = import.meta.env.VITE_TELEGRAM_APP_SHORT_NAME as string | undefined;
  if (!botUsername) return null;
  const base = shortName ? `https://t.me/${botUsername}/${shortName}` : `https://t.me/${botUsername}`;
  const params = new URLSearchParams({ startapp: startParam });
  if (mode !== "normal") params.set("mode", mode);
  return `${base}?${params.toString()}`;
}

export function openTelegramShare(url: string, text?: string) {
  const shareUrl = new URL("https://t.me/share/url");
  shareUrl.searchParams.set("url", url);
  if (text) shareUrl.searchParams.set("text", text);
  const webApp = getTelegramWebApp();
  if (webApp?.openTelegramLink) {
    webApp.openTelegramLink(shareUrl.toString());
    return true;
  }
  window.open(shareUrl.toString(), "_blank", "noopener,noreferrer");
  return false;
}

export function shareRoute(route: AppRoute, label: string) {
  const startParam = route.screen === "lesson" || route.screen === "scenarios" || route.screen === "grammar" || route.screen === "vocab"
    ? route
    : null;
  const link = startParam ? miniAppDirectLink(routeToStartParam(startParam)) : null;
  if (!link) return false;
  openTelegramShare(link, label);
  return true;
}

function routeToStartParam(route: Extract<AppRoute, { screen: "lesson" | "scenarios" | "grammar" | "vocab" }>): string {
  if (route.screen === "lesson" && route.lessonId) return `lesson_${route.lessonId}`;
  if (route.screen === "scenarios" && route.scenario) return `scenario_${route.scenario}`;
  if (route.screen === "grammar" && route.grammarId) return `grammar_${route.grammarId}`;
  if (route.screen === "vocab" && route.vocabId) return `word_${route.vocabId}`;
  return "screen_home";
}

export function openInlineShare(query: string, chooseChatTypes: string[] = ["users", "groups"]) {
  const webApp = getTelegramWebApp();
  if (!webApp?.switchInlineQuery) return false;
  webApp.switchInlineQuery(query, chooseChatTypes);
  return true;
}

export function maybeAddToHomeScreen() {
  const webApp = getTelegramWebApp();
  webApp?.addToHomeScreen?.();
}

export function checkHomeScreenStatus(callback: (status: string) => void) {
  getTelegramWebApp()?.checkHomeScreenStatus?.(callback);
}

export function haptic(type: "success" | "warning" | "error" | "soft" = "soft") {
  const webApp = getTelegramWebApp();
  if (!webApp?.HapticFeedback) return;
  if (type === "soft") {
    webApp.HapticFeedback.impactOccurred?.("soft");
    return;
  }
  webApp.HapticFeedback.notificationOccurred?.(type);
}
