/**
 * Motion preferences and small animation helpers.
 *
 * Motion is reduced when EITHER the OS asks for it (Windows: Settings →
 * Accessibility → Visual effects → Animation effects off, i.e.
 * prefers-reduced-motion) OR the user turned on Settings → "Reduce motion".
 * CSS covers both through the media query and :root[data-motion="reduce"]
 * (see index.css); components that animate from script (count-ups, tilt,
 * celebrations) ask useReducedMotion().
 *
 * Everything animated here moves with transform/opacity only, so it stays on the
 * compositor and does not trigger layout.
 */
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { num } from "./format";
import { useOptionalPrefs } from "./prefs";

const QUERY = "(prefers-reduced-motion: reduce)";

function canMatch(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function";
}

function subscribe(onChange: () => void): () => void {
  if (!canMatch()) return () => {};
  const mq = window.matchMedia(QUERY);
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
}

const osSnapshot = () => canMatch() && window.matchMedia(QUERY).matches;

/** The OS-level prefers-reduced-motion setting, live. */
export function useOsReducedMotion(): boolean {
  return useSyncExternalStore(subscribe, osSnapshot, () => false);
}

/** True when animations should be skipped (OS setting or the in-app toggle). */
export function useReducedMotion(): boolean {
  const prefs = useOptionalPrefs();
  const os = useOsReducedMotion();
  return os || Boolean(prefs?.settings.reduce_motion);
}

export const easeOutCubic = (k: number) => 1 - Math.pow(1 - k, 3);

/**
 * Animate a number towards `target` (from 0 on first mount, then from the value
 * currently shown). With reduced motion the target is returned straight away.
 */
export function useCountUp(target: number, duration = 700): number {
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(() => (reduce ? target : 0));
  const shownRef = useRef(shown);
  shownRef.current = shown;

  useEffect(() => {
    if (reduce || typeof requestAnimationFrame !== "function") {
      setShown(target);
      return;
    }
    const from = shownRef.current;
    if (from === target) return;
    const start = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const k = Math.min(1, (now - start) / duration);
      setShown(k >= 1 ? target : from + (target - from) * easeOutCubic(k));
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, reduce, duration]);

  return shown;
}

const defaultFormat = num;

/**
 * A number that counts up to its value. Screen readers get the final value
 * only (the ticking digits are hidden from them).
 */
export function CountUp({ value, format = defaultFormat, duration }: { value: number; format?: (n: number) => string; duration?: number }) {
  const shown = useCountUp(value, duration);
  return (
    <>
      <span aria-hidden="true" data-testid="count-up">{format(shown)}</span>
      <span className="sr-only">{format(value)}</span>
    </>
  );
}
