import type { Exercise, Section, SetIn, SetPatch, SkillUnlock, Workout, WorkoutSet } from "@ascend/shared";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import { Transient } from "../components/Celebrate";
import { IconCheck, IconSearch, IconTrophy } from "../components/Icons";
import { NumberField, RestTimer, RPE_OPTIONS, RpeSelect } from "../components/logger/fields";
import { SECTIONS, SectionTabs } from "../components/logger/SectionTabs";
import { HoldSetForm } from "../components/logger/HoldSetForm";
import { TimedSetForm } from "../components/logger/TimedSetForm";
import { Empty, ErrorState, Loading } from "../components/States";
import { SkillAcquired } from "../components/SkillAcquired";
import { useToast } from "../components/Toast";
import { count } from "../lib/format";
import { sessionLoad } from "../lib/load";
import { clearPendingExercise, peekPendingExercise } from "../lib/pending";
import { useReducedMotion } from "../lib/motion";
import { MUSCLE_LABEL } from "../lib/muscles";
import { usePrefs } from "../lib/prefs";
import { formatDistance, formatDuration, fromDisplayWeight, parseDuration, toDisplayWeight, weightUnit } from "../lib/units";
import { useApi } from "../lib/useApi";

const REST_SECONDS = 90;

export const isBodyweight = (e: Pick<Exercise, "equipment" | "section">): boolean =>
  e.section === "calisthenics" || /body ?weight|none/i.test(e.equipment);

