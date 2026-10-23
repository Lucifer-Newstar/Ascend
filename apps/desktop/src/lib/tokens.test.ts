import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { READY_TOKEN, STATUS_TOKEN } from "./muscleMap";

/**
 * UI-1: every text token meets WCAG AA (4.5:1) against the background and all three
 * surfaces, in every theme (the two 1.1 looks and the five v1.2 themes). The values are read from index.css itself, so a token
 * change that breaks contrast fails here.
 */
const css = readFileSync(new URL("../index.css", import.meta.url), "utf8");

function block(startMarker: string): Record<string, string> {
  const start = css.indexOf(startMarker);
  if (start < 0) throw new Error(`no block ${startMarker}`);
  const body = css.slice(css.indexOf("{", start) + 1, css.indexOf("\n}", start));
  const out: Record<string, string> = {};
  for (const m of body.matchAll(/--color-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) out[m[1]] = m[2];
  return out;
}

const dark = block("@theme static");
const light = { ...dark, ...block(':root[data-theme="light"]') };
// v1.2 themes: each overrides the dark tokens it changes; the rest are inherited.
const APP = ["shadow", "crimson", "frost", "emerald", "solar"].map(
  (name) => [name, { ...dark, ...block(`:root[data-theme="${name}"]`) }] as [string, Record<string, string>],
);

function luminance(hex: string): number {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = c.map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

const SURFACES = ["bg", "panel", "panel-2", "panel-3"];
const TEXT = ["ink", "muted", "faint", "accent", "xp", "good", "warn", "bad", "under", "gold", "rank-e", "rank-d", "rank-c", "rank-b", "rank-a", "rank-s"];

describe.each([
  ["dark", dark],
  ["light", light],
  ...APP,
])("%s theme tokens", (_name, t) => {
  it.each(TEXT)("text token %s is at least 4.5:1 on every surface", (token) => {
    expect(t[token], token).toBeDefined();
    for (const s of SURFACES) expect(contrast(t[token], t[s]), `${token} on ${s}`).toBeGreaterThanOrEqual(4.5);
  });

  it("text on the accent (primary buttons) is at least 4.5:1", () => {
    expect(contrast(t["on-accent"], t.accent)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(t["on-accent"], t["accent-hover"])).toBeGreaterThanOrEqual(4.5);
  });

  it("input borders are at least 3:1 against panels (non-text contrast)", () => {
    for (const s of ["panel", "panel-2"]) expect(contrast(t["line-input"], t[s])).toBeGreaterThanOrEqual(3);
  });
});

describe("v1.2 theme art stays readable", () => {
  it("every theme has a scrim over its background art and solid cards", () => {
    expect(css).toMatch(/\.theme-art \{[^}]*linear-gradient\(180deg, color-mix\(in srgb, var\(--color-bg\) 45%/);
    expect(css).toMatch(/\.event-art \{[^}]*radial-gradient/);
    expect(css).toMatch(/\.event-title \{[^}]*text-shadow/);
    for (const [name, t] of APP) for (const s of ["panel", "panel-2", "panel-3"]) expect(t[s], `${name} ${s}`).toMatch(/^#[0-9a-f]{6}$/i);
  });
});

describe("status colours (UI-4)", () => {
  it("gives every muscle status its own token, never the System blue", () => {
    const tokens = Object.values(STATUS_TOKEN);
    expect(new Set(tokens).size).toBe(tokens.length);
    expect(tokens).not.toContain("--color-accent");
    expect(STATUS_TOKEN).toEqual({
      over: "--color-map-over",
      recovering: "--color-map-recovering",
      under: "--color-map-under",
      optimal: "--color-map-optimal",
      no_data: "--color-map-nodata",
    });
  });

  it("pulses ready muscles in the ready/recovered token, the same one the legend shows", () => {
    expect(READY_TOKEN).toBe("--color-map-optimal");
    expect(READY_TOKEN).toBe(STATUS_TOKEN.optimal);
  });
});
