import { api } from "../api/client";
import { IconTrophy } from "../components/Icons";
import { Empty, ErrorState, Loading } from "../components/States";
import { dayLabel, kcal, timeLabel } from "../lib/format";
import { useApi } from "../lib/useApi";

export function HistoryPage({ refreshKey }: { refreshKey: number }) {
  const { data, error, loading, reload } = useApi(() => api.history(30), [refreshKey]);
  if (loading && !data) return <Loading label="Loading history…" />;
  if (error || !data) return <ErrorState message={error ?? "No data"} onRetry={reload} />;
  if (data.length === 0) return <div className="max-w-3xl"><Empty title="Nothing logged in the last 30 days." hint="Workouts and meals appear here, grouped by day." /></div>;

  return (
    <div className="max-w-4xl space-y-4">
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
                  {summarise(w.sets).map((row) => (
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
                      <span className="shrink-0 text-muted">{timeLabel(m.logged_at)} · {kcal(m.kcal)}</span>
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

function summarise(sets: { exercise_name: string; weight_kg: number; reps: number; is_pr: boolean }[]) {
  const map = new Map<string, { name: string; sets: number; best: string; top: number; pr: boolean }>();
  for (const s of sets) {
    const row = map.get(s.exercise_name) ?? { name: s.exercise_name, sets: 0, best: "", top: -1, pr: false };
    row.sets += 1;
    row.pr ||= s.is_pr;
    if (s.weight_kg > row.top) {
      row.top = s.weight_kg;
      row.best = s.weight_kg > 0 ? `${s.weight_kg} kg × ${s.reps}` : `${s.reps} reps`;
    }
    map.set(s.exercise_name, row);
  }
  return [...map.values()];
}
