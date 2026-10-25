/**
 * Near goals on Today (v1.3, review S5/S6 and 1.6): the next thing within reach and the
 * numbers that never go down. Lifetime sessions with the next milestone, the next
 * sub-rank, the best streak and weeks in a row at the weekly target. Nothing here can be
 * lost by missing a day (design rule D2).
 */
import type { GameSummary } from "@ascend/shared";

import { num } from "../lib/format";

function Bar({ value, max, label }: { value: number; max: number; label: string }) {
  const pct = Math.max(0, Math.min(100, Math.round((value / Math.max(1, max)) * 100)));
  return (
    <span className="relative block h-1.5 w-full overflow-hidden rounded-full bg-line" role="progressbar" aria-label={label}
      aria-valuemin={0} aria-valuemax={max} aria-valuenow={Math.min(value, max)}>
      <span className="absolute inset-y-0 left-0 rounded-full bg-xp" style={{ width: `${pct}%` }} />
    </span>
  );
}

export function NearGoals({ game }: { game: GameSummary }) {
  const s = game.streak;
  const xp = game.xp;
  const sessions = s.lifetime_sessions ?? 0;
  const milestone = s.next_milestone ?? null;
  const weeks = s.weeks_in_a_row ?? 0;
  const target = s.week_target ?? 3;
  return (
    <div className="mt-4 space-y-3 border-t border-line pt-3" data-testid="near-goals">
      <h3 className="font-display text-xs font-semibold uppercase tracking-[0.08em] text-muted">Within reach</h3>
      <div>
        <div className="flex justify-between gap-2 text-sm">
          <span className="text-ink" data-testid="lifetime-sessions">{num(sessions)} session{sessions === 1 ? "" : "s"} done</span>
          {milestone !== null && <span className="text-muted">next: {num(milestone)}</span>}
        </div>
        {milestone !== null && <div className="mt-1"><Bar value={sessions} max={milestone} label={`Sessions toward ${milestone}`} /></div>}
      </div>
      {xp.sub_rank && (
        <p className="text-sm text-muted" data-testid="sub-rank">
          Rank <span className="text-ink">{xp.sub_rank}</span>
          {xp.next_sub_rank && xp.next_sub_rank_level ? <> · {xp.next_sub_rank} at level {xp.next_sub_rank_level}</> : null}
        </p>
      )}
      <dl className="grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-md border border-line bg-panel-2 p-2">
          <dt className="text-muted">Best streak</dt>
          <dd className="text-sm text-ink" data-testid="best-streak">{s.best} day{s.best === 1 ? "" : "s"}</dd>
        </div>
        <div className="rounded-md border border-line bg-panel-2 p-2" title={`Weeks that met your ${target} training days (or beat the weekly boss)`}>
          <dt className="text-muted">Weeks in a row</dt>
          <dd className="text-sm text-ink" data-testid="weeks-in-a-row">{weeks} <span className="text-muted">at {target}/week</span></dd>
        </div>
      </dl>
    </div>
  );
}
