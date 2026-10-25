/**
 * Trophy shelf (v1.4, replaces the full boss ladder on Profile). Only the bosses you have
 * cleared, with how often and when you last beat them, then this week's boss as a locked
 * "???" silhouette: its tier and category say what kind of fight it is, never its name or
 * art (rule: no spoilers of locked bosses, but a clear "how to unlock").
 */
import type { BossLadderEntry, BossRaid, EarnedTitle } from "@ascend/shared";

import { CATEGORY_LABEL, bossArt } from "../lib/bosses";
import { dropName } from "../lib/cosmetics";

const shortDate = (iso: string) => new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

function lastWins(titles: EarnedTitle[]): Map<string, string> {
  const out = new Map<string, string>();
  for (const t of titles) if (!out.has(t.boss) || out.get(t.boss)! < t.earned_at) out.set(t.boss, t.earned_at);
  return out;
}

function Trophy({ b, last }: { b: BossLadderEntry; last?: string }) {
  const art = bossArt(b.name);
  return (
    <li className="flex items-center gap-3 rounded-lg border border-good/50 p-2" data-testid="trophy">
      {art ? <img src={art} alt="" width={48} height={48} className="h-12 w-12 shrink-0 rounded-md object-cover" /> : <span className="h-12 w-12 shrink-0 rounded-md bg-panel-2" />}
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-ink">{b.name}</p>
        <p className="text-[11px] text-muted">{b.seasonal ? `Seasonal · ${b.season}` : `Tier ${b.tier}`} · {CATEGORY_LABEL[b.category as keyof typeof CATEGORY_LABEL] ?? b.category}</p>
        <p className="text-[11px] text-good">
          {b.title} · beaten {b.beaten}x{last ? ` · last ${shortDate(last)}` : ""}
          {b.drop && dropName(b.drop) ? ` · dropped ${dropName(b.drop)}` : ""}
        </p>
      </div>
    </li>
  );
}

function Locked({ current }: { current: BossRaid | null | undefined }) {
  const art = current && !current.defeated ? bossArt(current.name) : null;
  const fight = current && !current.defeated;
  const kind = fight
    ? [current.seasonal ? "Seasonal" : current.tier ? `Tier ${current.tier}` : null, current.category ? CATEGORY_LABEL[current.category] : null].filter(Boolean).join(" · ")
    : "A new boss arrives on Monday";
  return (
    <li className="flex items-center gap-3 rounded-lg border border-dashed border-line-2 p-2" data-testid="trophy-locked">
      <span className="relative h-12 w-12 shrink-0 overflow-hidden rounded-md bg-panel-2" aria-hidden="true">
        {art && <img src={art} alt="" width={48} height={48} className="h-12 w-12 object-cover opacity-70 [filter:brightness(0)]" />}
        <span className="absolute inset-0 grid place-items-center font-display text-lg font-bold text-faint">?</span>
      </span>
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink">??? <span className="sr-only">(locked boss)</span></p>
        <p className="text-[11px] text-muted">{kind}</p>
        <p className="text-[11px] text-faint">
          {fight ? "How to unlock: beat this week's boss by training this week." : "How to unlock: beat next week's boss."}
          {fight && current.seasonal ? " It drops a seasonal cosmetic." : ""}
        </p>
      </div>
    </li>
  );
}

export function TrophyShelf({ bosses, current, titles }: { bosses: BossLadderEntry[]; current?: BossRaid | null; titles?: EarnedTitle[] | null }) {
  const cleared = bosses.filter((b) => b.beaten > 0);
  const last = lastWins(titles ?? []);
  return (
    <div className="space-y-2" data-testid="trophy-shelf">
      <p className="text-xs text-muted"><span className="text-ink">{cleared.length}</span> of {bosses.length} bosses cleared</p>
      <ul className="grid gap-1.5 md:grid-cols-2 xl:grid-cols-3">
        {cleared.map((b) => <Trophy key={b.name} b={b} last={last.get(b.name)} />)}
        <Locked current={current} />
      </ul>
      {cleared.length === 0 && <p className="text-sm text-muted">Your shelf is empty for now. Your first boss win goes here.</p>}
    </div>
  );
}
