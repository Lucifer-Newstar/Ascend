import type { Section } from "@ascend/shared";

/**
 * Hand-off from another screen to the logger ("Log it" in the gallery, "Train" on a
 * skill): the exercise to open next time the Training page mounts. Kept in
 * sessionStorage so it survives the lazy page load but not an app restart.
 */
const KEY = "ascend.pendingExercise";

export interface PendingExercise {
  id: number;
  section: Section;
}

export function setPendingExercise(p: PendingExercise): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(p));
  } catch {
    /* storage unavailable: the logger just opens normally */
  }
}

/**
 * Read the pending exercise without clearing it. Safe in a useState initializer,
 * which React may call twice in development; clear it from an effect once used.
 */
export function peekPendingExercise(): PendingExercise | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    const p = JSON.parse(raw) as Partial<PendingExercise>;
    return typeof p.id === "number" && typeof p.section === "string" ? (p as PendingExercise) : null;
  } catch {
    return null;
  }
}

export function clearPendingExercise(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    /* nothing to clear */
  }
}

/** Read and clear the pending exercise (one use). */
export function takePendingExercise(): PendingExercise | null {
  const p = peekPendingExercise();
  clearPendingExercise();
  return p;
}
