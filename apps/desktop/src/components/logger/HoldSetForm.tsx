/**
 * Form for an isometric hold (plank, L-sit, front lever...): seconds held, optional
 * added load, RPE. A built-in stopwatch can time the hold and log it on Stop.
 */
import type { Exercise, SetIn, Units } from "@ascend/shared";
import { type ReactNode, useEffect, useRef, useState } from "react";

import { fromDisplayWeight, weightUnit } from "../../lib/units";
import { NumberField, RpeSelect } from "./fields";

const PRESETS = [10, 20, 30, 45, 60];

export function HoldSetForm({ exercise, units, busy, onSubmit, children }: {
  exercise: Exercise;
  units: Units;
  busy: boolean;
  onSubmit: (body: SetIn) => void;
  /** Rendered next to the Log button (the "+N XP" float). */
  children?: ReactNode;
}) {
  const [seconds, setSeconds] = useState(20);
  const [added, setAdded] = useState(0);
  const [rpe, setRpe] = useState<number | null>(8);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const tick = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (tick.current) clearInterval(tick.current); }, []);

  const submit = (s: number) => {
    if (s < 1) return;
    onSubmit({ exercise_id: exercise.id, duration_s: Math.round(s), weight_kg: fromDisplayWeight(added, units), reps: 1, rpe });
  };

  function start() {
    const t0 = Date.now();
    setStartedAt(t0);
    setElapsed(0);
    tick.current = setInterval(() => setElapsed(Math.floor((Date.now() - t0) / 1000)), 250);
  }

  function stop() {
    if (tick.current) clearInterval(tick.current);
    tick.current = null;
    const s = startedAt ? Math.floor((Date.now() - startedAt) / 1000) : 0;
    setStartedAt(null);
    if (s >= 1) {
      setSeconds(s);
      submit(s);
    }
  }

  return (
    <div className="mt-5 space-y-3">
      <form className="grid grid-cols-[1fr_1fr_1fr_auto] items-end gap-3" aria-label={`Log a hold of ${exercise.name}`}
        onSubmit={(e) => { e.preventDefault(); if (!busy) submit(seconds); }}>
        <NumberField label="Hold (seconds)" value={seconds} step={5} onChange={setSeconds} />
        <NumberField label={`Added load (${weightUnit(units)})`} value={added} step={units === "imperial" ? 5 : 2.5} onChange={setAdded} />
        <RpeSelect value={rpe} onChange={setRpe} />
        <span className="relative">
          <button type="submit" className="btn-primary h-[38px] px-5 transition-transform active:scale-95" disabled={busy || seconds < 1}>Log hold</button>
          {children}
        </span>
      </form>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider text-faint">Quick</span>
        {PRESETS.map((p) => (
          <button key={p} type="button" className={`chip ${seconds === p ? "border-accent/50 text-accent" : ""}`} aria-pressed={seconds === p} onClick={() => setSeconds(p)}>{p} s</button>
        ))}
        <span className="mx-1 h-4 w-px bg-line" aria-hidden />
        {startedAt === null ? (
          <button type="button" className="btn-ghost py-1 text-xs" onClick={start} disabled={busy}>Start timer</button>
        ) : (
          <>
            <span role="timer" aria-label="Seconds held" className="font-display text-xl font-bold tabular-nums text-accent">{elapsed}s</span>
            <button type="button" className="btn-primary py-1 text-xs" onClick={stop}>Stop &amp; log</button>
          </>
        )}
      </div>
      <p className="text-[11px] text-faint">Log only the seconds you held with good form. The longest hold is your PR; added load is shown with it.</p>
    </div>
  );
}
