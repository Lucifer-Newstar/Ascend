import type { Ring } from "@ascend/shared";

import { kcal, pct } from "../lib/format";

interface RingSpec {
  key: string;
  ring: Ring;
  color: string;
  display: string;
  unit: string;
}

/** Three concentric progress rings: quest tasks, kcal eaten, kcal burned. */
export function Rings({ tasks, kcalIn, kcalOut }: { tasks: Ring; kcalIn: Ring; kcalOut: Ring }) {
  const specs: RingSpec[] = [
    { key: "tasks", ring: tasks, color: "var(--color-ring-tasks)", display: `${tasks.value}/${tasks.target}`, unit: "tasks" },
    { key: "in", ring: kcalIn, color: "var(--color-ring-in)", display: kcal(kcalIn.value), unit: `/ ${kcal(kcalIn.target)} kcal` },
    { key: "out", ring: kcalOut, color: "var(--color-ring-out)", display: kcal(kcalOut.value), unit: `/ ${kcal(kcalOut.target)} kcal` },
  ];
  const size = 168;
  const stroke = 13;
  const gap = 4;
  const allDone = specs.every((s) => pct(s.ring.value, s.ring.target) >= 1);

  return (
    <div className="flex items-center gap-6">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Daily rings"
        className={allDone ? "drop-shadow-[0_0_12px_rgba(34,211,238,0.45)]" : undefined}>
        {specs.map((s, i) => {
          const r = size / 2 - stroke / 2 - i * (stroke + gap);
          const c = 2 * Math.PI * r;
          const p = pct(s.ring.value, s.ring.target);
          return (
            <g key={s.key} transform={`rotate(-90 ${size / 2} ${size / 2})`}>
              <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={s.color} strokeOpacity={0.14} strokeWidth={stroke} />
              <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={s.color} strokeWidth={stroke} strokeLinecap="round"
                strokeDasharray={`${c * p} ${c}`} style={{ transition: "stroke-dasharray 600ms ease" }} />
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
