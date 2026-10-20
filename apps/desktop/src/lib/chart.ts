/** Tiny chart maths for the hand-rolled SVG charts (no chart library needed). */

export type Scale = (v: number) => number;

export function linearScale([d0, d1]: [number, number], [r0, r1]: [number, number]): Scale {
  const span = d1 - d0 || 1;
  return (v: number) => r0 + ((v - d0) / span) * (r1 - r0);
}

/** Round step (1, 2 or 5 x 10^n) giving about `count` ticks spanning min..max. */
export function niceTicks(min: number, max: number, count = 4): number[] {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [];
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const raw = (max - min) / Math.max(1, count);
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag;
  const start = Math.floor(min / step) * step;
  const end = Math.ceil(max / step - 1e-9) * step; // the top tick always covers the largest value
  const ticks: number[] = [];
  for (let v = start; v <= end + step * 1e-9; v += step) ticks.push(Math.round(v * 1e6) / 1e6);
  return ticks;
}

/** SVG path "M x y L x y ..." through the points; gaps (null) start a new segment. */
export function linePath(points: ({ x: number; y: number } | null)[]): string {
  let d = "";
  let pen = false;
  for (const p of points) {
    if (!p) {
      pen = false;
      continue;
    }
    d += `${pen ? "L" : "M"}${p.x.toFixed(1)} ${p.y.toFixed(1)} `;
    pen = true;
  }
  return d.trim();
}

/** Padded [min, max] of the values, ignoring nulls. */
export function extent(values: (number | null | undefined)[], pad = 0.05): [number, number] | null {
  const v = values.filter((x): x is number => typeof x === "number" && Number.isFinite(x));
  if (!v.length) return null;
  const lo = Math.min(...v);
  const hi = Math.max(...v);
  const p = (hi - lo || Math.abs(hi) || 1) * pad;
  return [lo - p, hi + p];
}

/** Compact axis label: 1250 -> "1.3k". */
export function compact(v: number): string {
  if (Math.abs(v) >= 1000) return `${Math.round(v / 100) / 10}k`;
  return String(v);
}

/**
 * Whether the x-axis label at index i is drawn when showing every `every`-th label.
 * The last label is always drawn, so a regular label too close to it is skipped
 * (otherwise "18 Oct" and "19 Oct" print on top of each other at the right edge).
 */
export function showLabel(i: number, count: number, every: number): boolean {
  if (i === count - 1) return true;
  return i % every === 0 && count - 1 - i >= every;
}
