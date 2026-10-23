import type { Exercise, ProgressionTarget, Section, SetIn, SetPatch, SkillUnlock, Workout, WorkoutSet } from "@ascend/shared";
import { useEffect, useLayoutEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import { ExerciseArt } from "../components/ExerciseArt";
import { ProgramCard } from "../components/ProgramCard";
import { RunThrough } from "../components/RunThrough";
import { WorkoutFinish, type FinishSummary } from "../components/WorkoutFinish";
import { play } from "../lib/sound";
import { Transient } from "../components/Celebrate";
import { IconCheck, IconSearch, IconTrophy } from "../components/Icons";
import { NumberField, RestTimer, RPE_OPTIONS, RpeSelect } from "../components/logger/fields";
import { SECTIONS, SectionTabs } from "../components/logger/SectionTabs";
import { HoldSetForm } from "../components/logger/HoldSetForm";
import { SuggestionCard } from "../components/logger/SuggestionCard";
import { TimedSetForm } from "../components/logger/TimedSetForm";
import { Empty, ErrorState, Loading } from "../components/States";
import { SkillAcquired } from "../components/SkillAcquired";
import { useToast } from "../components/Toast";
import { count } from "../lib/format";
import { sessionLoad } from "../lib/load";
import { clearPendingExercise, peekPendingExercise } from "../lib/pending";
import { fitsKit, hasGymKit, needsLabel, useLoadout } from "../lib/loadout";
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
  // v1.2: the finish moment (a full screen, not a toast) and the full-screen timer.
  const [finished, setFinished] = useState<FinishSummary | null>(null);
  const [fullTimer, setFullTimer] = useState(false);
  const plan = useApi(api.currentPlan, [], { cacheKey: "plan" });
  // v1.2: the loadout drives Train. Without gym kit it opens on Calisthenics, and the
  // library lists the moves that fit; "Explore all" shows the rest greyed out.
  const loadout = useLoadout();
  const [explore, setExplore] = useState(false);
  const [sectionChosen, setSectionChosen] = useState(Boolean(pending));
  useEffect(() => {
    if (sectionChosen || !loadout.loaded) return;
    setSectionChosen(true);
    if (!hasGymKit(loadout.choices)) setSection("calisthenics");
  }, [sectionChosen, loadout.loaded, loadout.choices]);

  useEffect(() => {
    if (active.data !== undefined) setWorkout(active.data);
  }, [active.data]);

  // Bodyweight moves start at no added load (a pull-up logged at the 40 kg default
  // would be a weighted pull-up); barbell/dumbbell work keeps the last weight used.
  // A layout effect, so the 40 kg default is never painted for a bodyweight move.
  const bodyweight = selected ? isBodyweight(selected) : false;
  useLayoutEffect(() => {
    if (selected && isBodyweight(selected)) setWeight(0);
  }, [selected]);

  // A program item picked on the card: selected once its section's list has loaded.
  const [pickId, setPickId] = useState<number | null>(null);
  useEffect(() => {
    if (pickId === null || !exercises.data) return;
    const match = exercises.data.find((e) => e.id === pickId);
    if (match) {
      setSelected(match);
      setPickId(null);
    }
  }, [pickId, exercises.data]);

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
    const all = exercises.data ?? [];
    const list = explore ? all : all.filter((e) => fitsKit(e.equipment, loadout.allowed));
    return q ? list.filter((e) => e.name.toLowerCase().includes(q) || e.muscles.some((m) => (MUSCLE_LABEL[m.muscle] ?? m.muscle).toLowerCase().includes(q))) : list;
  }, [exercises.data, query, explore, loadout.allowed]);
  const hiddenByKit = loadout.allowed ? (exercises.data ?? []).filter((e) => !fitsKit(e.equipment, loadout.allowed)).length : 0;

  // Last session's sets of the selected exercise: shown in grey ("last time") and used as
  // the target for the next set, so Enter alone repeats last time's set.
  const previous = useApi(() => (selected ? api.previousSession(selected.id) : Promise.resolve(null)), [selected?.id]);
  const detail = useApi(() => (selected ? api.exercise(selected.id) : Promise.resolve(null)), [selected?.id]);
  const doneSets = useMemo(() => (workout && selected ? workout.sets.filter((s) => s.exercise_id === selected.id) : []), [workout, selected]);
  const prevSets = previous.data?.sets ?? [];
  // The progression engine's suggestion (prog-v1) replaces "repeat last time" as the target,
  // unless there is none yet (first time), it is a timed activity, or you chose "Keep mine".
  const suggestion = useApi(
    () => (selected && !selected.time_based ? api.progression(selected.id) : Promise.resolve(null)),
    [selected?.id, previous.data?.workout_id],
  );
  const [decided, setDecided] = useState<Record<number, "accepted" | "kept">>({});
  const engine = usableSuggestion(suggestion.data ?? null);
  const lastTarget = targetFor(prevSets, doneSets.length);
  const target = engine && lastTarget ? fromSuggestion(lastTarget, engine) : lastTarget;
  const targetKey = `${selected?.id ?? 0}:${doneSets.length}:${previous.data?.workout_id ?? 0}:${engine ? `${engine.reason}:${engine.weight_kg}:${engine.reps ?? engine.seconds}` : "last"}`;

  const selectedId = selected?.id;
  const explainTarget = useMemo(
    () => (selectedId === undefined ? undefined : () => api.progressionExplanation(selectedId)),
    [selectedId],
  );

  async function decide(choice: "accepted" | "kept") {
    if (!selected) return;
    const id = selected.id;
    try {
      await api.decideProgression(id, choice);
      setDecided((d) => ({ ...d, [id]: choice }));
      if (choice === "kept") suggestion.reload();
      else if (engine && engine.kind === "reps") {
        setWeight(toDisplayWeight(engine.weight_kg, units));
        if (engine.reps !== null) setReps(engine.reps);
        if (engine.rpe !== null) setRpe(engine.rpe);
      }
    } catch {
      toast("Could not save that choice. Try again.", "error");
    }
  }

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
    setSectionChosen(true);
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
      play("set");
      if (!selected.time_based) {
        setRestLeft(REST_SECONDS);
        setRestPaused(false);
      }
      const isHold = selected.measure === "hold";
      if (res.set.is_pr && isHold) toast(`New best hold! ${selected.name} ${res.set.duration_s} s · +${res.xp_awarded} XP`, "pr");
      else if (res.set.is_pr) toast(`New personal best! ${selected.name} · +${res.xp_awarded} XP`, "pr");
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
      const before = await api.game().catch(() => null);
      const res = await api.finishWorkout(workout.id);
      const [game, boss] = await Promise.all([api.game().catch(() => null), api.boss().catch(() => null)]);
      setFinished({ result: res, game, boss, levelBefore: before?.xp.level ?? null });
      setFullTimer(false);
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
  const nextUp = nextInPlan(plan.data?.next.items.map((i) => i.exercise) ?? [], selected?.name);

  return (
    <div className="space-y-5">
    {finished && (
      <WorkoutFinish summary={finished} onClose={() => setFinished(null)} onToday={() => { setFinished(null); window.location.hash = "dashboard"; }} />
    )}
    {fullTimer && selected && !selected.time_based && (
      <RunThrough
        exercise={selected}
        target={target ? describeSet(target, units) : null}
        setsDone={doneSets.length}
        restLeft={restLeft}
        restTotal={REST_SECONDS}
        paused={restPaused}
        busy={busy}
        nextUp={nextUp}
        onTogglePause={() => setRestPaused((p) => !p)}
        onSkipRest={() => setRestLeft(0)}
        onSetDone={() => void logSet()}
        onExit={() => setFullTimer(false)}
      />
    )}
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
        <ProgramCard refreshKey={workout?.sets.length ?? 0} onPick={(id, itemSection) => {
          // v1.2: a program item opens in its own section's logger (a calisthenics or hold
          // item used to do nothing from the gym list).
          if (itemSection && itemSection !== section && SECTIONS.some((s) => s.id === itemSection)) {
            changeSection(itemSection as Section);
          }
          setPickId(id);
        }} />
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
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 className="card-title">{sectionLabel} library</h2>
              {hiddenByKit > 0 && (
                <label className="flex items-center gap-1.5 text-xs text-muted" title="Show moves that need kit you don't have">
                  <input type="checkbox" className="accent-accent" checked={explore} onChange={(e) => setExplore(e.target.checked)} />
                  Explore all
                </label>
              )}
            </div>
            <div className="relative">
              <IconSearch className="absolute left-3 top-2.5 text-faint" width={16} height={16} />
              <input className="input pl-9" aria-label="Search exercises" placeholder="Exercise or muscle…" value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
          </div>
          <ul className="max-h-[calc(100vh-360px)] min-h-0 flex-1 overflow-y-auto p-2" aria-busy={exercises.loading}>
            {exercises.loading && !exercises.data && <li><Loading label="Loading exercises…" /></li>}
            {filtered.map((e) => (
              <li key={e.id}>
                <button type="button" onClick={() => setSelected(e)} data-fits={fitsKit(e.equipment, loadout.allowed) || undefined}
                  className={`w-full rounded-md px-3 py-2 text-left transition-colors duration-150 ${selected?.id === e.id ? "bg-accent/10" : "hover:bg-panel-2"} ${fitsKit(e.equipment, loadout.allowed) ? "" : "opacity-55"}`}>
                  <div className={`text-sm ${selected?.id === e.id ? "text-accent" : "text-ink"}`}>
                    {e.name}
                    {!fitsKit(e.equipment, loadout.allowed) && <span className="ml-2 text-[11px] text-muted">{needsLabel(e.equipment)}</span>}
                  </div>
                  <div className={`mt-0.5 truncate text-xs ${selected?.id === e.id ? "text-muted" : "text-faint"}`}>
                    {e.equipment}
                    {e.muscles.some((m) => m.weight >= 1) && ` · ${e.muscles.filter((m) => m.weight >= 1).map((m) => MUSCLE_LABEL[m.muscle] ?? m.muscle).join(", ")}`}
                    {e.time_based && e.met ? ` · MET ${e.met}` : ""}
                  </div>
                </button>
              </li>
            ))}
            {filtered.length === 0 && !exercises.loading && (
              <li className="p-4 text-sm text-faint">
                {query ? <>No exercise matches “{query}”.</> : "Nothing here fits your kit."}
                {hiddenByKit > 0 && !explore && <> <button type="button" className="text-accent hover:underline" onClick={() => setExplore(true)}>Explore all</button></>}
              </li>
            )}
          </ul>
        </section>
      </div>

      <section className="col-span-12 space-y-5 lg:col-span-6">
        <div className="card p-5">
          {selected ? (
            <>
              <div className="flex items-start justify-between gap-4">
                <div className="w-24 shrink-0 overflow-hidden rounded-lg" data-testid="train-exercise-art"><ExerciseArt exercise={selected} className="h-24" /></div>
                <div className="min-w-0 flex-1">
                  <h2 className="text-h2 truncate text-ink">{selected.name}</h2>
                  <p className="mt-0.5 text-small text-muted">
                    {target ? <>Target: <span className="text-ink">{describeSet(target, units)}</span> ({engine ? "suggested" : `last time${lastDay ? `, ${lastDay}` : ""}`})</> : previous.loading ? "Loading last time…" : "First time logging this: set your own target."}
                  </p>
                </div>
                {!selected.time_based && (
                  <div className="flex shrink-0 flex-col items-end gap-2">
                    <RestTimer seconds={restLeft} onSkip={() => setRestLeft(0)} />
                    <button type="button" className="btn-ghost h-8 px-3 text-xs" onClick={() => setFullTimer(true)}>Full-screen timer</button>
                  </div>
                )}
              </div>
              {!selected.time_based && <GhostGrid prev={prevSets} done={doneSets} units={units} justLogged={logged?.id} />}
              {suggestion.data && (
                <SuggestionCard target={suggestion.data} units={units} decided={decided[selected.id] ?? null}
                  onUse={() => void decide("accepted")} onKeep={() => void decide("kept")} explain={explainTarget} />
              )}
              {selected.time_based ? (
                <div className="mt-5">
                  <div className="relative">
                    <TimedSetForm key={`${selected.id}:${previous.data?.workout_id ?? 0}`} exercise={selected} units={units} busy={busy} onSubmit={(s) => logSet(s)} initialSeconds={target?.duration_s ?? undefined} />
                    <XpGain logged={logged} className="bottom-10 right-4" />
                  </div>
                  {prevSets.length > 0 && <p className="mt-2 text-xs text-muted">Last time{lastDay ? ` (${lastDay})` : ""}: <span className="text-faint">{prevSets.map((s) => describeSet(s, units)).join(" · ")}</span></p>}
                  <details className="mt-2 text-[11px] text-faint">
                    <summary className="cursor-pointer">Details</summary>
                    Calories use the activity's MET value ({selected.met ?? "n/a"}) × your weight × time, an estimate.
                    {selected.muscles.length === 0 && " Stretching and meditation add no muscle load."}
                  </details>
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
                    <RpeSelect value={rpe} onChange={setRpe} label="Effort (1-10)" />
                    <span className="relative">
                      <button type="submit" className="btn-primary h-[38px] px-5" disabled={busy}>Log set</button>
                      <XpGain logged={logged} className="-top-5 right-2" />
                    </span>
                  </form>
                  <p className="mt-2 text-[11px] text-faint">Enter logs the set shown. Effort: 10 = no reps left, 8 = two left.</p>
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
                    <span className="w-14 text-right text-muted">{m.weight >= 1 ? "main" : "helper"}</span>
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
                <p className="mt-2 text-[11px] text-faint">Today's target comes from the suggestion card. It repeats last session when there is no suggestion yet or you chose "Keep mine".</p>
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
            <h2 id="ctx-load" className="card-title mb-3">Muscles worked this session</h2>
            <ul className="space-y-1.5">
              {load.slice(0, 8).map(([muscle, es]) => (
                <li key={muscle} className="flex items-center gap-2 text-xs">
                  <span className="w-24 shrink-0 truncate text-muted">{MUSCLE_LABEL[muscle] ?? muscle}</span>
                  <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
                    <span className="block h-full origin-left rounded-full bg-accent" style={{ transform: `scaleX(${Math.min(1, es / load[0][1])})` }} />
                  </span>
                  <span className="w-14 text-right text-muted">{count(Math.round(es), "set")}</span>
                </li>
              ))}
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
              <th className="font-medium">Effort</th><th className="w-24 font-medium"><span className="sr-only">Personal record</span></th><th><span className="sr-only">Actions</span></th>
            </>
          ) : timed ? (
            <>
              <th className="w-14 py-1 font-medium">#</th><th className="font-medium">Time</th><th className="font-medium">Distance</th>
              <th className="font-medium">Avg HR</th><th className="font-medium">Effort</th><th><span className="sr-only">Actions</span></th>
            </>
          ) : (
            <>
              <th className="w-14 py-1 font-medium">Set</th><th className="font-medium">{weightUnit(units)}</th><th className="font-medium">Reps</th>
              <th className="font-medium">Effort</th><th className="font-medium">Strength est.</th><th className="w-24 font-medium"><span className="sr-only">Personal record</span></th><th><span className="sr-only">Actions</span></th>
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
        <select aria-label="Edit effort" className="input h-8 w-20 py-0" value={rpe ?? ""} onChange={(e) => setRpe(e.target.value ? Number(e.target.value) : null)}>
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

/** The suggestion to fill the inputs from: none for a first time, a timed activity or "keep mine". */
export function usableSuggestion(t: ProgressionTarget | null): ProgressionTarget | null {
  if (!t || t.kind === "none" || t.change === "first" || t.reason === "kept") return null;
  return t;
}

/** Last time's set n with the suggestion's numbers in place. */
export function fromSuggestion(last: WorkoutSet, t: ProgressionTarget): WorkoutSet {
  return {
    ...last,
    weight_kg: t.weight_kg,
    reps: t.kind === "reps" && t.reps !== null ? t.reps : last.reps,
    duration_s: t.kind === "hold" && t.seconds !== null ? t.seconds : last.duration_s,
    rpe: t.rpe ?? last.rpe,
  };
}

/** The target for set n (0-based): last time's set n, or its last set when doing more sets. */
export function targetFor(prev: WorkoutSet[], n: number): WorkoutSet | null {
  if (prev.length === 0) return null;
  return prev[Math.min(n, prev.length - 1)];
}

/** The exercise after `current` in the program's next session (for "Next up"). */
export function nextInPlan(items: string[], current: string | undefined): string | null {
  if (!current) return items[0] ?? null;
  const i = items.findIndex((n) => n.toLowerCase() === current.toLowerCase());
  return i >= 0 ? items[i + 1] ?? null : null;
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
