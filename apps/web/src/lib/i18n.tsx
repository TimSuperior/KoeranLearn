import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import type { AuthUser, Language, Localized } from "../types";
import { t } from "./format";
import { api } from "./api";

type I18nContextValue = {
  uiLanguage: Language;
  explanationLanguage: Language;
  ui: (key: string, fallback?: string) => string;
  admin: (key: string, fallback?: string) => string;
  content: (text: Partial<Localized> | undefined, fallback?: string) => string;
  topicLabel: (value: string | null | undefined) => string;
};

const fallbackContext: I18nContextValue = {
  uiLanguage: "en",
  explanationLanguage: "en",
  ui: (_key, fallback = "") => fallback,
  admin: (_key, fallback = "") => fallback,
  content: (text, fallback = "") => t(text, "en", fallback),
  topicLabel: (value) => value?.replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase()) || "General",
};

const I18nContext = createContext<I18nContextValue>(fallbackContext);

export function I18nProvider({ user, children }: { user: AuthUser; children: ReactNode }) {
  const [webBundle, setWebBundle] = useState<Record<string, string>>({});
  const [adminBundle, setAdminBundle] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.localizationBundle("web", user.interface_language),
      api.localizationBundle("admin", user.interface_language),
    ])
      .then(([web, admin]) => {
        if (cancelled) return;
        setWebBundle(web);
        setAdminBundle(admin);
      })
      .catch(() => {
        if (cancelled) return;
        setWebBundle({});
        setAdminBundle({});
      });

    return () => {
      cancelled = true;
    };
  }, [user.interface_language]);

  const value = useMemo<I18nContextValue>(() => {
    const uiLanguage = user.interface_language;
    const explanationLanguage = user.explanation_language || user.interface_language;
    const ui = (key: string, fallback = "") => webBundle[key] || fallback || key;
    const admin = (key: string, fallback = "") => adminBundle[key] || fallback || key;
    const topicLabel = (value: string | null | undefined) => {
      if (!value) return ui("topic.general", "General");
      return ui(`topic.${value}`, value.replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase()));
    };
    return {
      uiLanguage,
      explanationLanguage,
      ui,
      admin,
      content: (text: Partial<Localized> | undefined, fallback = "") => t(text, explanationLanguage, fallback),
      topicLabel,
    };
  }, [adminBundle, user.explanation_language, user.interface_language, webBundle]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
