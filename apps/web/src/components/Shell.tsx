import { ChartColumnBig, Home, Languages, MessageCircleMore, Repeat2, Settings2 } from "lucide-react";
import type { ReactNode } from "react";
import type { AppRoute } from "../lib/routes";
import { navSection } from "../lib/routes";
import { IconButton } from "./ui";

const navItems = [
  { key: "home", label: "Home", icon: Home },
  { key: "review", label: "Review", icon: Repeat2 },
  { key: "scenarios", label: "Scenarios", icon: MessageCircleMore },
  { key: "library", label: "Library", icon: Languages },
  { key: "progress", label: "Progress", icon: ChartColumnBig }
] as const;

export function Shell({
  children,
  route,
  title,
  subtitle,
  onNavigate,
  headerAction
}: {
  children: ReactNode;
  route: AppRoute;
  title: string;
  subtitle?: string;
  onNavigate: (route: AppRoute) => void;
  headerAction?: ReactNode;
}) {
  const active = navSection(route);

  return (
    <div className="min-h-screen bg-[color:var(--app-bg)] text-[color:var(--app-text)]">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -left-20 top-0 h-64 w-64 rounded-full bg-[radial-gradient(circle,rgba(31,122,90,0.18),transparent_70%)]" />
        <div className="absolute -right-16 top-28 h-72 w-72 rounded-full bg-[radial-gradient(circle,rgba(217,107,49,0.12),transparent_68%)]" />
      </div>

      <header className="sticky top-0 z-30 px-4 pb-4 pt-[max(16px,var(--tg-content-safe-area-top))]">
        <div className="mx-auto max-w-3xl rounded-[28px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)]/88 px-4 py-4 shadow-[0_16px_50px_rgba(15,23,42,0.08)] backdrop-blur-md">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[color:var(--app-muted)]">Korean Learn</p>
              <h1 className="mt-1 truncate text-[1.35rem] font-semibold leading-tight">{title}</h1>
              {subtitle ? <p className="mt-1 truncate text-sm text-[color:var(--app-muted)]">{subtitle}</p> : null}
            </div>
            <div className="shrink-0">{headerAction || <IconButton icon={Settings2} label="Settings" tone="neutral" onClick={() => onNavigate({ screen: "settings" })} />}</div>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-3xl px-4 pb-[calc(108px+var(--tg-content-safe-area-bottom))]">
        {children}
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-40 px-4 pb-[max(14px,var(--tg-content-safe-area-bottom))]">
        <div className="mx-auto max-w-3xl rounded-[30px] border border-[color:var(--app-line)] bg-[color:var(--app-surface)]/94 p-2 shadow-[0_18px_60px_rgba(15,23,42,0.16)] backdrop-blur-xl">
          <div className="grid grid-cols-5 gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const selected = item.key === active;
              const target =
                item.key === "library"
                  ? ({ screen: route.screen === "grammar" ? "grammar" : "vocab" } as AppRoute)
                  : ({ screen: item.key } as AppRoute);

              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => onNavigate(target)}
                  className={`flex min-h-[62px] flex-col items-center justify-center gap-1 rounded-[22px] px-1 text-[11px] font-medium transition ${
                    selected
                      ? "bg-[color:var(--app-text)] text-white shadow-[0_10px_24px_rgba(15,23,42,0.16)]"
                      : "text-[color:var(--app-muted)]"
                  }`}
                >
                  <Icon size={19} strokeWidth={selected ? 2.4 : 2} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </nav>
    </div>
  );
}
