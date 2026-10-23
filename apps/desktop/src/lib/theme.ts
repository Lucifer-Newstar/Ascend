/**
 * Theme handling. The user's preference is stored by the sidecar; this module resolves it
 * and applies it to <html>:
 *
 * - data-theme: the look, which switches the CSS tokens in index.css. "dark" and "light"
 *   are the 1.1 looks (kept as free themes; "system" follows Windows between them); the
 *   v1.2 themes (Shadow, Crimson Gate, Frost, Emerald, Solar Gold) each bring their own
 *   palette, card frames, button shape, icon tint, particles and art.
 * - data-tone: "dark" or "light", for code that needs literal colours (charts).
 * - data-art: the background art setting (on | dim | off).
 */
import type { AppTheme, BackgroundArt, ThemePref } from "@ascend/shared";

export type { ThemePref };
export type Theme = "dark" | "light" | AppTheme;
export type Tone = "dark" | "light";

/** The v1.2 themes, in the order the picker shows them. */
export const APP_THEMES: readonly AppTheme[] = ["shadow", "crimson", "frost", "emerald", "solar"];

export function isAppTheme(t: string): t is AppTheme {
  return (APP_THEMES as readonly string[]).includes(t);
}

export function resolveTheme(pref: ThemePref, systemPrefersLight: boolean): Theme {
  if (pref === "system") return systemPrefersLight ? "light" : "dark";
  return pref === "dark" || pref === "light" || isAppTheme(pref) ? pref : "dark";
}

/** Every v1.2 theme is a dark theme; only the 1.1 Light look is light. */
export function toneOf(theme: Theme): Tone {
  return theme === "light" ? "light" : "dark";
}

export function systemPrefersLight(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: light)").matches
    : false;
}

export function applyTheme(theme: Theme, root: HTMLElement = document.documentElement): void {
  root.dataset.theme = theme;
  root.dataset.tone = toneOf(theme);
}

export function applyBackgroundArt(mode: BackgroundArt, root: HTMLElement = document.documentElement): void {
  root.dataset.art = mode;
}

/**
 * Mirror Settings → "Reduce motion" onto <html data-motion>, so the CSS rules that
 * honour prefers-reduced-motion follow the in-app toggle too (see index.css).
 */
export function applyMotionPreference(reduce: boolean, root: HTMLElement = document.documentElement): void {
  root.dataset.motion = reduce ? "reduce" : "full";
}

/** Current value of a CSS custom property, for libraries that need literal colours. */
export function cssVar(name: string, fallback = ""): string {
  if (typeof document === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}
