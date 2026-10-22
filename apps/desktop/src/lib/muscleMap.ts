import type { MuscleActivity, MuscleState, MuscleStatus } from "@ascend/shared";

/**
 * Each status has exactly one colour token (index.css), shared by the map, its legend,
 * the hover card and the "ready to train" pulse. System blue (--color-accent) is never a
 * status colour.
 */
export const STATUS_TOKEN: Record<MuscleStatus, string> = {
  over: "--color-map-over",
  recovering: "--color-map-recovering",
  under: "--color-map-under",
  optimal: "--color-map-optimal",
  no_data: "--color-map-nodata",
};

/** A muscle that is ready to train again pulses in the "ready / recovered" colour. */
export const READY_TOKEN = "--color-map-optimal";

/** CSS colour for a status, as a var() reference (for style attributes and CSS rules). */
export const statusVar = (status: MuscleStatus): string => `var(${STATUS_TOKEN[status]})`;

/** Dark-theme values of the status tokens, used only when a token cannot be read (tests, SSR). */
export const STATUS_COLORS: Record<MuscleStatus, string> = {
  over: "#b86b6b",
  recovering: "#b8995f",
  under: "#6f80b5",
  optimal: "#5a9c7f",
  no_data: "#26324a",
};

export const STATUS_LABELS: Record<MuscleStatus, string> = {
  over: "Over",
  recovering: "Recovering",
  under: "Under",
  optimal: "Optimal",
  no_data: "No data",
};

const PRECEDENCE: Record<MuscleStatus, number> = {
  over: 4,
  recovering: 3,
  under: 2,
  optimal: 1,
  no_data: 0,
};

/**
 * Several of ASCEND's 19 regions share one figure region (the three delt heads
 * all draw as "deltoids"). The figure shows the most urgent status:
 * over > recovering > under > optimal > no data (same rule as the sidecar).
 */
export function statusBySlug(states: MuscleState[]): Map<string, MuscleStatus> {
  const out = new Map<string, MuscleStatus>();
  for (const s of states) {
    const prev = out.get(s.map_slug);
    if (!prev || PRECEDENCE[s.status] > PRECEDENCE[prev]) out.set(s.map_slug, s.status);
  }
  return out;
}

export function regionsForSlug(states: MuscleState[], slug: string): MuscleState[] {
  return states.filter((s) => s.map_slug === slug);
}

export function countByStatus(states: MuscleState[]): Record<MuscleStatus, number> {
  const counts: Record<MuscleStatus, number> = { over: 0, recovering: 0, under: 0, optimal: 0, no_data: 0 };
  for (const s of states) counts[s.status] += 1;
  return counts;
}

/** Display names for the figure's regions (several ASCEND muscles share one region). */
export const SLUG_LABELS: Record<string, string> = {
  chest: "Chest",
  deltoids: "Shoulders",
  biceps: "Biceps",
  triceps: "Triceps",
  forearm: "Forearms",
  trapezius: "Traps",
  "upper-back": "Upper back",
  "lower-back": "Lower back",
  abs: "Abs",
  obliques: "Obliques",
  gluteal: "Glutes",
  quadriceps: "Quads",
  hamstring: "Hamstrings",
  adductors: "Adductors",
  calves: "Calves",
};

/** Over or still recovering: drawn with a quiet outline. */
export function isFatigued(m: MuscleState): boolean {
  return m.status === "over" || m.status === "recovering";
}

/**
 * Trained recently, now recovered and not over the weekly band: ready to train
 * again. These breathe gently on the map (Fitbod-style "fresh" muscles).
 */
export function isReadyAgain(m: MuscleState): boolean {
  return m.es_7d > 0 && m.readiness >= 0.95 && (m.status === "under" || m.status === "optimal");
}

export interface SlugSummary {
  slug: string;
  label: string;
  status: MuscleStatus;
  regions: MuscleState[];
  sets: number;
  volumeKg: number;
  lastTrained: string | null;
  fatigued: boolean;
  readyAgain: boolean;
}

/** One summary per figure region: worst status, summed load, latest training. */
export function summarizeSlugs(states: MuscleState[], activity: MuscleActivity[] = []): Map<string, SlugSummary> {
  const act = new Map(activity.map((a) => [a.key, a]));
  const status = statusBySlug(states);
  const out = new Map<string, SlugSummary>();
  for (const m of states) {
    const a = act.get(m.key);
    let row = out.get(m.map_slug);
    if (!row) {
      row = {
        slug: m.map_slug,
        label: SLUG_LABELS[m.map_slug] ?? m.label,
        status: status.get(m.map_slug) ?? "no_data",
        regions: [],
        sets: 0,
        volumeKg: 0,
        lastTrained: null,
        fatigued: false,
        readyAgain: false,
      };
      out.set(m.map_slug, row);
    }
    row.regions.push(m);
    row.sets += a?.sets ?? 0;
    row.volumeKg += a?.volume_kg ?? 0;
    if (a?.last_trained && (!row.lastTrained || a.last_trained > row.lastTrained)) row.lastTrained = a.last_trained;
    row.fatigued ||= isFatigued(m);
  }
  for (const row of out.values()) {
    row.sets = Math.round(row.sets * 10) / 10;
    row.readyAgain = !row.fatigued && row.regions.some(isReadyAgain);
  }
  return out;
}

/** The region to open when a figure region is clicked: the most urgent one. */
export function primaryRegion(summary: SlugSummary): MuscleState {
  return [...summary.regions].sort((a, b) => PRECEDENCE[b.status] - PRECEDENCE[a.status] || b.es_7d - a.es_7d)[0];
}

/** Volume heat ramp (Hevy-style distribution), light to deep, per theme. */
export const HEAT: Record<"dark" | "light", string[]> = {
  dark: ["#1d3442", "#25495a", "#2f6175", "#3c7a8f", "#5193a6"],
  light: ["#d6e6ec", "#b0cdd8", "#86afbf", "#5e90a3", "#3d7286"],
};

/** Colour for a share of the busiest region's sets (0..1); null means untrained. */
export function heatColor(share: number, theme: "dark" | "light"): string | null {
  if (!(share > 0)) return null;
  const ramp = HEAT[theme];
  return ramp[Math.min(ramp.length - 1, Math.floor(Math.min(1, share) * ramp.length - 1e-9))];
}

/** "today", "yesterday", "3 days ago", "never" (looking back 28 days). */
export function agoLabel(iso: string | null, now: Date = new Date()): string {
  if (!iso) return "not in the last 4 weeks";
  const then = new Date(iso);
  const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((day(now) - day(then)) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  return `${days} days ago`;
}
