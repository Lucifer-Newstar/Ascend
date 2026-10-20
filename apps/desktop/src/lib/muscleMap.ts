import type { MuscleState, MuscleStatus } from "@ascend/shared";

/** Status colours (same tokens as index.css), used by the map and its legend. */
export const STATUS_COLORS: Record<MuscleStatus, string> = {
  over: "#ef4444",
  recovering: "#f5a524",
  under: "#4f7bd9",
  optimal: "#22c55e",
  no_data: "#2a3345",
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
