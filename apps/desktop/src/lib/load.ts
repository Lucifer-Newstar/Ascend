import type { Exercise, Workout } from "@ascend/shared";

/**
 * Effort multiplier from RPE: same bands as the sidecar load model
 * (services/sidecar/app/modules/progress/muscle_load.py):
 * RPE >= 7 or not logged -> 1.0, 5-6.5 -> 0.5, below 5 -> 0.25.
 */
export function effort(rpe: number | null): number {
  if (rpe === null || rpe >= 7) return 1;
  if (rpe >= 5) return 0.5;
  return 0.25;
}

/** Effective sets per muscle for one session, sorted high to low (display only). */
export function sessionLoad(w: Workout | null, library: Exercise[]): [string, number][] {
  if (!w) return [];
  const byId = new Map(library.map((e) => [e.id, e]));
  const totals = new Map<string, number>();
  for (const s of w.sets) {
    for (const m of byId.get(s.exercise_id)?.muscles ?? []) {
      totals.set(m.muscle, (totals.get(m.muscle) ?? 0) + m.weight * effort(s.rpe));
    }
  }
  return [...totals.entries()].sort((a, b) => b[1] - a[1]);
}
