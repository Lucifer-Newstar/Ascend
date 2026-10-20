import type { Exercise, Workout } from "@ascend/shared";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import { IconSearch, IconTimer, IconTrophy } from "../components/Icons";
import { Empty, ErrorState, Loading } from "../components/States";
import { useToast } from "../components/Toast";
import { sessionLoad } from "../lib/load";
import { useApi } from "../lib/useApi";

const MUSCLE_LABEL: Record<string, string> = {
  upper_chest: "Upper chest", lower_chest: "Chest", front_delts: "Front delts", side_delts: "Side delts",
  rear_delts: "Rear delts", biceps: "Biceps", triceps: "Triceps", forearms: "Forearms", traps: "Traps",
  lats: "Lats", rhomboids: "Mid-back", lower_back: "Lower back", abs: "Abs", obliques: "Obliques",
  glutes: "Glutes", quads: "Quads", hamstrings: "Hamstrings", adductors: "Adductors", calves: "Calves",
};
const REST_SECONDS = 90;
const RPE_OPTIONS = [6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10];

export function WorkoutPage({ onChanged }: { onChanged: () => void }) {
  const exercises = useApi(() => api.exercises(), []);
  const active = useApi(api.activeWorkout, []);
  const [query, setQuery] = useState("");
  const [workout, setWorkout] = useState<Workout | null>(null);
  const [selected, setSelected] = useState<Exercise | null>(null);
  const [weight, setWeight] = useState(40);
  const [reps, setReps] = useState(8);
  const [rpe, setRpe] = useState<number | null>(8);
  const [busy, setBusy] = useState(false);
  const [restLeft, setRestLeft] = useState(0);
  const toast = useToast();

  useEffect(() => {
    if (active.data !== undefined) setWorkout(active.data);
  }, [active.data]);

  useEffect(() => {
    if (restLeft <= 0) return;
    const t = setTimeout(() => setRestLeft((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [restLeft]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = exercises.data ?? [];
    return q ? list.filter((e) => e.name.toLowerCase().includes(q) || e.muscles.some((m) => (MUSCLE_LABEL[m.muscle] ?? m.muscle).toLowerCase().includes(q))) : list;
  }, [exercises.data, query]);

  if (exercises.loading && !exercises.data) return <Loading label="Loading exercise library…" />;
  if (exercises.error) return <ErrorState message={exercises.error} onRetry={exercises.reload} />;

  async function logSet() {
    if (!selected) return;
    setBusy(true);
    try {
      const w = workout ?? (await api.startWorkout());
      const res = await api.logSet(w.id, { exercise_id: selected.id, weight_kg: weight, reps, rpe });
      const fresh = await api.activeWorkout();
      setWorkout(fresh);
      setRestLeft(REST_SECONDS);
      if (res.set.is_pr) toast(`New PR! ${selected.name} e1RM ${res.set.e1rm} kg · +${res.xp_awarded} XP`, "pr");
      else toast(`Set logged · +${res.xp_awarded} XP`, "xp");
      onChanged();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    if (!workout) return;
    setBusy(true);
    try {
      const res = await api.finishWorkout(workout.id);
      toast(`Workout complete · ${res.hard_sets} hard sets · +${res.xp_awarded} XP`, "xp");
      setWorkout(null);
      setRestLeft(0);
      onChanged();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  const groups = groupSets(workout);
  const load = sessionLoad(workout, exercises.data ?? []);

  return (
    <div className="grid h-full grid-cols-12 gap-5">
      <section className="card col-span-12 flex min-h-0 flex-col lg:col-span-4">
        <div className="border-b border-line p-4">
          <h2 className="card-title mb-3">Exercise library</h2>
          <div className="relative">
            <IconSearch className="absolute left-3 top-2.5 text-faint" width={16} height={16} />
            <input className="input pl-9" placeholder="Search exercise or muscle…" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
        </div>
        <ul className="max-h-[calc(100vh-260px)] min-h-0 flex-1 overflow-y-auto p-2">
          {filtered.map((e) => (
            <li key={e.id}>
              <button type="button" onClick={() => setSelected(e)}
                className={`w-full rounded-lg px-3 py-2 text-left transition-colors ${selected?.id === e.id ? "bg-accent/10" : "hover:bg-panel-2"}`}>
                <div className={`text-sm ${selected?.id === e.id ? "text-accent" : "text-ink"}`}>{e.name}</div>
                <div className="mt-0.5 truncate text-xs text-faint">
                  {e.equipment} · {e.muscles.filter((m) => m.weight >= 1).map((m) => MUSCLE_LABEL[m.muscle] ?? m.muscle).join(", ")}
                </div>
              </button>
            </li>
          ))}
          {filtered.length === 0 && <li className="p-4 text-sm text-faint">No exercise matches “{query}”.</li>}
        </ul>
      </section>

      <section className="col-span-12 space-y-5 lg:col-span-8">
        <div className="card p-5">
          {selected ? (
            <>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-ink">{selected.name}</h2>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {selected.muscles.map((m) => (
                      <span key={m.muscle} className={`chip ${m.weight >= 1 ? "border-accent/40 text-accent" : ""}`}>
                        {MUSCLE_LABEL[m.muscle] ?? m.muscle} ×{m.weight}
                      </span>
                    ))}
                  </div>
                </div>
                <RestTimer seconds={restLeft} onSkip={() => setRestLeft(0)} />
              </div>
              <div className="mt-5 grid grid-cols-[1fr_1fr_1fr_auto] items-end gap-3">
                <NumberField label="Weight (kg)" value={weight} step={2.5} onChange={setWeight} />
                <NumberField label="Reps" value={reps} step={1} onChange={setReps} />
                <label className="block">
                  <span className="mb-1.5 block text-xs text-muted">RPE (effort)</span>
                  <select className="input" value={rpe ?? ""} onChange={(e) => setRpe(e.target.value ? Number(e.target.value) : null)}>
                    <option value="">not logged</option>
                    {RPE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </label>
                <button type="button" className="btn-primary h-[38px] px-5" onClick={logSet} disabled={busy}>Log set</button>
              </div>
              <p className="mt-2 text-[11px] text-faint">RPE 10 = no reps left in the tank, 8 = two left. PRs use the Epley e1RM formula (1–10 reps).</p>
            </>
          ) : (
            <Empty title="Pick an exercise from the library to start logging." hint="Sets are saved instantly. Your session starts with the first set." />
          )}
        </div>

        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="card-title">Current session</h2>
            {workout && (
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted">{workout.sets.length} sets · started {new Date(workout.started_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}</span>
                <button type="button" className="btn-ghost" onClick={finish} disabled={busy || workout.sets.length === 0}>Finish workout</button>
              </div>
            )}
          </div>
          {groups.length === 0 ? (
            <Empty title="No sets yet today." />
          ) : (
            <div className="space-y-4">
              {groups.map(([name, sets]) => (
                <div key={name}>
                  <div className="mb-1.5 text-sm font-medium text-ink">{name}</div>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-[11px] uppercase tracking-wider text-faint">
                        <th className="w-14 py-1 font-medium">Set</th><th className="font-medium">kg</th><th className="font-medium">Reps</th>
                        <th className="font-medium">RPE</th><th className="font-medium">e1RM</th><th className="w-24 font-medium" />
                      </tr>
                    </thead>
                    <tbody>
                      {sets.map((s, i) => (
                        <tr key={s.id} className="border-t border-line/70">
                          <td className="py-1.5 text-muted">{i + 1}</td>
                          <td className="text-ink">{s.weight_kg}</td>
                          <td className="text-ink">{s.reps}</td>
                          <td className="text-muted">{s.rpe ?? "–"}</td>
                          <td className="text-muted">{s.e1rm ? `${s.e1rm} kg` : "–"}</td>
                          <td>{s.is_pr && <span className="inline-flex items-center gap-1 rounded-md bg-warn/10 px-2 py-0.5 text-xs font-semibold text-warn"><IconTrophy width={12} height={12} /> PR</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}
        </div>

        {load.length > 0 && (
          <div className="card p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="card-title">This session's muscle load</h2>
              <span className="text-[11px] text-faint">effective sets = muscle weight × effort (RPE)</span>
            </div>
            <ul className="grid grid-cols-2 gap-x-6 gap-y-2">
              {load.map(([muscle, es]) => (
                <li key={muscle} className="flex items-center gap-3 text-xs">
                  <span className="w-24 shrink-0 text-muted">{MUSCLE_LABEL[muscle] ?? muscle}</span>
                  <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
                    <span className="block h-full rounded-full bg-accent" style={{ width: `${Math.min(100, (es / load[0][1]) * 100)}%` }} />
                  </span>
                  <span className="w-10 text-right text-ink">{es.toFixed(1)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}

function groupSets(w: Workout | null): [string, Workout["sets"]][] {
  if (!w) return [];
  const m = new Map<string, Workout["sets"]>();
  for (const s of w.sets) m.set(s.exercise_name, [...(m.get(s.exercise_name) ?? []), s]);
  return [...m.entries()];
}

function NumberField({ label, value, step, onChange }: { label: string; value: number; step: number; onChange: (n: number) => void }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs text-muted">{label}</span>
      <div className="flex">
        <button type="button" className="rounded-l-lg border border-r-0 border-line-2 bg-panel-2 px-3 text-muted hover:text-ink" onClick={() => onChange(Math.max(0, +(value - step).toFixed(1)))} aria-label={`decrease ${label}`}>−</button>
        <input className="input rounded-none text-center" type="number" value={value} step={step} onChange={(e) => onChange(Number(e.target.value))} />
        <button type="button" className="rounded-r-lg border border-l-0 border-line-2 bg-panel-2 px-3 text-muted hover:text-ink" onClick={() => onChange(+(value + step).toFixed(1))} aria-label={`increase ${label}`}>+</button>
      </div>
    </label>
  );
}

function RestTimer({ seconds, onSkip }: { seconds: number; onSkip: () => void }) {
  if (seconds <= 0) return <div className="flex items-center gap-1.5 text-xs text-faint"><IconTimer width={14} height={14} /> rest timer starts after a set</div>;
  const mm = Math.floor(seconds / 60);
  const ss = String(seconds % 60).padStart(2, "0");
  return (
    <div className="flex items-center gap-2 rounded-lg border border-accent/30 bg-accent/[0.06] px-3 py-1.5">
      <IconTimer width={16} height={16} className="text-accent" />
      <span className="font-display text-lg font-bold text-accent">{mm}:{ss}</span>
      <button type="button" className="text-xs text-muted hover:text-ink" onClick={onSkip}>skip</button>
    </div>
  );
}
