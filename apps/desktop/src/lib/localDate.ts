/**
 * Dates on the PC's own clock (v1.4, rule: "local system date/time").
 *
 * `toISOString()` is UTC: in India anything before 05:30 got yesterday's date (a photo
 * taken at 01:00 was filed under the day before, and the weekly recap looked a day back).
 * Every YYYY-MM-DD the app makes comes from here; tests/rules check nothing else does.
 */
const pad = (n: number) => String(n).padStart(2, "0");

/** YYYY-MM-DD of `d` on the local clock. */
export function localDay(d: Date = new Date()): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** YYYY-MM-DD `n` calendar days before `now` on the local clock (safe across DST changes). */
export function localDaysAgo(n: number, now: Date = new Date()): string {
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - n, 12);
  return localDay(d);
}
