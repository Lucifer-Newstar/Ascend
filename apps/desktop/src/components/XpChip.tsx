/**
 * Rank, level and XP in the top bar, on every page: the rank badge, "LV n", a
 * 10-segment XP bar and the streak flame.
 *
 * When a logged set, a quest or a finished workout earns XP, the segments fill with an
 * eased count-up (at most 600 ms), "+N XP" floats up, and a level-up bursts a little
 * confetti (decoration only; with Reduce motion the new numbers simply appear). A new
 * level starts its bar and count from zero (keyed by level) instead of sliding backwards.
 */
import type { GameSummary } from "@ascend/shared";
import { useEffect, useId, useRef, useState } from "react";

import { api } from "../api/client";
import { num } from "../lib/format";
import { CountUp, useReducedMotion } from "../lib/motion";
import { useApi } from "../lib/useApi";
import { Confetti, Flash, Transient, useRise } from "./Celebrate";
import { IconFlame } from "./Icons";
import { RankBadge } from "./XpBar";

export const XP_SEGMENTS = 10;

/** How full each of the n segments is (0..1) for an overall fill of 0..1. */
export function segmentFills(fill: number, n = XP_SEGMENTS): number[] {
  const f = Math.min(1, Math.max(0, fill)) * n;
  return Array.from({ length: n }, (_, i) => Math.min(1, Math.max(0, f - i)));
}

/** A segmented XP bar. Each segment scales on X (transform only, 600 ms); Reduce motion → instant. */
export function XpSegments({ fill, className = "h-1.5 w-28" }: { fill: number; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <div className={`flex gap-[3px] ${className}`} aria-hidden="true" data-testid="xp-segments">
      {segmentFills(fill).map((k, i) => (
        <span key={i} className="relative h-full flex-1 overflow-hidden rounded-[2px] bg-xp/20">
          <span
            className="absolute inset-0 origin-left bg-xp"
            data-fill={k.toFixed(2)}
            style={{ transform: `scaleX(${k})`, transition: reduce ? "none" : `transform 600ms var(--ease-out) ${i * 20}ms` }}
          />
        </span>
      ))}
    </div>
  );
}

/** Fetches the game summary itself (tests, standalone use). The shell passes its own. */
export function XpChip({ refreshKey }: { refreshKey: number }) {
  const game = useApi(api.game, [refreshKey]);
  return <XpStatus game={game.data ?? undefined} />;
}

export function XpStatus({ game }: { game: GameSummary | undefined }) {
  const xp = game?.xp;
  const { riseKey, delta } = useRise(xp?.total);
  const { riseKey: levelKey } = useRise(xp?.level);
  if (!xp || !game) return null;
  const fill = Math.min(1, xp.xp_into_level / Math.max(1, xp.xp_for_next));
  return (
    <div className="flex items-center gap-3" data-testid="xp-status">
      <div className="relative flex items-center gap-2.5 rounded-md border border-line py-1 pl-1 pr-3 text-xs" data-testid="xp-chip">
        <Transient trigger={levelKey}><Flash /><Confetti pieces={12} spread={46} /></Transient>
        <RankBadge rank={xp.rank} title={xp.rank_title} size={28} />
        <span className="font-display text-base font-semibold leading-none text-ink">LV {xp.level}</span>
        <XpSegments key={xp.level} fill={fill} />
        <span className="text-muted">
          <span className="text-ink"><CountUp key={xp.level} value={xp.xp_into_level} duration={600} /></span>
          <span className="sr-only"> of {num(xp.xp_for_next)} XP to the next level</span>
          <span aria-hidden="true">/{num(xp.xp_for_next)} XP</span>
        </span>
        <Transient trigger={riseKey}>
          <span aria-hidden="true" className="float-up motion-decor pointer-events-none absolute -top-2 right-3 font-semibold text-xp" data-testid="xp-gain">
            +{delta} XP
          </span>
        </Transient>
        <span role="status" className="sr-only">{levelKey > 0 ? `Level up! You reached level ${xp.level}.` : ""}</span>
      </div>
      <StreakButton streak={game.streak} />
    </div>
  );
}

/**
 * The streak flame. Clicking it explains the rules: a reason by the next day keeps a missed
 * day, two missed days in a row reset the streak, and a missed
 * day never removes XP, levels, ranks or skills (the next quest adds a Comeback item).
 */
export function StreakButton({ streak: s }: { streak: GameSummary["streak"] }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const id = useId();
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    const onDown = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onDown);
    };
  }, [open]);
  return (
    <div className="relative" ref={box}>
      <button type="button" aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)} data-testid="top-streak"
        aria-label={`${s.current}-day streak, details`}
        className="flex items-center gap-1 rounded-md px-1.5 py-1 text-sm font-semibold text-ink transition-colors duration-150 hover:bg-panel-2">
        <span className={`inline-flex ${s.current > 0 ? "flame" : "opacity-50"}`} aria-hidden="true"><IconFlame width={16} height={16} className="text-warn" /></span>
        {s.current}
      </button>
      {open && (
        <div id={id} role="dialog" aria-label="Streak" className="card panel-in absolute right-0 top-full z-40 mt-2 w-72 p-4 text-left shadow-[var(--shadow-panel)]">
          <p className="text-h3 text-ink">{s.current}-day streak</p>
          <p className="text-xs text-muted">Best {s.best} · {s.active_today ? "today counted" : "today not counted yet"}</p>
          {s.excused > 0 && <p className="mt-2 text-xs text-muted">{s.excused} missed day{s.excused === 1 ? "" : "s"} kept with a reason</p>}
          {s.reason_due && <p className="mt-2 text-xs text-warn">Yesterday is waiting for its reason: tell your trainer on Today.</p>}
          <ul className="mt-3 space-y-1.5 text-xs text-muted">
            <li>Missed a day? Give the reason by the next day and the streak is kept. Two missed days in a row, or no reason, reset it.</li>
            <li><span className="font-medium text-ink">Progress is never lost.</span> A missed day never removes XP, levels, ranks or unlocked skills; the next day&apos;s quest adds a short Comeback item instead.</li>
          </ul>
        </div>
      )}
    </div>
  );
}
