import { Crown, Lock } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AuthUser } from "../types";

type Pack = { id: number; title: Record<string, string>; description: Record<string, string>; price_minor: number; currency: string };

export function PremiumScreen({ user }: { user: AuthUser }) {
  const [packs, setPacks] = useState<Pack[]>([]);
  const [access, setAccess] = useState<{ is_premium: boolean; limits: Record<string, number> } | null>(null);

  useEffect(() => {
    api.premiumCatalog().then(setPacks).catch(console.error);
    api.premiumAccess(user.telegram_id).then(setAccess).catch(console.error);
  }, [user.telegram_id]);

  return (
    <div className="space-y-4">
      <section className="rounded-app border border-line bg-white p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-app bg-sun/10 text-sun">
            <Crown size={20} />
          </div>
          <div>
            <h2 className="font-semibold">{access?.is_premium ? "Premium active" : "Free plan"}</h2>
            <p className="text-sm text-ink/60">Writing limit: {access?.limits.writing_daily ?? 5} per day</p>
          </div>
        </div>
      </section>
      <div className="grid gap-3 md:grid-cols-2">
        {packs.map((pack) => (
          <article key={pack.id} className="rounded-app border border-line bg-white p-4">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold">{pack.title[user.interface_language]}</h2>
                <p className="mt-1 text-sm leading-5 text-ink/65">{pack.description[user.interface_language]}</p>
              </div>
              <Lock className="shrink-0 text-sun" size={18} />
            </div>
            <button type="button" className="h-10 w-full rounded-app bg-ink px-4 text-sm font-medium text-white">
              {pack.currency} {(pack.price_minor / 100).toFixed(2)}
            </button>
          </article>
        ))}
      </div>
    </div>
  );
}
