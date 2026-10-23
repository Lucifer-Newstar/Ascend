/**
 * Today's workout (v1.2, on Today): the next session of the program the player follows,
 * with a Start button, or a nudge to pick a program that fits their kit.
 */
import { api } from "../api/client";
import type { Page } from "./Layout";
import { planTarget } from "./ProgramCard";
import { useApi } from "../lib/useApi";

export function TodayWorkout({ refreshKey = 0, onNavigate }: { refreshKey?: number; onNavigate?: (p: Page) => void }) {
  const plan = useApi(api.currentPlan, [refreshKey], { cacheKey: "plan" });
  const p = plan.data;
  return (
    <section className="card card-hover p-5" aria-labelledby="today-workout-title" data-testid="today-workout">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 id="today-workout-title" className="card-title">Today&apos;s workout</h2>
        {p && <span className="text-xs text-muted">{p.name}</span>}
      </div>
      {plan.loading && p === undefined ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : p ? (
        <>
          <p className="text-h3 text-ink">{p.next.name}</p>
          <p className="text-xs text-muted">{p.next.focus} · {p.next.items.length} exercises</p>
          <ul className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
            {p.next.items.slice(0, 6).map((it) => (
              <li key={it.exercise} className="flex justify-between gap-3">
                <span className="truncate text-ink">{it.exercise}</span>
                <span className="shrink-0 text-xs text-muted">{planTarget(it)}</span>
              </li>
            ))}
          </ul>
          {onNavigate && <button type="button" className="btn-primary mt-4" onClick={() => onNavigate("workout")}>Start workout</button>}
        </>
      ) : (
        <>
          <p className="text-sm text-ink">No program yet.</p>
          <p className="text-xs text-muted">Pick one that fits your kit on Train; your trainer then lays out each day for you.</p>
          {onNavigate && <button type="button" className="btn-primary mt-4" onClick={() => onNavigate("workout")}>Pick a program</button>}
        </>
      )}
    </section>
  );
}
