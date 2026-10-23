/**
 * The theme's background (v1.2): its art under a scrim plus a few slow particles (chains,
 * embers, snow, leaves or light rays, styled per theme in index.css). Purely decorative:
 * hidden from screen readers, never takes clicks, and off with Background art "Off" or
 * reduced motion (particles only).
 */
import { useMemo } from "react";

import { useAppTheme } from "../lib/prefs";
import { themeArt } from "../lib/themeArt";

const COUNT = 14;

/** Deterministic spread (no Math.random, so renders and tests are stable). */
function particles(n: number) {
  return Array.from({ length: n }, (_, i) => {
    const r = (i * 37) % 100;
    return { x: `${(i * 71) % 100}%`, d: `${-((i * 13) % 20)}s`, s: `${16 + (r % 14)}s` };
  });
}

export function ThemeAmbience() {
  const theme = useAppTheme();
  const bg = themeArt(theme, "bg");
  const dots = useMemo(() => particles(COUNT), []);
  if (!bg) return null;
  return (
    <>
      <div className="theme-art" aria-hidden="true" data-testid="theme-art" style={{ ["--theme-bg" as string]: `url("${bg}")` }} />
      <div className="theme-ambience" aria-hidden="true">
        {dots.map((p, i) => (
          <span key={i} style={{ ["--x" as string]: p.x, ["--d" as string]: p.d, ["--s" as string]: p.s }} />
        ))}
      </div>
    </>
  );
}
