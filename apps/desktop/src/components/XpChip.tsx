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

import { api } from "../api/client";
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
  const streak = game.streak.current;
  return (
    <div className="flex items-center gap-3" data-testid="xp-status">
      <div className="relative flex items-center gap-2.5 rounded-md border border-line py-1 pl-1 pr-3 text-xs" data-testid="xp-chip">
        <Transient trigger={levelKey}><Flash /><Confetti pieces={12} spread={46} /></Transient>
        <RankBadge rank={xp.rank} title={xp.rank_title} size={28} />
        <span className="font-display text-base font-semibold leading-none text-ink">LV {xp.level}</span>
        <XpSegments key={xp.level} fill={fill} />
        <span className="text-muted">
          <span className="text-ink"><CountUp key={xp.level} value={xp.xp_into_level} duration={600} /></span>
          <span className="sr-only"> of {xp.xp_for_next} XP to the next level</span>
          <span aria-hidden="true">/{xp.xp_for_next} XP</span>
        </span>
        <Transient trigger={riseKey}>
          <span aria-hidden="true" className="float-up motion-decor pointer-events-none absolute -top-2 right-3 font-semibold text-xp" data-testid="xp-gain">
            +{delta} XP
          </span>
        </Transient>
        <span role="status" className="sr-only">{levelKey > 0 ? `Level up! You reached level ${xp.level}.` : ""}</span>
      </div>
      <span className="flex items-center gap-1 text-sm font-semibold text-ink" title={`${streak}-day streak · best ${game.streak.best} · ${game.streak.freezes_held} freeze${game.streak.freezes_held === 1 ? "" : "s"} held`} data-testid="top-streak">
        <span className={`inline-flex ${streak > 0 ? "flame" : "opacity-50"}`} aria-hidden="true"><IconFlame width={16} height={16} className="text-warn" /></span>
        {streak}
        <span className="sr-only">-day streak</span>
      </span>
    </div>
  );
}
