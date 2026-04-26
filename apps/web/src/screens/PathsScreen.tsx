import { Lock, Route } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AuthUser, Path } from "../types";

export function PathsScreen({ user }: { user: AuthUser }) {
  const [paths, setPaths] = useState<Path[]>([]);
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    api.paths().then(setPaths).catch(console.error);
  }, []);

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {paths.map((path) => (
        <article key={path.id} className="rounded-app border border-line bg-white p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-app bg-leaf/10 text-leaf">
                <Route size={20} />
              </div>
              <div>
                <h2 className="font-semibold">{path.title[user.interface_language]}</h2>
                <p className="mt-1 text-sm leading-5 text-ink/65">{path.description[user.interface_language]}</p>
              </div>
            </div>
            {path.is_premium ? <Lock className="shrink-0 text-sun" size={18} /> : null}
          </div>
          <div className="mt-4 flex items-center gap-2 text-xs text-ink/55">
            <span className="rounded-app border border-line px-2 py-1">{path.level}</span>
            <span className="rounded-app border border-line px-2 py-1">{path.target_goal.replaceAll("_", " ")}</span>
          </div>
          <button
            type="button"
            onClick={async () => {
              await api.switchPath(path.id);
              setSelected(path.id);
            }}
            disabled={path.is_premium && !user.is_premium}
            className="mt-4 h-10 w-full rounded-app bg-leaf px-3 text-sm font-medium text-white disabled:bg-line disabled:text-ink/45"
          >
            {selected === path.id ? "Selected" : path.is_premium && !user.is_premium ? "Locked" : "Switch path"}
          </button>
        </article>
      ))}
    </div>
  );
}
