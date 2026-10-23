/** Small pure helpers used across screens (unit-tested in format.test.ts). */

export function pct(value: number, target: number): number {
  if (target <= 0) return 0;
  return Math.max(0, Math.min(1, value / target));
}

/** A whole number with digit grouping, en-IN like the rest of the app (82,416 / 3,82,416). */
export function num(n: number): string {
  return Math.round(n).toLocaleString("en-IN");
}

export function kcal(n: number): string {
  return Math.round(n).toLocaleString("en-IN");
}

export function grams(n: number): string {
  return `${Math.round(n)} g`;
}

export function signedXp(n: number): string {
  return `+${n} XP`;
}

export function portionLabel(portions: number, label: string): string {
  // "1 katori" x 1.5 -> "1.5 x 1 katori"
  return portions === 1 ? label : `${portions} × ${label}`;
}

export function dayLabel(isoDay: string, today = new Date()): string {
  const d = new Date(`${isoDay}T00:00:00`);
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const diff = Math.round((t.getTime() - d.getTime()) / 86_400_000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return dateLabel(isoDay);
}

/** "Tue 20 Oct": the calendar date in the app's one date style. */
export function dateLabel(isoDay: string): string {
  return new Date(`${isoDay}T00:00:00`).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}

export function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export function readyAtLabel(iso: string | null): string {
  if (!iso) return "ready now";
  const d = new Date(iso);
  return `ready ~${d.toLocaleDateString("en-GB", { weekday: "short" })} ${d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
}

/** "1 set", "3 sets": a count with its noun in the right number. */
export function count(n: number, singular: string, plural = `${singular}s`): string {
  return `${n} ${n === 1 ? singular : plural}`;
}

/**
 * A date range like "24 Nov – 15 Dec", with the years when either end is not this year
 * ("Nov 2027 – Aug 2028"): without them a range a year away read as next month.
 */
export function dateRange(fromIso: string, toIso: string, today = new Date()): string {
  const from = new Date(`${fromIso.slice(0, 10)}T00:00:00`);
  const to = new Date(`${toIso.slice(0, 10)}T00:00:00`);
  const y = today.getFullYear();
  const withYear = from.getFullYear() !== y || to.getFullYear() !== y;
  // Across years the day adds nothing a reader needs: "Nov 2027 – Aug 2028".
  const f = (d: Date) => d.toLocaleDateString("en-GB", withYear ? { month: "short", year: "numeric" } : { day: "numeric", month: "short" });
  return `${f(from)} – ${f(to)}`;
}
