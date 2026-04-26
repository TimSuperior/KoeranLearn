import type { LucideIcon } from "lucide-react";

export function StatTile({ label, value, icon: Icon, tone = "leaf" }: { label: string; value: string | number; icon: LucideIcon; tone?: "leaf" | "sky" | "sun" | "coral" }) {
  const toneClass = {
    leaf: "text-leaf bg-leaf/10",
    sky: "text-sky bg-sky/10",
    sun: "text-sun bg-sun/10",
    coral: "text-coral bg-coral/10"
  }[tone];

  return (
    <div className="rounded-app border border-line bg-white p-3">
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-app ${toneClass}`}>
          <Icon size={20} />
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm text-ink/60">{label}</div>
          <div className="truncate text-xl font-semibold">{value}</div>
        </div>
      </div>
    </div>
  );
}
