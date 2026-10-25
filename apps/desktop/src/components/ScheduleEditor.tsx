/**
 * Training schedule (v1.4, schedule-v1): pick the weekdays you train and, if you like, a
 * time. The other weekdays become planned rest (they never break the streak), reminders
 * wait for your time, and the week plan lines your sessions up on these days. The program
 * still decides what comes next; this only decides when.
 */
import type { Schedule } from "@ascend/shared";
import { useState } from "react";

import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import { useToast } from "./Toast";

export const WEEKDAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export const WEEKDAY_LONG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export function ScheduleEditor({ onSaved }: { onSaved?: (s: Schedule) => void }) {
  const toast = useToast();
  const sched = useApi(api.schedule, []);
  // Edits start from what is saved; until the first edit the saved values show.
  const [draftDays, setDays] = useState<number[] | null>(null);
  const [draftTime, setTime] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const days = draftDays ?? sched.data?.days ?? [];
  const time = draftTime ?? sched.data?.time ?? "";

  const toggle = (d: number) => setDays(days.includes(d) ? days.filter((y) => y !== d) : [...days, d].sort());

  async function save() {
    if (days.length === 0) return;
    setBusy(true);
    try {
      const s = await api.saveSchedule(days, time || null);
      toast(`Training days: ${s.label}${s.time ? ` at ${s.time}` : ""}`, "info");
      setDays(null);
      setTime(null);
      sched.reload();
      onSaved?.(s);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  const fromProgram = sched.data?.source === "program";
  return (
    <div className="space-y-3" data-testid="schedule-editor">
      <div>
        <span className="text-sm text-ink">Training days</span>
        <br />
        <span className="text-xs text-muted">
          {fromProgram ? "Suggested by your program until you pick your own. " : ""}
          The other days are planned rest: they never break your streak and get no reminders.
        </span>
      </div>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Training days">
        {WEEKDAY_SHORT.map((label, d) => (
          <button key={label} type="button" aria-pressed={days.includes(d)} aria-label={WEEKDAY_LONG[d]}
            className={`rounded-md border px-3 py-1.5 text-sm ${days.includes(d) ? "border-accent bg-accent/15 text-ink" : "border-line-2 text-muted"}`}
            onClick={() => toggle(d)}>
            {label}
          </button>
        ))}
      </div>
      <label className="flex items-center justify-between gap-4 text-sm text-ink">
        <span>
          Usual time
          <br />
          <span className="text-xs text-muted">Optional. Reminders wait until this time on a training day.</span>
        </span>
        <input type="time" className="input w-32" value={time} onChange={(e) => setTime(e.target.value)} aria-label="Usual training time" />
      </label>
      <button type="button" className="btn-primary" disabled={busy || days.length === 0} onClick={() => void save()}>
        {busy ? "Saving…" : `Save ${days.length} day${days.length === 1 ? "" : "s"} a week`}
      </button>
    </div>
  );
}
