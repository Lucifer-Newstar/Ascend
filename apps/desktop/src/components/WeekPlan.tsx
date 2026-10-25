/**
 * The week plan (v1.4, schedule-v1): this week planned vs done, the coming sessions on your
 * training days, and a plan-the-week step for next week (best done on Sunday). Planned rest
 * days are shown as rest, never as missed.
 */
import type { WeekPlan as Week } from "@ascend/shared";
import { useState } from "react";

import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import { WEEKDAY_LONG, WEEKDAY_SHORT } from "./ScheduleEditor";
import { useToast } from "./Toast";

const isoDay = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/** The Monday after the week that starts on `weekStart` (local dates, "YYYY-MM-DD"). */
export function nextMonday(weekStart: string): string {
  const [y, m, d] = weekStart.split("-").map(Number);
  return isoDay(new Date(y, m - 1, d + 7));
}

function dayState(d: Week["days"][number]): { label: string; tone: string } {
  if (d.done) return { label: d.planned ? "Done" : "Extra", tone: "border-accent bg-accent/15 text-ink" };
  if (!d.planned) return { label: "Rest", tone: "border-line text-muted" };
  if (d.past) return { label: "Not logged", tone: "border-line-2 text-muted" };
  return { label: d.session ?? "Training", tone: "border-line-2 text-ink" };
}

export function WeekRow({ week }: { week: Week }) {
  return (
    <ol className="grid grid-cols-7 gap-2" aria-label={`Week of ${week.week_start}`}>
      {week.days.map((d) => {
        const s = dayState(d);
        return (
          <li key={d.day} className={`rounded-md border p-2 text-center text-xs ${s.tone} ${d.today ? "ring-2 ring-accent" : ""}`}
            aria-label={`${WEEKDAY_LONG[d.weekday]}: ${s.label}`} data-testid={`week-day-${d.weekday}`}>
            <div className="font-display font-semibold uppercase tracking-[0.06em]">{WEEKDAY_SHORT[d.weekday]}</div>
            <div className="mt-1 truncate" title={s.label}>{s.label}</div>
          </li>
        );
      })}
    </ol>
  );
}

export function WeekPlanPanel({ refreshKey = 0 }: { refreshKey?: number }) {
  const toast = useToast();
  const week = useApi(() => api.week(), [refreshKey], { cacheKey: "week" });
  const [next, setNext] = useState<number[] | null>(null);
  const [busy, setBusy] = useState(false);
  const w = week.data;

  async function save() {
    if (!w || !next) return;
    setBusy(true);
    try {
      const saved = await api.planWeek(nextMonday(w.week_start), next);
      toast(`Next week: ${saved.planned} training day${saved.planned === 1 ? "" : "s"} planned`, "info");
      setNext(null);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card p-5" aria-labelledby="week-plan-title" data-testid="week-plan">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="week-plan-title" className="card-title">This week</h2>
        {w && <span className="text-sm text-muted" data-testid="week-count">{w.done} of {w.planned} planned sessions done</span>}
      </div>
      {!w ? (
        <p className="text-sm text-muted">{week.loading ? "Loading…" : week.error ?? "No week yet."}</p>
      ) : (
        <>
          <WeekRow week={w} />
          {w.source === "none" && <p className="mt-2 text-xs text-muted">Pick your training days in Settings &gt; Trainer, or follow a program, to plan your week.</p>}
          {next === null ? (
            <button type="button" className="btn-ghost mt-4" onClick={() => setNext(w.days.filter((d) => d.planned).map((d) => d.weekday))}>
              Plan next week
            </button>
          ) : (
            <div className="mt-4 space-y-3 border-t border-line pt-3" data-testid="plan-next-week">
              <p className="text-sm text-ink">Which days will you train next week?</p>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Next week's training days">
                {WEEKDAY_SHORT.map((label, d) => (
                  <button key={label} type="button" aria-pressed={next.includes(d)} aria-label={`Next ${WEEKDAY_LONG[d]}`}
                    className={`rounded-md border px-3 py-1.5 text-sm ${next.includes(d) ? "border-accent bg-accent/15 text-ink" : "border-line-2 text-muted"}`}
                    onClick={() => setNext((x) => (x!.includes(d) ? x!.filter((y) => y !== d) : [...x!, d].sort()))}>
                    {label}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <button type="button" className="btn-primary" disabled={busy} onClick={() => void save()}>
                  {busy ? "Saving…" : `Plan ${next.length} day${next.length === 1 ? "" : "s"}`}
                </button>
                <button type="button" className="btn-ghost" onClick={() => setNext(null)}>Cancel</button>
              </div>
              <p className="text-[11px] text-muted">Days you leave out are planned rest: they keep your streak as it is.</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
