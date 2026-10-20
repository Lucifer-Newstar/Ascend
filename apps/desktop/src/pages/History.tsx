import type { Units, WorkoutSet } from "@ascend/shared";

import { api } from "../api/client";
import { IconTrophy } from "../components/Icons";
import type { Page } from "../components/Layout";
import { LoadingLayout, SkeletonCard } from "../components/Skeleton";
import { ErrorState, StaleNotice } from "../components/States";
import { dayLabel, kcal, timeLabel } from "../lib/format";
import { usePrefs } from "../lib/prefs";
import { formatDistance, formatDuration, toDisplayWeight, weightUnit } from "../lib/units";
import { isOffline, useApi } from "../lib/useApi";

export function HistoryPage({ refreshKey, onNavigate }: { refreshKey: number; onNavigate: (p: Page) => void }) {
  const { data, error, status, loading, reload } = useApi(() => api.history(30), [refreshKey]);
  const { settings } = usePrefs();
  if (loading && !data) {
    return (
      <LoadingLayout label="Loading history…">
        <div className="max-w-4xl space-y-4">{[0, 1, 2].map((i) => <SkeletonCard key={i} lines={3} />)}</div>
      </LoadingLayout>
    );
  }
  if (!data) return <ErrorState message={error ?? "No data"} onRetry={reload} offline={isOffline(status)} />;
  if (data.length === 0) {
    return (
      <div className="card max-w-3xl p-8 text-center">
        <h2 className="text-base font-semibold text-ink">Nothing logged in the last 30 days</h2>
        <p className="mt-1 text-sm text-muted">Workouts and meals appear here, grouped by day.</p>
        <div className="mt-5 flex justify-center gap-3">
          <button type="button" className="btn-primary" onClick={() => onNavigate("workout")}>Log a workout</button>
          <button type="button" className="btn-ghost" onClick={() => onNavigate("diet")}>Log a meal</button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-4">
      {error && <StaleNotice message={error} onRetry={reload} />}
      {data.map((d) => (
        <section key={d.day} className="card p-5">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-sm font-semibold text-ink">{dayLabel(d.day)} <span className="ml-2 text-xs font-normal text-faint">{d.day}</span></h2>
            <span className="text-xs text-muted">{d.sets} sets · {kcal(d.kcal_in)} kcal eaten · <span className="text-xp">+{d.xp} XP</span></span>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="mb-1.5 text-[11px] uppercase tracking-wider text-faint">Workouts</div>
              {d.workouts.length === 0 ? <p className="text-xs text-faint">Rest day</p> : d.workouts.map((w) => (
                <ul key={w.id} className="space-y-1 text-sm">
                  {summarise(w.sets, settings.units).map((row) => (
                    <li key={row.name} className="flex justify-between gap-2">
                      <span className="text-ink">{row.name}{row.pr && <IconTrophy className="ml-1.5 inline text-warn" width={13} height={13} />}</span>
                      <span className="text-muted">{row.sets} × {row.best}</span>
                    </li>
                  ))}
                </ul>
              ))}
            </div>
            <div>
              <div className="mb-1.5 text-[11px] uppercase tracking-wider text-faint">Meals</div>
              {d.meals.length === 0 ? <p className="text-xs text-faint">No meals logged</p> : (
                <ul className="space-y-1 text-sm">
                  {d.meals.map((m) => (
                    <li key={m.id} className="flex justify-between gap-2">
                      <span className="truncate text-ink"><span className="capitalize text-muted">{m.meal_type}</span> · {m.items.map((i) => i.food_name).join(", ")}</span>
                      <span className="shrink-0 text-muted">{timeLabel(m.logged_at)} · {kcal(m.kcal)} kcal</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>
      ))}
    </div>
  );
}

/** One line per exercise: set count and the best set, in the user's units. */
export function summarise(sets: WorkoutSet[], units: Units) {
  const map = new Map<string, { name: string; sets: number; best: string; top: number; pr: boolean }>();
  for (const s of sets) {
    const row = map.get(s.exercise_name) ?? { name: s.exercise_name, sets: 0, best: "", top: -1, pr: false };
    row.sets += 1;
    row.pr ||= s.is_pr;
    // Timed sets rank by duration, lifts by weight, bodyweight by reps.
    const score = s.duration_s ? s.duration_s : s.weight_kg > 0 ? s.weight_kg : s.reps;
    if (score > row.top) {
      row.top = score;
      row.best = s.duration_s
        ? `${formatDuration(s.duration_s)}${s.distance_m ? ` · ${formatDistance(s.distance_m, units)}` : ""}`
        : s.weight_kg > 0
          ? `${toDisplayWeight(s.weight_kg, units)} ${weightUnit(units)} × ${s.reps}`
          : `${s.reps} reps`;
    }
    map.set(s.exercise_name, row);
  }
  return [...map.values()];
}
