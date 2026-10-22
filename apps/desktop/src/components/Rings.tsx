import type { Ring } from "@ascend/shared";
import { useEffect, useState, type ReactNode } from "react";

import { kcal, pct } from "../lib/format";
import { CountUp, useReducedMotion } from "../lib/motion";

interface RingSpec {
  key: string;
  ring: Ring;
  color: string;
  display: ReactNode;
  unit: string;
}

/** Three concentric progress rings: quest tasks, kcal eaten, kcal burned. */
export function Rings({ tasks, kcalIn, kcalOut }: { tasks: Ring; kcalIn: Ring; kcalOut: Ring }) {
  const specs: RingSpec[] = [
    { key: "tasks", ring: tasks, color: "var(--color-ring-tasks)", display: <><CountUp value={tasks.value} />/{tasks.target}</>, unit: "tasks" },
    { key: "in", ring: kcalIn, color: "var(--color-ring-in)", display: <CountUp value={kcalIn.value} format={kcal} />, unit: `/ ${kcal(kcalIn.target)} kcal` },
    { key: "out", ring: kcalOut, color: "var(--color-ring-out)", display: <CountUp value={kcalOut.value} format={kcal} />, unit: `/ ${kcal(kcalOut.target)} kcal` },
  ];
  const size = 168;
  const stroke = 13;
  const gap = 4;
  const allDone = specs.every((s) => pct(s.ring.value, s.ring.target) >= 1);
  // Rings draw in from empty on first paint (Apple Fitness style); reduced motion starts full.
  const reduce = useReducedMotion();
  // No animation: drawn from the first render (derived, not set from an effect).
  const instant = reduce || typeof requestAnimationFrame !== "function";
  const [animated, setAnimated] = useState(false);
  const drawn = instant || animated;
  useEffect(() => {
    if (instant) return;
    const raf = requestAnimationFrame(() => setAnimated(true));
    return () => cancelAnimationFrame(raf);
  }, [instant]);

  return (
    <div className="flex items-center gap-6">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Daily rings"
        className={allDone ? "drop-shadow-[0_0_12px_rgba(34,211,238,0.45)]" : undefined}>
        {specs.map((s, i) => {
          const r = size / 2 - stroke / 2 - i * (stroke + gap);
          const c = 2 * Math.PI * r;
          const target = pct(s.ring.value, s.ring.target);
          const p = drawn ? target : 0;
          return (
            <g key={s.key} transform={`rotate(-90 ${size / 2} ${size / 2})`}>
              <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={s.color} strokeOpacity={0.14} strokeWidth={stroke} />
              {target > 0 && (
                <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={s.color} strokeWidth={stroke} strokeLinecap="round"
                  strokeDasharray={`${c * p} ${c}`} style={{ opacity: drawn ? 1 : 0, transition: "stroke-dasharray 900ms cubic-bezier(0.2, 0.7, 0.2, 1), opacity 150ms" }} />
              )}
            </g>
          );
        })}
      </svg>
      <ul className="space-y-3 text-sm">
        {specs.map((s) => (
          <li key={s.key} className="flex items-start gap-2.5">
            <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: s.color }} />
            <div>
              <div className="text-[11px] uppercase tracking-wider text-muted">
                {s.ring.label}
                {s.ring.is_estimate && <span className="ml-1 normal-case tracking-normal text-faint">(estimate)</span>}
              </div>
              <div className="font-semibold text-ink">
                {s.display} <span className="text-xs font-normal text-muted">{s.unit}</span>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
