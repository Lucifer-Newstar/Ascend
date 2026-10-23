/**
 * The missed-day reason (v1.2 streak rule): when yesterday was missed, the trainer asks
 * why. A reason given today keeps the streak; two missed days in a row, or no reason,
 * reset it. Quick picks plus your own words; it stays on your machine.
 */
import type { StreakInfo } from "@ascend/shared";
import { useState } from "react";

import { api } from "../api/client";
import { useToast } from "./Toast";
import { TrainerSays, useTrainerOn } from "./Trainer";

export const QUICK_REASONS = ["Sick", "Exams or college", "Work", "Travel", "Rest day", "Family"];

export function dayName(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { weekday: "long" });
}

export function StreakReasonCard({ streak, onSaved }: { streak: StreakInfo; onSaved: () => void }) {
  const trainer = useTrainerOn();
  const toast = useToast();
  const [other, setOther] = useState("");
  const [busy, setBusy] = useState(false);
  if (!streak.reason_due) return null;
  const due = streak.reason_due;

  async function give(reason: string) {
    if (!reason.trim()) return;
    setBusy(true);
    try {
      const s = await api.streakReason(due, reason.trim());
      toast(`Streak kept: ${s.current} day${s.current === 1 ? "" : "s"}`, "info");
      onSaved();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  const ask = `You missed ${dayName(due)}. What happened? Tell me today and your ${streak.current}-day streak stays.`;
  return (
    <section className="card p-5" aria-labelledby="reason-title" data-testid="streak-reason">
      <h2 id="reason-title" className="card-title mb-3">Missed a day</h2>
      {trainer ? (
        <TrainerSays mood="warning" size={48}><p className="text-sm text-ink">{ask}</p></TrainerSays>
      ) : (
        <p className="text-sm text-ink">{ask}</p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {QUICK_REASONS.map((r) => (
          <button key={r} type="button" className="chip hover:border-accent hover:text-ink" disabled={busy} onClick={() => void give(r)}>{r}</button>
        ))}
      </div>
      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); void give(other); }}>
        <input className="input flex-1" aria-label="Your reason" placeholder="Or in your own words" maxLength={120} value={other} onChange={(e) => setOther(e.target.value)} />
        <button type="submit" className="btn-primary" disabled={busy || !other.trim()}>Keep my streak</button>
      </form>
      <p className="mt-2 text-[11px] text-muted">Two missed days in a row, or no reason by tonight, reset the streak.</p>
    </section>
  );
}
