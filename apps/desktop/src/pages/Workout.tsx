import type { Exercise, Section, SetIn, SetPatch, Workout, WorkoutSet } from "@ascend/shared";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import { IconSearch, IconTrophy } from "../components/Icons";
import { NumberField, RestTimer, RPE_OPTIONS, RpeSelect } from "../components/logger/fields";
import { SECTIONS, SectionTabs } from "../components/logger/SectionTabs";
import { TimedSetForm } from "../components/logger/TimedSetForm";
import { Empty, ErrorState, Loading } from "../components/States";
import { useToast } from "../components/Toast";
import { count } from "../lib/format";
import { sessionLoad } from "../lib/load";
import { MUSCLE_LABEL } from "../lib/muscles";
import { usePrefs } from "../lib/prefs";
import { formatDistance, formatDuration, fromDisplayWeight, parseDuration, toDisplayWeight, weightUnit } from "../lib/units";
import { useApi } from "../lib/useApi";

const REST_SECONDS = 90;

export function WorkoutPage({ onChanged }: { onChanged: () => void }) {
  const [section, setSection] = useState<Section>("gym");
  const exercises = useApi(() => api.exercises("", section), [section]);
  const active = useApi(api.activeWorkout, []);
  const { settings } = usePrefs();
  const units = settings.units;
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

  if (exercises.error) return <ErrorState message={exercises.error} onRetry={exercises.reload} />;

  function changeSection(s: Section) {
    setSection(s);
    setSelected(null);
    setQuery("");
  }

  async function logSet(body?: SetIn) {
    if (!selected) return;
    setBusy(true);
    try {
      const w = workout ?? (await api.startWorkout(section));
      const payload = body ?? { exercise_id: selected.id, weight_kg: fromDisplayWeight(weight, units), reps, rpe };
      const res = await api.logSet(w.id, payload);
      const fresh = await api.activeWorkout();
      setWorkout(fresh);
      if (!selected.time_based) setRestLeft(REST_SECONDS);
      if (res.set.is_pr) toast(`New PR! ${selected.name} e1RM ${toDisplayWeight(res.set.e1rm ?? 0, units)} ${weightUnit(units)} · +${res.xp_awarded} XP`, "pr");
      else toast(`${selected.time_based ? formatDuration(res.set.duration_s ?? 0) + " logged" : "Set logged"} · +${res.xp_awarded} XP`, "xp");
      onChanged();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function refreshSession() {
    setWorkout(await api.activeWorkout());
    onChanged();
  }

  async function editSet(s: WorkoutSet, patch: SetPatch) {
    if (!workout) return;
    setBusy(true);
    try {
      const updated = await api.editSet(workout.id, s.id, patch);
      await refreshSession();
      toast(updated.is_pr ? "Set updated · still a PR" : "Set updated", "info");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function deleteSet(s: WorkoutSet) {
    if (!workout) return;
    setBusy(true);
    try {
      await api.deleteSet(workout.id, s.id);
      await refreshSession();
      toast("Set deleted", "info");
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
      toast(`Workout complete · ${count(res.hard_sets, "hard set")} · +${res.xp_awarded} XP`, "xp");
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

  const sectionLabel = SECTIONS.find((s) => s.id === section)?.label ?? "Gym";

  return (
    <div className="space-y-5">
    <SectionTabs value={section} onChange={changeSection} />
    <div className="grid h-full grid-cols-12 gap-5">
      <section className="card col-span-12 flex min-h-0 flex-col lg:col-span-4">
        <div className="border-b border-line p-4">
          <h2 className="card-title mb-3">{sectionLabel} library</h2>
          <div className="relative">
            <IconSearch className="absolute left-3 top-2.5 text-faint" width={16} height={16} />
            <input className="input pl-9" aria-label="Search exercises" placeholder="Search exercise or muscle…" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
        </div>
        <ul className="max-h-[calc(100vh-320px)] min-h-0 flex-1 overflow-y-auto p-2" aria-busy={exercises.loading}>
          {exercises.loading && !exercises.data && <li><Loading label="Loading exercises…" /></li>}
          {filtered.map((e) => (
            <li key={e.id}>
              <button type="button" onClick={() => setSelected(e)}
                className={`w-full rounded-lg px-3 py-2 text-left transition-colors ${selected?.id === e.id ? "bg-accent/10" : "hover:bg-panel-2"}`}>
                <div className={`text-sm ${selected?.id === e.id ? "text-accent" : "text-ink"}`}>{e.name}</div>
                <div className={`mt-0.5 truncate text-xs ${selected?.id === e.id ? "text-muted" : "text-faint"}`}>
                  {e.equipment}
                  {e.muscles.some((m) => m.weight >= 1) && ` · ${e.muscles.filter((m) => m.weight >= 1).map((m) => MUSCLE_LABEL[m.muscle] ?? m.muscle).join(", ")}`}
                  {e.time_based && e.met ? ` · MET ${e.met}` : ""}
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
                {!selected.time_based && <RestTimer seconds={restLeft} onSkip={() => setRestLeft(0)} />}
              </div>
              {selected.time_based ? (
                <div className="mt-5">
                  <TimedSetForm key={selected.id} exercise={selected} units={units} busy={busy} onSubmit={(s) => logSet(s)} />
                  <p className="mt-2 text-[11px] text-faint">
                    Calories use the activity's MET value ({selected.met ?? "n/a"}) × your weight × time, an estimate.
                    {selected.muscles.length === 0 && " Stretching and meditation add no muscle load."}
                  </p>
                </div>
              ) : (
                <>
                  {/* A real form, so Enter in any field logs the set. */}
                  <form
                    className="mt-5 grid grid-cols-[1fr_1fr_1fr_auto] items-end gap-3"
                    aria-label={`Log a set of ${selected.name}`}
                    onSubmit={(e) => { e.preventDefault(); if (!busy) void logSet(); }}
                  >
                    <NumberField label={`Weight (${weightUnit(units)})`} value={weight} step={units === "imperial" ? 5 : 2.5} onChange={setWeight} />
                    <NumberField label="Reps" value={reps} step={1} onChange={setReps} />
                    <RpeSelect value={rpe} onChange={setRpe} />
                    <button type="submit" className="btn-primary h-[38px] px-5" disabled={busy}>Log set</button>
                  </form>
                  <p className="mt-2 text-[11px] text-faint">RPE 10 = no reps left in the tank, 8 = two left. PRs use the Epley e1RM formula (1–10 reps).</p>
                </>
              )}
            </>
          ) : (
            <Empty title={`Pick a ${sectionLabel.toLowerCase()} exercise from the library to start logging.`} hint="Sets are saved instantly. Your session starts with the first set." />
          )}
        </div>

        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="card-title">Current session</h2>
            {workout && (
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted">{count(workout.sets.length, "set")} · started {new Date(workout.started_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}</span>
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
                  <SetTable sets={sets} units={units} onEdit={editSet} onDelete={deleteSet} busy={busy} />
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
    </div>
  );
}

function SetTable({ sets, units, onEdit, onDelete, busy }: {
  sets: WorkoutSet[];
  units: "metric" | "imperial";
  onEdit: (s: WorkoutSet, patch: SetPatch) => void;
  onDelete: (s: WorkoutSet) => void;
  busy: boolean;
}) {
  const timed = sets.some((s) => s.duration_s !== null);
  const [editing, setEditing] = useState<number | null>(null);
  const [confirming, setConfirming] = useState<number | null>(null);
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-[11px] uppercase tracking-wider text-faint">
          {timed ? (
            <>
              <th className="w-14 py-1 font-medium">#</th><th className="font-medium">Time</th><th className="font-medium">Distance</th>
              <th className="font-medium">Avg HR</th><th className="font-medium">RPE</th><th><span className="sr-only">Actions</span></th>
            </>
          ) : (
            <>
              <th className="w-14 py-1 font-medium">Set</th><th className="font-medium">{weightUnit(units)}</th><th className="font-medium">Reps</th>
              <th className="font-medium">RPE</th><th className="font-medium">e1RM</th><th className="w-24 font-medium"><span className="sr-only">Personal record</span></th><th><span className="sr-only">Actions</span></th>
            </>
          )}
        </tr>
      </thead>
      <tbody>
        {sets.map((s, i) => editing === s.id ? (
          <EditRow key={s.id} index={i} set={s} timed={timed} units={units} busy={busy}
            onCancel={() => setEditing(null)}
            onSave={(patch) => { onEdit(s, patch); setEditing(null); }} />
        ) : (
          <tr key={s.id} className="group border-t border-line/70">
            <td className="py-1.5 text-muted">{i + 1}</td>
            {timed ? (
              <>
                <td className="text-ink">{formatDuration(s.duration_s ?? 0)}</td>
                <td className="text-ink">{s.distance_m ? formatDistance(s.distance_m, units) : "–"}</td>
                <td className="text-muted">{s.avg_hr ?? "–"}</td>
                <td className="text-muted">{s.rpe ?? "–"}</td>
              </>
            ) : (
              <>
                <td className="text-ink">{toDisplayWeight(s.weight_kg, units)}</td>
                <td className="text-ink">{s.reps}</td>
                <td className="text-muted">{s.rpe ?? "–"}</td>
                <td className="text-muted">{s.e1rm ? `${toDisplayWeight(s.e1rm, units)} ${weightUnit(units)}` : "–"}</td>
                <td>{s.is_pr && <span className="inline-flex items-center gap-1 rounded-md bg-warn/10 px-2 py-0.5 text-xs font-semibold text-warn"><IconTrophy width={12} height={12} /> PR</span>}</td>
              </>
            )}
            <td className="w-28 text-right">
              {confirming === s.id ? (
                <span className="inline-flex gap-2 text-xs">
                  <button type="button" className="text-bad hover:underline" disabled={busy} onClick={() => { onDelete(s); setConfirming(null); }}>Delete set {i + 1}?</button>
                  <button type="button" className="text-muted hover:text-ink" onClick={() => setConfirming(null)}>No</button>
                </span>
              ) : (
                <span className="inline-flex gap-3 text-xs">
                  <button type="button" className="text-muted hover:text-accent" aria-label={`Edit set ${i + 1}`} onClick={() => setEditing(s.id)}>Edit</button>
                  <button type="button" className="text-muted hover:text-bad" aria-label={`Delete set ${i + 1}`} onClick={() => setConfirming(s.id)}>Delete</button>
                </span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function EditRow({ index, set, timed, units, busy, onSave, onCancel }: {
  index: number;
  set: WorkoutSet;
  timed: boolean;
  units: "metric" | "imperial";
  busy: boolean;
  onSave: (patch: SetPatch) => void;
  onCancel: () => void;
}) {
  const [weight, setWeight] = useState(String(toDisplayWeight(set.weight_kg, units)));
  const [reps, setReps] = useState(String(set.reps));
  const [duration, setDuration] = useState(formatDuration(set.duration_s ?? 0));
  const [rpe, setRpe] = useState<number | null>(set.rpe);
  const [error, setError] = useState<string | null>(null);

  function save() {
    if (timed) {
      const seconds = parseDuration(duration);
      if (!seconds) return setError("duration?");
      return onSave({ duration_s: seconds, rpe });
    }
    const w = Number(weight);
    const r = Number(reps);
    if (Number.isNaN(w) || w < 0 || !Number.isInteger(r) || r < 1) return setError("check weight/reps");
    onSave({ weight_kg: fromDisplayWeight(w, units), reps: r, rpe });
  }

  return (
    <tr className="border-t border-line/70 bg-panel-2/60">
      <td className="py-1.5 text-muted">{index + 1}</td>
      {timed ? (
        <td colSpan={3}>
          <input aria-label="Edit duration" className="input h-8 w-28" value={duration} onChange={(e) => setDuration(e.target.value)} />
          {error && <span className="ml-2 text-xs text-bad">{error}</span>}
        </td>
      ) : (
        <>
          <td><input aria-label="Edit weight" className="input h-8 w-20" value={weight} onChange={(e) => setWeight(e.target.value)} inputMode="decimal" /></td>
          <td><input aria-label="Edit reps" className="input h-8 w-16" value={reps} onChange={(e) => setReps(e.target.value)} inputMode="numeric" /></td>
        </>
      )}
      <td>
        <select aria-label="Edit RPE" className="input h-8 w-20 py-0" value={rpe ?? ""} onChange={(e) => setRpe(e.target.value ? Number(e.target.value) : null)}>
          <option value="">–</option>
          {RPE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </td>
      {!timed && <td colSpan={2} className="text-xs text-bad">{error}</td>}
      <td className="text-right">
        <span className="inline-flex gap-3 text-xs">
          <button type="button" className="text-accent hover:underline" disabled={busy} onClick={save}>Save</button>
          <button type="button" className="text-muted hover:text-ink" onClick={onCancel}>Cancel</button>
        </span>
      </td>
    </tr>
  );
}

function groupSets(w: Workout | null): [string, Workout["sets"]][] {
  if (!w) return [];
  const m = new Map<string, Workout["sets"]>();
  for (const s of w.sets) m.set(s.exercise_name, [...(m.get(s.exercise_name) ?? []), s]);
  return [...m.entries()];
}
