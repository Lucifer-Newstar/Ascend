import type { StreakInfo, XpInfo } from "@ascend/shared";
import { useEffect, useState } from "react";

import { num } from "../lib/format";
import { CountUp, useReducedMotion } from "../lib/motion";
import { Confetti, Flash, Transient, useRise } from "./Celebrate";
import { IconFlame } from "./Icons";

/** Rank colours come from the rank tokens in index.css (both themes meet AA on panels). */
export const RANK_TOKENS: Record<string, string> = {
  E: "--color-rank-e",
  D: "--color-rank-d",
  C: "--color-rank-c",
  B: "--color-rank-b",
  A: "--color-rank-a",
  S: "--color-rank-s",
};

export const rankColor = (rank: string): string => `var(${RANK_TOKENS[rank] ?? RANK_TOKENS.E})`;

/** The rank letter is always shown as text (never colour alone), with an accessible name. */
export function RankBadge({ rank, size = 44, title }: { rank: string; size?: number; title?: string }) {
  const color = rankColor(rank);
  return (
    <div className="grid shrink-0 place-items-center rounded-md border font-display font-semibold leading-none"
      role="img" aria-label={`Rank ${rank}${title ? `, ${title}` : ""}`} data-rank={rank}
      style={{
        width: size,
        height: size,
        borderColor: `color-mix(in srgb, ${color} 55%, transparent)`,
        color,
        background: `color-mix(in srgb, ${color} 9%, transparent)`,
        fontSize: size * 0.55,
      }}>
      <span aria-hidden="true">{rank}</span>
    </div>
  );
}

/**
 * Last XP state the Dashboard showed, kept for the app session so coming back
 * after logging sets animates from where the bar was (and a level gained in the
 * meantime is celebrated once).
 */
let lastShown: { level: number; fill: number } | null = null;

export function resetXpMemory() {
  lastShown = null;
}

const fraction = (xp: XpInfo) => Math.min(1, Math.max(0, xp.xp_into_level / Math.max(1, xp.xp_for_next)));

/**
 * The fill is a full-width bar slid in from the left (translateX), so it animates
 * on the compositor and keeps its rounded end at any width.
 */
export function XpFill({ fill, className = "h-2", sheenKey = 0 }: { fill: number; className?: string; sheenKey?: number }) {
  return (
    <div className={`relative overflow-hidden rounded-full bg-xp/15 ${className}`}>
      <div
        data-testid="xp-fill"
        className="h-full w-full rounded-full bg-xp shadow-[0_0_10px_color-mix(in_srgb,var(--color-xp)_60%,transparent)] will-change-transform"
        style={{ transform: `translateX(${(fill - 1) * 100}%)`, transition: "transform 900ms cubic-bezier(0.2, 0.7, 0.2, 1)" }}
      />
      {sheenKey > 0 && (
        <span
          key={sheenKey}
          aria-hidden="true"
          className="motion-decor pointer-events-none absolute inset-y-0 left-0 w-1/4 bg-gradient-to-r from-transparent via-white/45 to-transparent"
          style={{ animation: "asc-sheen 900ms 250ms ease-out both" }}
        />
      )}
    </div>
  );
}

/** Streak count with a flame that flickers gently while the streak is alive. */
export function StreakFlame({ current }: { current: number }) {
  const alive = current > 0;
  return (
    <span className="flex items-center gap-1" data-testid="streak">
      <span className={`inline-flex ${alive ? "flame" : "opacity-50"}`} data-flame={alive ? "on" : "off"}>
        <IconFlame width={14} height={14} className="text-warn" />
      </span>
      {current}-day streak
    </span>
  );
}

export function XpBar({ xp, streak }: { xp: XpInfo; streak: StreakInfo }) {
  const reduce = useReducedMotion();
  const target = fraction(xp);
  const [levelUpOnMount] = useState(() => lastShown !== null && xp.level > lastShown.level);
  const [fill, setFill] = useState(() => {
    if (reduce) return target;
    return lastShown && lastShown.level === xp.level ? lastShown.fill : 0;
  });
  const { riseKey: xpRise } = useRise(xp.total);
  const { riseKey: levelRise } = useRise(xp.level);
  const celebrate = levelRise + (levelUpOnMount ? 1 : 0);

  useEffect(() => {
    lastShown = { level: xp.level, fill: target };
    if (reduce || typeof requestAnimationFrame !== "function") {
      setFill(target);
      return;
    }
    // Next frame, so the browser paints the start position before transitioning.
    const raf = requestAnimationFrame(() => setFill(target));
    return () => cancelAnimationFrame(raf);
  }, [target, xp.level, reduce]);

  return (
    <div className="relative flex items-center gap-4">
      <div className="relative">
        <RankBadge rank={xp.rank} />
        <Transient trigger={celebrate}><Confetti /></Transient>
      </div>
      <div className="relative min-w-0 flex-1">
        <Transient trigger={celebrate}><Flash className="-inset-2" /></Transient>
        <div className="flex items-baseline justify-between gap-3">
          <div className="flex items-baseline gap-2">
            <span className="font-display text-2xl font-bold leading-none text-ink">LV {xp.level}</span>
            <span className="text-xs text-muted">Rank {xp.rank} · {xp.rank_title}</span>
            <Transient trigger={celebrate} ms={2600}>
              <span className="pop-in rounded-full bg-xp/15 px-2 py-0.5 text-[11px] font-semibold text-xp">Level up!</span>
            </Transient>
          </div>
          <span className="text-xs text-muted">
            <span className="text-ink"><CountUp key={xp.level} value={xp.xp_into_level} /></span> / {num(xp.xp_for_next)} XP
          </span>
        </div>
        <XpFill fill={fill} className="mt-2 h-2" sheenKey={xpRise + (levelUpOnMount ? 1 : 0)} />
        <div className="mt-2 flex gap-4 text-xs text-muted">
          <span>+<CountUp value={xp.today} /> XP today <span className="text-faint">(cap {xp.daily_cap})</span></span>
          <StreakFlame current={streak.current} />
          {streak.excused > 0 && <span title="Missed days kept because you gave a reason by the next day">{streak.excused} kept with a reason</span>}
        </div>
        <span role="status" className="sr-only">{celebrate > 0 ? `Level up! You reached level ${xp.level}.` : ""}</span>
      </div>
    </div>
  );
}
