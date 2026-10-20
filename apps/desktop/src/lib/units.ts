/**
 * Display units. The sidecar always stores kilograms, centimetres and metres;
 * conversion happens only at the edge of the UI.
 */
export type Units = "metric" | "imperial";

export const KG_PER_LB = 0.45359237;
export const CM_PER_IN = 2.54;
export const M_PER_MI = 1609.344;

const round = (v: number, dp: number) => Math.round(v * 10 ** dp) / 10 ** dp;

export function weightUnit(units: Units): "kg" | "lb" {
  return units === "imperial" ? "lb" : "kg";
}

/** kg -> number shown in an input or label. */
export function toDisplayWeight(kg: number, units: Units, dp = 1): number {
  return round(units === "imperial" ? kg / KG_PER_LB : kg, dp);
}

/** Number typed by the user -> kg sent to the sidecar. */
export function fromDisplayWeight(value: number, units: Units): number {
  return units === "imperial" ? round(value * KG_PER_LB, 3) : value;
}

export function formatWeight(kg: number, units: Units, dp = 1): string {
  return `${toDisplayWeight(kg, units, dp)} ${weightUnit(units)}`;
}

export function formatLength(cm: number, units: Units): string {
  return units === "imperial" ? `${round(cm / CM_PER_IN, 1)} in` : `${round(cm, 1)} cm`;
}

export function formatDistance(m: number, units: Units): string {
  return units === "imperial" ? `${round(m / M_PER_MI, 2)} mi` : `${round(m / 1000, 2)} km`;
}

/** Seconds -> "m:ss" or "h:mm:ss". */
export function formatDuration(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}

/** "25", "25:30" or "1:05:00" -> seconds; null when it can't be read. */
export function parseDuration(text: string): number | null {
  const parts = text.trim().split(":").map((p) => p.trim());
  if (!parts.length || parts.some((p) => p === "" || !/^\d+$/.test(p)) || parts.length > 3) return null;
  const nums = parts.map(Number);
  if (nums.length === 1) return nums[0] * 60; // a bare number means minutes
  if (nums.slice(1).some((n) => n >= 60)) return null;
  return nums.reduce((acc, n) => acc * 60 + n, 0);
}
