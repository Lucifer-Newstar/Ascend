/**
 * Theme art (v1.2), found by file name so a picture can be swapped without code changes:
 * assets/themes/theme-<theme>-<kind>.webp, kind = landing (the intro screen), bg (behind
 * every page) or event (level-up, boss, workout finish and the timer). Light and Dark,
 * the 1.1 looks, have no art and keep their plain backgrounds.
 */
import type { AppTheme } from "@ascend/shared";

import { isAppTheme, type Theme } from "./theme";

export type ArtKind = "landing" | "bg" | "event";

const art = import.meta.glob<string>("../assets/themes/*.webp", { eager: true, import: "default" });

export function themeArt(theme: Theme | AppTheme, kind: ArtKind): string | null {
  if (!isAppTheme(theme)) return null;
  return art[`../assets/themes/theme-${theme}-${kind}.webp`] ?? null;
}
