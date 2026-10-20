/** Small pure helpers used across screens (unit-tested in format.test.ts). */

export function pct(value: number, target: number): number {
  if (target <= 0) return 0;
  return Math.max(0, Math.min(1, value / target));
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
  return d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}

export function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export function readyAtLabel(iso: string | null): string {
  if (!iso) return "ready now";
  const d = new Date(iso);
  return `ready ~${d.toLocaleDateString("en-GB", { weekday: "short" })} ${d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
}
