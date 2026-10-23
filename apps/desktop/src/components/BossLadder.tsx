/**
 * The boss ladder (boss-v2, v1.2): the twelve weekly bosses grouped by tier, E to S,
 * each tagged with its category, and the four seasonal bosses with their months and the
 * cosmetic each drops. Beaten bosses show how many times.
 */
import type { BossCategory, BossLadderEntry } from "@ascend/shared";

import { bossArt } from "../lib/bosses";
import { dropName } from "../lib/cosmetics";

export const CATEGORY_LABEL: Record<BossCategory, string> = {
  strength: "Strength",
  calisthenics: "Calisthenics",
  cardio: "Cardio",
  martial_arts: "Martial arts",
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const monthSpan = (m: number[]): string => (m.length ? `${MONTHS[m[0] - 1]} to ${MONTHS[m[m.length - 1] - 1]}` : "");

function BossTile({ b }: { b: BossLadderEntry }) {
  const art = bossArt(b.name);
  return (
    <li className={`flex items-center gap-3 rounded-lg border p-2 ${b.beaten ? "border-good/50" : "border-line-2"}`} data-testid="ladder-boss">
      {art ? <img src={art} alt="" width={48} height={48} className="h-12 w-12 shrink-0 rounded-md object-cover" /> : <span className="h-12 w-12 shrink-0 rounded-md bg-panel-2" />}
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-ink">{b.name}</p>
        <p className="text-[11px] text-muted">
          {CATEGORY_LABEL[b.category]}
          {b.seasonal ? ` · ${b.season}, ${monthSpan(b.months)}` : ""}
        </p>
        <p className="text-[11px] text-faint">
          {b.beaten ? <span className="text-good">Beaten {b.beaten}x · {b.title}</span> : `Title: ${b.title}`}
          {b.drop && dropName(b.drop) ? ` · drops ${dropName(b.drop)}` : ""}
        </p>
      </div>
    </li>
  );
}

export function BossLadder({ bosses }: { bosses: BossLadderEntry[] }) {
  const tiers = ["E", "D", "C", "B", "A", "S"];
  const seasonal = bosses.filter((b) => b.seasonal);
  return (
    <div className="space-y-4" data-testid="boss-ladder">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {tiers.map((t) => {
          const row = bosses.filter((b) => !b.seasonal && b.tier === t);
          if (row.length === 0) return null;
          return (
            <section key={t} aria-label={`Tier ${t}`}>
              <h3 className="mb-1.5 font-display text-xs font-bold tracking-wider text-accent">Tier {t}</h3>
              <ul className="space-y-1.5">{row.map((b) => <BossTile key={b.name} b={b} />)}</ul>
            </section>
          );
        })}
      </div>
      {seasonal.length > 0 && (
        <section aria-label="Seasonal bosses">
          <h3 className="mb-1.5 font-display text-xs font-bold tracking-wider text-warn">Seasonal: tier follows your level</h3>
          <ul className="grid gap-1.5 md:grid-cols-2 xl:grid-cols-4">{seasonal.map((b) => <BossTile key={b.name} b={b} />)}</ul>
        </section>
      )}
    </div>
  );
}
