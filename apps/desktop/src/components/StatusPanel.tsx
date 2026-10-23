/**
 * The Hunter profile on Today (v8; was the Status panel): name, rank, level, XP, the
 * newest boss title and the five computed hunter stats.
 *
 * It is a normal card (the System window is kept for System events). Each stat has a
 * "Why?" button that lists the formula and the exact numbers it used (stats-v1), so no
 * number on this panel is unexplained.
 */
import type { GameSummary, Stat, Stats } from "@ascend/shared";
import { useId, useState } from "react";

import { CountUp } from "../lib/motion";
import { XpSegments } from "./XpChip";
import { RankBadge } from "./XpBar";

const ABBR: Record<Stat["key"], string> = { str: "STR", agi: "AGI", end: "END", vit: "VIT", int: "INT" };

const INPUT_LABEL: Record<string, string> = {
  strength_steps_unlocked: "Strength-tree steps earned",
  strength_steps_total: "Strength-tree steps in total",
  best_e1rm_kg_90d: "Best estimated one-rep max in 90 days (kg)",
  bodyweight_kg: "Body weight (kg)",
  relative_e1rm: "Estimated one-rep max ÷ body weight",
  skill_steps_unlocked: "Skill-tree steps earned",
  skill_steps_total: "Skill-tree steps in total",
  cardio_minutes: "Cardio minutes",
  target_minutes: "Target minutes",
  checkin_days: "Days with a check-in",
  window_days: "Days in the window",
  mean_readiness: "Average readiness",
  meal_days: "Days with a meal logged",
  quest_done: "Quest tasks done",
  quest_total: "Quest tasks issued",
};

function StatRow({ stat }: { stat: Stat }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <li>
      <div className="flex items-center gap-3">
        <span className="w-9 font-display text-sm font-semibold tracking-[0.08em] text-muted" title={stat.label}>{ABBR[stat.key]}</span>
        <span className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-line" aria-hidden="true">
          <span className="absolute inset-0 origin-left rounded-full bg-ink/80 transition-transform duration-[600ms] ease-[var(--ease-out)]" style={{ transform: `scaleX(${stat.value / 100})` }} />
        </span>
        <span className="w-8 text-right text-sm font-semibold text-ink"><CountUp value={stat.value} duration={600} /></span>
        <button type="button" className="text-xs text-accent hover:underline" aria-expanded={open} aria-controls={id}
          aria-label={`Why is ${stat.label} ${stat.value}?`} onClick={() => setOpen((o) => !o)}>
          Why?
        </button>
      </div>
      {open && (
        <div id={id} className="panel-in mt-2 rounded-md border border-line bg-panel-2 p-3 text-xs">
          <p className="text-ink">{stat.label}: {stat.formula}.</p>
          <dl className="mt-2 grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 text-muted">
            {Object.entries(stat.inputs).map(([k, v]) => (
              <div key={k} className="contents">
                <dt>{INPUT_LABEL[k] ?? k}</dt>
                <dd className="text-right text-ink">{v === null ? "no data" : String(v)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </li>
  );
}

export function StatusPanel({ game, stats, title = null, name = null, titlesEarned = 0 }: {
  game: GameSummary;
  stats: Stats | null;
  /** The newest title from a beaten weekly boss (the only title source). */
  title?: string | null;
  name?: string | null;
  titlesEarned?: number;
}) {
  const xp = game.xp;
  const fill = Math.min(1, xp.xp_into_level / Math.max(1, xp.xp_for_next));
  return (
    <section className={`card hunter-card rank-${xp.rank.toLowerCase()} h-full p-5`} aria-labelledby="status-title" data-testid="status-panel">
      <div className="flex items-baseline justify-between gap-2">
        <h2 id="status-title" className="card-title">Hunter profile</h2>
        {game.streak.current > 0 && <span className="text-xs text-muted" title="Days in a row with something logged">🔥 {game.streak.current}-day streak</span>}
      </div>
      {name && <p className="mt-1 truncate font-display text-lg font-bold uppercase tracking-[0.06em] text-ink">{name}</p>}
      <div className="mt-3 flex items-center gap-4">
        <RankBadge rank={xp.rank} title={xp.rank_title} size={56} />
        <div className="min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="font-display text-sm font-semibold uppercase tracking-[0.08em] text-muted">Level</span>
            <span className="text-display-xl text-ink"><CountUp value={xp.level} duration={600} /></span>
          </div>
          {title && (
            <p className="truncate text-xs text-accent" data-testid="hunter-title" title={`Title from a beaten weekly boss${titlesEarned > 1 ? ` (${titlesEarned} earned)` : ""}`}>
              « {title} »
            </p>
          )}
          <div className="truncate text-sm text-muted">{xp.rank_title}</div>
        </div>
      </div>
      <div className="mt-3">
        <XpSegments key={xp.level} fill={fill} className="h-2 w-full" />
        <div className="mt-1.5 flex flex-wrap justify-between gap-x-3 text-small text-muted">
          <span><span className="text-ink">{xp.xp_into_level}</span> / {xp.xp_for_next} XP</span>
          <span>{xp.xp_for_next - xp.xp_into_level} to level {xp.level + 1}</span>
        </div>
      </div>
      <ul className="mt-4 space-y-2.5" aria-label="Stats">
        {stats ? stats.stats.map((s) => <StatRow key={s.key} stat={s} />) : <li className="text-xs text-muted">Stats load with your logs.</li>}
      </ul>
      {stats && <p className="mt-3 text-[11px] text-faint">Computed from your last {stats.window_days} days of logs</p>}
    </section>
  );
}
