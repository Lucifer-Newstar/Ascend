/**
 * Form for a timed set: a run, a boxing round, a stretch hold or a meditation sit.
 * Duration accepts minutes ("25"), m:ss or h:mm:ss. Distance and heart rate are
 * offered only where they mean something (cardio; HR also for martial arts).
 */
import type { Exercise, SetIn, Units } from "@ascend/shared";
import { useState } from "react";

import { M_PER_MI, formatDuration, parseDuration } from "../../lib/units";
import { RpeSelect } from "./fields";

export function TimedSetForm({
  exercise,
  units,
  busy,
  onSubmit,
  initialSeconds,
}: {
  exercise: Exercise;
  units: Units;
  busy?: boolean;
  onSubmit: (set: SetIn) => void;
  initialSeconds?: number;
}) {
  const section = exercise.section;
  const [duration, setDuration] = useState(initialSeconds ? formatDuration(initialSeconds) : defaultDuration(section));
  const [distance, setDistance] = useState("");
  const [hr, setHr] = useState("");
  const [rpe, setRpe] = useState<number | null>(section === "meditation" ? null : 7);
  const [error, setError] = useState<string | null>(null);
  const distanceUnit = units === "imperial" ? "mi" : "km";
  const showDistance = section === "cardio";
  const showHr = section === "cardio" || section === "martial_arts";

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const seconds = parseDuration(duration);
    if (!seconds) {
      setError("Enter a duration like 25, 3:00 or 1:05:00");
      return;
    }
    const km = distance.trim() ? Number(distance) : null;
    if (km !== null && (Number.isNaN(km) || km < 0)) {
      setError("Distance must be a positive number");
      return;
    }
    setError(null);
    onSubmit({
      exercise_id: exercise.id,
      duration_s: seconds,
      distance_m: km === null ? null : Math.round(units === "imperial" ? km * M_PER_MI : km * 1000),
      avg_hr: hr.trim() ? Math.round(Number(hr)) : null,
      rpe: section === "meditation" ? null : rpe,
    });
  }

  return (
    <form onSubmit={submit} className="space-y-2" aria-label={`Log ${exercise.name}`}>
      <div className="grid grid-cols-[1fr_1fr_1fr_auto] items-end gap-3">
        <label className="block">
          <span className="mb-1.5 block text-xs text-muted">Duration (min or m:ss)</span>
          <input className="input" value={duration} onChange={(e) => setDuration(e.target.value)} inputMode="numeric" />
        </label>
        {showDistance ? (
          <label className="block">
            <span className="mb-1.5 block text-xs text-muted">Distance ({distanceUnit})</span>
            <input className="input" value={distance} onChange={(e) => setDistance(e.target.value)} inputMode="decimal" placeholder="optional" />
          </label>
        ) : (
          <div />
        )}
        {section === "meditation" ? (
          <div />
        ) : (
          <RpeSelect value={rpe} onChange={setRpe} label={showHr ? "RPE (effort)" : "Intensity (RPE)"} />
        )}
        <button type="submit" className="btn-primary h-[38px] px-5" disabled={busy}>
          {section === "meditation" ? "Log sit" : "Log"}
        </button>
      </div>
      {showHr && (
        <label className="flex max-w-xs items-center gap-3">
          <span className="text-xs text-muted">Avg heart rate</span>
          <input className="input w-24" value={hr} onChange={(e) => setHr(e.target.value)} inputMode="numeric" placeholder="bpm" />
        </label>
      )}
      {error && <p role="alert" className="text-xs text-bad">{error}</p>}
    </form>
  );
}

function defaultDuration(section: string): string {
  if (section === "martial_arts") return "3:00";
  if (section === "flexibility") return "1:00";
  if (section === "meditation") return "10";
  return "30";
}
