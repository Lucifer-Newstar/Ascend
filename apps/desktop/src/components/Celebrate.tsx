/**
 * Small celebrations: a confetti burst and a soft flash, both decoration only
 * (aria-hidden, .motion-decor so reduced motion hides them). Particles move with
 * transform/opacity and unmount when done. Positions are fixed per index, not
 * random, so renders stay pure and screenshots are repeatable.
 */
import { useEffect, useRef, useState, type CSSProperties } from "react";

import { useReducedMotion } from "../lib/motion";

const COLORS = ["var(--color-xp)", "var(--color-accent)", "var(--color-warn)", "var(--color-good)"];

export function Confetti({ pieces = 14, spread = 70, duration = 900 }: { pieces?: number; spread?: number; duration?: number }) {
  if (useReducedMotion()) return null;
  return (
    <span aria-hidden="true" className="motion-decor pointer-events-none absolute inset-0 grid place-items-center overflow-visible" data-testid="confetti">
      {Array.from({ length: pieces }, (_, i) => {
        const angle = (i / pieces) * Math.PI * 2 + (i % 2 ? 0.2 : -0.1);
        const dist = spread * (0.65 + ((i * 37) % 10) / 28);
        const style = {
          "--dx": `${Math.cos(angle) * dist}px`,
          "--dy": `${Math.sin(angle) * dist - 12}px`,
          "--rot": `${(i % 2 ? 1 : -1) * (120 + i * 25)}deg`,
          background: COLORS[i % COLORS.length],
          animation: `asc-confetti ${duration}ms cubic-bezier(0.15, 0.7, 0.3, 1) both`,
          animationDelay: `${(i % 3) * 30}ms`,
        } as CSSProperties;
        return <span key={i} className={`absolute ${i % 3 === 0 ? "h-1.5 w-1.5 rounded-full" : "h-2 w-1 rounded-sm"}`} style={style} />;
      })}
    </span>
  );
}

export function Flash({ className = "" }: { className?: string }) {
  if (useReducedMotion()) return null;
  return (
    <span
      aria-hidden="true"
      className={`motion-decor pointer-events-none absolute inset-0 rounded-[inherit] ${className}`}
      style={{
        background: "radial-gradient(circle at 30% 50%, color-mix(in srgb, var(--color-xp) 35%, transparent), transparent 70%)",
        animation: "asc-flash 900ms ease-out both",
      }}
    />
  );
}

/**
 * Remembers the last value seen and reports when it went up. Returns a key that
 * changes on each rise (use it to replay an animation) and the size of the rise.
 * The first value seen is a baseline, not a rise.
 */
export function useRise(value: number | undefined): { riseKey: number; delta: number } {
  const prev = useRef<number | undefined>(undefined);
  const [state, setState] = useState({ riseKey: 0, delta: 0 });
  useEffect(() => {
    if (value === undefined) return;
    const before = prev.current;
    prev.current = value;
    if (before !== undefined && value > before) setState((s) => ({ riseKey: s.riseKey + 1, delta: value - before }));
  }, [value]);
  return state;
}

/** Shows `children` for `ms` after each change of `trigger` (0 = never shown). */
export function Transient({ trigger, ms = 1400, children }: { trigger: number; ms?: number; children: React.ReactNode }) {
  const [shown, setShown] = useState(0);
  const reduce = useReducedMotion();
  useEffect(() => {
    if (!trigger) return;
    setShown(trigger);
    const t = setTimeout(() => setShown(0), reduce ? Math.min(ms, 2500) : ms);
    return () => clearTimeout(t);
  }, [trigger, ms, reduce]);
  return shown ? <>{children}</> : null;
}