export function WorkoutPage({ onChanged }: { onChanged: () => void }) {
  // "Log it" from the gallery (or "Train" on a skill) hands over an exercise to open.
  // Peeked, not taken: React may run this initializer twice in development.
  const [pending] = useState(peekPendingExercise);
  useEffect(clearPendingExercise, []);
  const [section, setSection] = useState<Section>(pending?.section ?? "gym");
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
  const [restPaused, setRestPaused] = useState(false);
  // The set just logged: its row slides in with a check, and "+N XP" floats off the button.
  const [logged, setLogged] = useState<{ id: number; xp: number; n: number } | null>(null);
  const toast = useToast();
  // Skill-tree steps the last set unlocked: shown as the "Skill acquired" moment.
  const [acquired, setAcquired] = useState<SkillUnlock[]>([]);

  useEffect(() => {
    if (active.data !== undefined) setWorkout(active.data);
  }, [active.data]);

  // Bodyweight moves start at no added load (a pull-up logged at the 40 kg default
  // would be a weighted pull-up); barbell/dumbbell work keeps the last weight used.
  const bodyweight = selected ? isBodyweight(selected) : false;
  useEffect(() => {
    if (selected && isBodyweight(selected)) setWeight(0);
  }, [selected]);

  const [pendingDone, setPendingDone] = useState(false);
  useEffect(() => {
    if (!pending || pendingDone || !exercises.data) return;
    const match = exercises.data.find((e) => e.id === pending.id);
    if (match) setSelected(match);
    setPendingDone(true);
  }, [pending, pendingDone, exercises.data]);

  useEffect(() => {
    if (restLeft <= 0 || restPaused) return;
    const t = setTimeout(() => setRestLeft((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [restLeft, restPaused]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = exercises.data ?? [];
    return q ? list.filter((e) => e.name.toLowerCase().includes(q) || e.muscles.some((m) => (MUSCLE_LABEL[m.muscle] ?? m.muscle).toLowerCase().includes(q))) : list;
  }, [exercises.data, query]);

  // Last session's sets of the selected exercise: shown in grey ("last time") and used as
  // the target for the next set, so Enter alone repeats last time's set.
  const previous = useApi(() => (selected ? api.previousSession(selected.id) : Promise.resolve(null)), [selected?.id]);
  const detail = useApi(() => (selected ? api.exercise(selected.id) : Promise.resolve(null)), [selected?.id]);
  const doneSets = useMemo(() => (workout && selected ? workout.sets.filter((s) => s.exercise_id === selected.id) : []), [workout, selected]);
  const prevSets = previous.data?.sets ?? [];
  const target = targetFor(prevSets, doneSets.length);
  const targetKey = `${selected?.id ?? 0}:${doneSets.length}:${previous.data?.workout_id ?? 0}`;

  // Pre-fill the inputs with the target whenever the next set or the exercise changes.
  useEffect(() => {
    if (!target || !selected || selected.measure === "hold" || selected.time_based) return;
    setWeight(toDisplayWeight(target.weight_kg, units));
    setReps(target.reps);
    if (target.rpe !== null) setRpe(target.rpe);
    // targetKey captures every input of the target; units only re-run on a unit switch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetKey, units]);

  // Space pauses or resumes the rest timer when focus is not in a field or on a button.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== " " || restLeft <= 0) return;
      const el = e.target as HTMLElement | null;
      if (el && el.closest("input, select, textarea, button, a, [role='switch'], [contenteditable='true']")) return;
      e.preventDefault();
      setRestPaused((p) => !p);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [restLeft]);

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
      setLogged((prev) => ({ id: res.set.id, xp: res.xp_awarded, n: (prev?.n ?? 0) + 1 }));
      if (!selected.time_based) {
        setRestLeft(REST_SECONDS);
        setRestPaused(false);
      }
      const isHold = selected.measure === "hold";
      if (res.set.is_pr && isHold) toast(`New best hold! ${selected.name} ${res.set.duration_s} s · +${res.xp_awarded} XP`, "pr");
      else if (res.set.is_pr) toast(`New PR! ${selected.name} e1RM ${toDisplayWeight(res.set.e1rm ?? 0, units)} ${weightUnit(units)} · +${res.xp_awarded} XP`, "pr");
      else if (isHold) toast(`${res.set.duration_s} s hold logged · +${res.xp_awarded} XP`, "xp");
      else toast(`${selected.time_based ? formatDuration(res.set.duration_s ?? 0) + " logged" : "Set logged"} · +${res.xp_awarded} XP`, "xp");
      if (res.unlocks?.length) setAcquired(res.unlocks);
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

  const sessionExercises = groupSessionExercises(workout);
  const lastDay = previous.data ? shortDay(previous.data.day) : null;

  return (
    <div className="space-y-5">
    {acquired.length > 0 && (
      <SkillAcquired
        unlocks={acquired}
        onClose={() => setAcquired([])}
        onView={(key) => { setAcquired([]); window.location.hash = `skills/${key}`; }}
      />
    )}
    <SectionTabs value={section} onChange={changeSection} />
    {/* Three panes on the 12-column grid: session + library (3) | active exercise (6) | context (3). */}
    <div className="grid grid-cols-12 gap-5">
      <div className="col-span-12 flex min-h-0 flex-col gap-5 lg:col-span-3">
        {sessionExercises.length > 0 && (
          <section className="card p-4" aria-labelledby="session-list-title">
            <h2 id="session-list-title" className="card-title mb-2">This session</h2>
            <ul className="space-y-0.5">
              {sessionExercises.map((g) => {
                const ex = exercises.data?.find((e) => e.id === g.id);
                const active = selected?.id === g.id;
                return (
                  <li key={g.id}>
                    <button type="button" disabled={!ex} onClick={() => ex && setSelected(ex)} aria-current={active ? "true" : undefined}
                      className={`flex w-full items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-left text-sm transition-colors duration-150 ${active ? "bg-accent/10 text-accent" : "text-ink hover:bg-panel-2"} disabled:cursor-default`}>
                      <span className="truncate">{active && <span aria-hidden="true">▸ </span>}{g.name}</span>
                      <span className={`shrink-0 text-xs ${active ? "text-accent" : "text-muted"}`}>{count(g.sets, "set")}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        )}
        <section className="card flex min-h-0 flex-1 flex-col">
          <div className="border-b border-line p-4">
            <h2 className="card-title mb-3">{sectionLabel} library</h2>
            <div className="relative">
              <IconSearch className="absolute left-3 top-2.5 text-faint" width={16} height={16} />
              <input className="input pl-9" aria-label="Search exercises" placeholder="Exercise or muscle…" value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
          </div>
          <ul className="max-h-[calc(100vh-360px)] min-h-0 flex-1 overflow-y-auto p-2" aria-busy={exercises.loading}>
            {exercises.loading && !exercises.data && <li><Loading label="Loading exercises…" /></li>}
            {filtered.map((e) => (
              <li key={e.id}>
                <button type="button" onClick={() => setSelected(e)}
                  className={`w-full rounded-md px-3 py-2 text-left transition-colors duration-150 ${selected?.id === e.id ? "bg-accent/10" : "hover:bg-panel-2"}`}>
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
      </div>

      <section className="col-span-12 space-y-5 lg:col-span-6">
        <div className="card p-5">
          {selected ? (
            <>
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h2 className="text-h2 truncate text-ink">{selected.name}</h2>
                  <p className="mt-0.5 text-small text-muted">
                    {target ? <>Target: <span className="text-ink">{describeSet(target, units)}</span> (last time{lastDay ? `, ${lastDay}` : ""})</> : previous.loading ? "Loading last time…" : "First time logging this: set your own target."}
                  </p>
                </div>
                {!selected.time_based && <RestTimer seconds={restLeft} onSkip={() => setRestLeft(0)} />}
              </div>
              {!selected.time_based && <GhostGrid prev={prevSets} done={doneSets} units={units} justLogged={logged?.id} />}
              {selected.time_based ? (
                <div className="mt-5">
                  <div className="relative">
                    <TimedSetForm key={`${selected.id}:${previous.data?.workout_id ?? 0}`} exercise={selected} units={units} busy={busy} onSubmit={(s) => logSet(s)} initialSeconds={target?.duration_s ?? undefined} />
                    <XpGain logged={logged} className="bottom-10 right-4" />
                  </div>
                  {prevSets.length > 0 && <p className="mt-2 text-xs text-muted">Last time{lastDay ? ` (${lastDay})` : ""}: <span className="text-faint">{prevSets.map((s) => describeSet(s, units)).join(" · ")}</span></p>}
                  <p className="mt-2 text-[11px] text-faint">
                    Calories use the activity's MET value ({selected.met ?? "n/a"}) × your weight × time, an estimate.
                    {selected.muscles.length === 0 && " Stretching and meditation add no muscle load."}
                  </p>
                </div>
              ) : selected.measure === "hold" ? (
                <HoldSetForm key={selected.id} exercise={selected} units={units} busy={busy} onSubmit={(s) => logSet(s)}
                  target={target ? { seconds: target.duration_s ?? 0, added: toDisplayWeight(target.weight_kg, units), rpe: target.rpe, key: targetKey } : undefined}>
                  <XpGain logged={logged} className="-top-5 right-2" />
                </HoldSetForm>
              ) : (
                <>
                  {/* A real form, so Enter in any field logs the set. Reps come first (Tab: reps → load → RPE). */}
                  <form
                    className="mt-4 grid grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_minmax(0,1fr)_auto] items-end gap-3"
                    aria-label={`Log a set of ${selected.name}`}
                    onSubmit={(e) => { e.preventDefault(); if (!busy) void logSet(); }}
                  >
                    <NumberField label="Reps" value={reps} step={1} onChange={setReps} />
                    <NumberField label={bodyweight ? `Added load (${weightUnit(units)})` : `Weight (${weightUnit(units)})`} value={weight} step={units === "imperial" ? 5 : 2.5} onChange={setWeight} />
                    <RpeSelect value={rpe} onChange={setRpe} />
                    <span className="relative">
                      <button type="submit" className="btn-primary h-[38px] px-5" disabled={busy}>Log set</button>
                      <XpGain logged={logged} className="-top-5 right-2" />
                    </span>
                  </form>
                  <p className="mt-2 text-[11px] text-faint">Enter logs the set shown; the next set fills in from last time. RPE 10 = no reps left, 8 = two left. PRs use the Epley e1RM (1–10 reps).</p>
                </>
              )}
              {!selected.time_based && <RestBar left={restLeft} total={REST_SECONDS} paused={restPaused} />}
            </>
          ) : (
            <Empty title={`Pick a ${sectionLabel.toLowerCase()} exercise from the library to start logging.`} hint="Sets are saved instantly. Your session starts with the first set." />
          )}
        </div>

        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="card-title">Session log</h2>
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
                  <SetTable label={`${name}: logged sets`} sets={sets} units={units} onEdit={editSet} onDelete={deleteSet} busy={busy} justLogged={logged?.id} />
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <aside className="col-span-12 space-y-5 lg:col-span-3" aria-label="Exercise context">
        {selected && (
          <section className="card p-4" aria-labelledby="ctx-muscles">
            <h2 id="ctx-muscles" className="card-title mb-2">Muscles hit</h2>
            {selected.muscles.length === 0 ? <p className="text-xs text-muted">No muscle load (stretching or meditation).</p> : (
              <ul className="space-y-1.5">
                {[...selected.muscles].sort((a, b) => b.weight - a.weight).map((m) => (
                  <li key={m.muscle} className="flex items-center gap-2 text-xs">
                    <span className="w-24 shrink-0 truncate text-muted">{MUSCLE_LABEL[m.muscle] ?? m.muscle}</span>
                    <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-line" aria-hidden="true">
                      <span className="block h-full origin-left rounded-full bg-ink/70" style={{ transform: `scaleX(${Math.min(1, m.weight)})` }} />
                    </span>
                    <span className="w-8 text-right text-ink">×{m.weight}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
        {selected && (
          <section className="card p-4" aria-labelledby="ctx-last">
            <h2 id="ctx-last" className="card-title mb-2">Last time</h2>
            {previous.loading && !previous.data ? <p className="text-xs text-muted">Loading…</p> : prevSets.length === 0 ? (
              <p className="text-xs text-muted">Never logged before. Whatever you log today becomes next session's target.</p>
            ) : (
              <>
                <p className="text-xs text-muted">{lastDay}{previous.data?.source !== "app" ? ` · imported from ${previous.data?.source}` : ""} · {count(prevSets.length, "set")}</p>
                <ol className="mt-2 space-y-0.5 text-sm text-faint">
                  {prevSets.map((s, i) => <li key={s.id}><span className="inline-block w-5 text-muted">{i + 1}</span>{describeSet(s, units)}</li>)}
                </ol>
                <p className="mt-2 text-[11px] text-faint">Targets repeat last session. Progression suggestions (add load or reps) arrive with the progression engine.</p>
              </>
            )}
          </section>
        )}
        {selected && (detail.data?.skills.length ?? 0) > 0 && (
          <section className="card p-4" aria-labelledby="ctx-skills">
            <h2 id="ctx-skills" className="card-title mb-2">Skills this feeds</h2>
            <ul className="space-y-1">
              {detail.data!.skills.slice(0, 4).map((s) => (
                <li key={`${s.skill_key}-${s.role}`}>
                  <a href={`#skills/${s.skill_key}`} className="text-sm text-accent hover:underline">{s.skill_name}</a>
                  <span className="text-xs text-muted"> · {s.role === "step" ? `step: ${s.step_name}` : "feeder"}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
        {load.length > 0 && (
          <section className="card p-4" aria-labelledby="ctx-load">
            <h2 id="ctx-load" className="card-title mb-1">Session muscle load</h2>
            <p className="mb-3 text-[11px] text-faint">effective sets = muscle weight × effort (RPE)</p>
            <ul className="space-y-1.5">
              {load.slice(0, 8).map(([muscle, es]) => (
                <li key={muscle} className="flex items-center gap-2 text-xs">
                  <span className="w-24 shrink-0 truncate text-muted">{MUSCLE_LABEL[muscle] ?? muscle}</span>
                  <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
                    <span className="block h-full origin-left rounded-full bg-accent" style={{ transform: `scaleX(${Math.min(1, es / load[0][1])})` }} />
                  </span>
                  <span className="w-8 text-right text-ink">{es.toFixed(1)}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
        {!selected && load.length === 0 && (
          <section className="card p-4 text-xs text-muted">
            <h2 className="card-title mb-2">Keyboard</h2>
            <ul className="space-y-1">
              <li><kbd className="chip">Enter</kbd> log the set shown (last time's set)</li>
              <li><kbd className="chip">Tab</kbd> reps → load → RPE</li>
              <li><kbd className="chip">Space</kbd> pause or resume rest</li>
              <li><kbd className="chip">Ctrl 2</kbd> open Train from anywhere</li>
            </ul>
          </section>
        )}
      </aside>
    </div>
    </div>
  );
}

/** "+N XP" that floats up and fades once per logged set (decoration; hidden with reduced motion). */
function XpGain({ logged, className }: { logged: { xp: number; n: number } | null; className: string }) {
  const reduce = useReducedMotion();
  if (reduce || !logged || logged.xp <= 0) return null;
  return (
    <Transient trigger={logged.n} ms={1100}>
      <span aria-hidden="true" className={`float-up motion-decor pointer-events-none absolute whitespace-nowrap text-xs font-semibold text-xp ${className}`} data-testid="set-xp-gain">
        +{logged.xp} XP
      </span>
    </Transient>
  );
}

function SetTable({ label, sets, units, onEdit, onDelete, busy, justLogged }: {
  label: string;
  sets: WorkoutSet[];
  justLogged?: number;
  units: "metric" | "imperial";
  onEdit: (s: WorkoutSet, patch: SetPatch) => void;
  onDelete: (s: WorkoutSet) => void;
  busy: boolean;
}) {
  const hold = sets.length > 0 && sets.every((s) => s.measure === "hold");
  const timed = !hold && sets.some((s) => s.duration_s !== null);
  const [editing, setEditing] = useState<number | null>(null);
  const [confirming, setConfirming] = useState<number | null>(null);
  return (
    <table className="w-full text-sm" aria-label={label}>
      <thead>
        <tr className="text-left text-[11px] uppercase tracking-wider text-faint">
          {hold ? (
            <>
              <th className="w-14 py-1 font-medium">Set</th><th className="font-medium">Hold</th><th className="font-medium">Added {weightUnit(units)}</th>
              <th className="font-medium">RPE</th><th className="w-24 font-medium"><span className="sr-only">Personal record</span></th><th><span className="sr-only">Actions</span></th>
            </>
          ) : timed ? (
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
          <EditRow key={s.id} index={i} set={s} timed={timed} hold={hold} units={units} busy={busy}
            onCancel={() => setEditing(null)}
            onSave={(patch) => { onEdit(s, patch); setEditing(null); }} />
        ) : (
          <tr key={s.id} className={`group border-t border-line/70 ${s.id === justLogged ? "set-row-in" : ""}`} data-just-logged={s.id === justLogged || undefined}>
            <td className="py-1.5 text-muted">
              <span className="inline-flex items-center gap-1.5">
                {i + 1}
                {s.id === justLogged && <IconCheck width={12} height={12} className="pop-in text-good" aria-hidden="true" />}
              </span>
            </td>
            {hold ? (
              <>
                <td className="text-ink">{s.duration_s ?? 0} s</td>
                <td className="text-ink">{s.weight_kg ? `+${toDisplayWeight(s.weight_kg, units)}` : "–"}</td>
                <td className="text-muted">{s.rpe ?? "–"}</td>
                <td>{s.is_pr && <span className="inline-flex items-center gap-1 rounded-md bg-warn/10 px-2 py-0.5 text-xs font-semibold text-warn"><IconTrophy width={12} height={12} /> Best</span>}</td>
              </>
            ) : timed ? (
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

function EditRow({ index, set, timed, hold = false, units, busy, onSave, onCancel }: {
  index: number;
  set: WorkoutSet;
  timed: boolean;
  hold?: boolean;
  units: "metric" | "imperial";
  busy: boolean;
  onSave: (patch: SetPatch) => void;
  onCancel: () => void;
}) {
  const [weight, setWeight] = useState(String(toDisplayWeight(set.weight_kg, units)));
  const [reps, setReps] = useState(String(set.reps));
  const [duration, setDuration] = useState(hold ? String(set.duration_s ?? 0) : formatDuration(set.duration_s ?? 0));
  const [rpe, setRpe] = useState<number | null>(set.rpe);
  const [error, setError] = useState<string | null>(null);

  function save() {
    if (hold) {
      const seconds = Number(duration);
      const added = Number(weight);
      if (!Number.isInteger(seconds) || seconds < 1) return setError("seconds?");
      if (Number.isNaN(added) || added < 0) return setError("added load?");
      return onSave({ duration_s: seconds, weight_kg: fromDisplayWeight(added, units), rpe });
    }
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
      {hold ? (
        <>
          <td><input aria-label="Edit seconds held" className="input h-8 w-20" value={duration} onChange={(e) => setDuration(e.target.value)} inputMode="numeric" /></td>
          <td><input aria-label="Edit added load" className="input h-8 w-20" value={weight} onChange={(e) => setWeight(e.target.value)} inputMode="decimal" /></td>
        </>
      ) : timed ? (
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
      {hold && <td className="text-xs text-bad">{error}</td>}
      {!timed && !hold && <td colSpan={2} className="text-xs text-bad">{error}</td>}
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

/** The target for set n (0-based): last time's set n, or its last set when doing more sets. */
export function targetFor(prev: WorkoutSet[], n: number): WorkoutSet | null {
  if (prev.length === 0) return null;
  return prev[Math.min(n, prev.length - 1)];
}

/** "60 kg × 8 @8", "+5 kg · 45 s", "30:00". */
export function describeSet(s: Pick<WorkoutSet, "weight_kg" | "reps" | "rpe" | "duration_s" | "distance_m" | "measure">, units: "metric" | "imperial"): string {
  const rpe = s.rpe !== null && s.rpe !== undefined ? ` @${s.rpe}` : "";
  if (s.measure === "hold") return `${s.weight_kg ? `+${toDisplayWeight(s.weight_kg, units)} ${weightUnit(units)} · ` : ""}${s.duration_s ?? 0} s${rpe}`;
  if (s.measure === "time" || (s.duration_s && !s.reps)) return `${formatDuration(s.duration_s ?? 0)}${s.distance_m ? ` · ${formatDistance(s.distance_m, units)}` : ""}`;
  return `${s.weight_kg ? `${toDisplayWeight(s.weight_kg, units)} ${weightUnit(units)}` : "BW"} × ${s.reps}${rpe}`;
}

function shortDay(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}

function groupSessionExercises(w: Workout | null): { id: number; name: string; sets: number }[] {
  if (!w) return [];
  const m = new Map<number, { id: number; name: string; sets: number }>();
  for (const s of w.sets) {
    const row = m.get(s.exercise_id) ?? { id: s.exercise_id, name: s.exercise_name, sets: 0 };
    row.sets += 1;
    m.set(s.exercise_id, row);
  }
  return [...m.values()];
}

/**
 * Last session (grey) next to today's sets, row by row, with the next set marked.
 * A freshly saved set flashes the accent for 150 ms.
 */
function GhostGrid({ prev, done, units, justLogged }: { prev: WorkoutSet[]; done: WorkoutSet[]; units: "metric" | "imperial"; justLogged?: number }) {
  const rows = Math.max(prev.length, done.length + 1);
  if (prev.length === 0 && done.length === 0) return null;
  return (
    <table className="mt-4 w-full text-sm" aria-label="Sets: last time and today">
      <thead>
        <tr className="text-left text-[11px] uppercase tracking-wider text-faint">
          <th className="w-12 py-1 font-medium">Set</th>
          <th className="font-medium">Last time</th>
          <th className="font-medium">Today</th>
        </tr>
      </thead>
      <tbody>
        {Array.from({ length: rows }, (_, i) => {
          const p = prev[i];
          const t = done[i];
          const next = i === done.length;
          return (
            <tr key={i} className={`border-t border-line/70 ${t && t.id === justLogged ? "set-flash" : ""} ${next ? "bg-accent/[0.05]" : ""}`} data-ghost-row={i + 1}>
              <td className="py-1.5 text-muted">{next ? <span className="text-accent" aria-label={`Set ${i + 1}, next`}>▸ {i + 1}</span> : i + 1}</td>
              <td className="text-faint" data-testid="ghost">{p ? describeSet(p, units) : "–"}</td>
              <td className={t ? "text-ink" : "text-faint"}>{t ? describeSet(t, units) : next ? "next" : ""}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/** A thin bar under the active set that shrinks as rest runs out (transform only). */
function RestBar({ left, total, paused }: { left: number; total: number; paused: boolean }) {
  if (left <= 0) return null;
  return (
    <div className="mt-4" data-testid="rest-bar">
      <div className="h-1 overflow-hidden rounded-full bg-line" aria-hidden="true">
        <div className="h-full origin-left rounded-full bg-accent" style={{ transform: `scaleX(${left / total})`, transition: "transform 1s linear" }} />
      </div>
      <p className="mt-1 text-[11px] text-faint">{paused ? "Rest paused · Space to resume" : "Resting · Space to pause"}</p>
    </div>
  );
}
