/**
 * First run (v1.2): a System intro screen, three short steps, then the reveal.
 *
 * Intro: the trainer big on screen over the theme's landing art, with Begin and
 * "Restore my data" (backups found on this PC).
 * 1. Your body: empty fields, no made-up numbers; goal weight is optional.
 * 2. Your goal in plain words, how active you are and how many days a week.
 * 3. Your kit (quests, programs and skills only use what is ticked).
 * Reveal: rank, daily targets (formula details on request), trainer, the first quest and an
 * optional 5-minute baseline test. The weight from step 1 is saved as the first weigh-in.
 *
 * `ProfileForm` (the same fields on one form) is also used in Settings.
 */
import type { BaselineIn, BaselineOut, EquipmentChoice, Focus, Profile, ProfileIn, QuestItem, Units } from "@ascend/shared";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";

import { api } from "../api/client";
import { BackupsPanel } from "../components/BackupsPanel";
import { TrainerPicker, TrainerPortrait, useTrainer } from "../components/Trainer";
import { SystemWindow } from "../components/SystemWindow";
import { RankBadge } from "../components/XpBar";
import { kcal } from "../lib/format";
import { CountUp } from "../lib/motion";
import { useAppTheme, useOptionalPrefs, usePrefs } from "../lib/prefs";
import { themeArt } from "../lib/themeArt";
import { CM_PER_IN, fromDisplayWeight, toDisplayWeight, weightUnit } from "../lib/units";

const ACTIVITY: { id: ProfileIn["activity"]; label: string }[] = [
  { id: "sedentary", label: "Mostly sitting (desk, little exercise)" },
  { id: "light", label: "A little active (1–3 sessions a week)" },
  { id: "moderate", label: "Active (3–5 sessions a week)" },
  { id: "active", label: "Very active (6–7 sessions a week)" },
  { id: "very_active", label: "Physical job plus training" },
];

/** Goals in plain words. Each sets the focus and the calorie direction (no Cut/Bulk to pick). */
export const GOALS: { id: string; label: string; hint: string; focus: Focus | null; goal: ProfileIn["goal"] }[] = [
  { id: "lose_fat", label: "Lose fat", hint: "Get leaner and keep your strength", focus: "fat_loss", goal: "cut" },
  { id: "build_muscle", label: "Build muscle", hint: "Grow bigger, eat a little more", focus: "muscle", goal: "bulk" },
  { id: "get_stronger", label: "Get stronger", hint: "Lift or pull more than before", focus: "strength", goal: "maintain" },
  { id: "skills", label: "Learn bodyweight skills", hint: "Pull-ups, handstands, levers", focus: "skills", goal: "maintain" },
  { id: "fit", label: "Just get fit", hint: "Feel better, move more, build a habit", focus: null, goal: "maintain" },
];

export const goalIdFor = (focus: Focus | null | undefined): string => GOALS.find((g) => g.focus === (focus ?? null))?.id ?? "fit";

export const EQUIPMENT: { id: EquipmentChoice; label: string; hint: string }[] = [
  { id: "none", label: "No equipment", hint: "Floor and body weight" },
  { id: "pullup_bar", label: "Pull-up bar", hint: "Pull-ups, hangs, levers" },
  { id: "rings", label: "Rings", hint: "Ring dips, rows, support holds" },
  { id: "dumbbells", label: "Dumbbells", hint: "Presses, rows, curls, lunges" },
  { id: "gym", label: "Full gym", hint: "Barbells, cables and machines" },
];

/** Equipment checkboxes. "Full gym" covers everything; nothing ticked means not stated. */
export function EquipmentPicker({ value, onChange }: { value: EquipmentChoice[]; onChange: (v: EquipmentChoice[]) => void }) {
  const toggle = (id: EquipmentChoice) => onChange(value.includes(id) ? value.filter((x) => x !== id) : [...value, id]);
  return (
    <fieldset>
      <legend className="mb-1.5 text-xs text-muted">Equipment you have</legend>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {EQUIPMENT.map((e) => {
          const on = value.includes(e.id);
          return (
            <label key={e.id} className={`flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors duration-150 ${on ? "border-accent bg-accent/10" : "border-line-2 hover:border-line-input"}`}>
              <input type="checkbox" className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]" checked={on} onChange={() => toggle(e.id)} />
              <span>
                <span className="block text-sm text-ink">{e.label}</span>
                <span className="block text-xs text-muted">{e.hint}</span>
              </span>
            </label>
          );
        })}
      </div>
      <p className="mt-2 text-xs text-muted">Train, Exercises, Skills, programs and quests only use what you tick.</p>
    </fieldset>
  );
}

function Choice<T extends string>({ legend, value, options, onChange }: { legend: string; value: T | ""; options: { id: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <fieldset>
      <legend className="mb-1.5 text-xs text-muted">{legend}</legend>
      <div className="flex gap-2">
        {options.map((o) => (
          <button key={o.id} type="button" aria-pressed={value === o.id} onClick={() => onChange(o.id)}
            className={`btn flex-1 border ${value === o.id ? "border-accent bg-accent/10 text-accent" : "border-line-2 text-muted hover:text-ink"}`}>{o.label}</button>
        ))}
      </div>
    </fieldset>
  );
}

function GoalChoice({ value, onChange }: { value: string; onChange: (id: string) => void }) {
  return (
    <fieldset>
      <legend className="mb-1.5 text-xs text-muted">Your goal</legend>
      <div className="grid gap-2 sm:grid-cols-2">
        {GOALS.map((g) => {
          const on = value === g.id;
          return (
            <button key={g.id} type="button" aria-pressed={on} onClick={() => onChange(g.id)}
              className={`rounded-md border p-3 text-left transition-colors duration-150 ${on ? "border-accent bg-accent/10" : "border-line-2 hover:border-line-input"}`}>
              <span className={`block text-sm font-medium ${on ? "text-accent" : "text-ink"}`}>{g.label}</span>
              <span className="block text-xs text-muted">{g.hint}</span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

/** A number field that starts empty (no made-up defaults); "" means not filled in. */
function NumberField({ label, unit, value, onChange, step = 1, required = true, optional = false }: {
  label: string; unit: string; value: string; onChange: (s: string) => void; step?: number; required?: boolean; optional?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs text-muted">{label}{optional && " (optional)"}</span>
      <div className="relative">
        <input className="input pr-10" type="number" inputMode="decimal" step={step} min={0} value={value} required={required}
          onChange={(e) => onChange(e.target.value)} />
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-faint">{unit}</span>
      </div>
    </label>
  );
}

interface Draft {
  name: string;
  age: string;
  sex: ProfileIn["sex"] | "";
  height: string;
  weight: string;
  target: string;
  goalId: string;
  activity: ProfileIn["activity"] | "";
  equipment: EquipmentChoice[];
}

const EMPTY: Draft = { name: "", age: "", sex: "", height: "", weight: "", target: "", goalId: "", activity: "", equipment: [] };

function draftFrom(p: ProfileIn, units: Units): Draft {
  const imperial = units === "imperial";
  return {
    name: p.name,
    age: String(p.age),
    sex: p.sex,
    height: String(imperial ? Math.round(p.height_cm / CM_PER_IN) : p.height_cm),
    weight: String(toDisplayWeight(p.weight_kg, units)),
    target: p.target_weight_kg ? String(toDisplayWeight(p.target_weight_kg, units)) : "",
    goalId: goalIdFor(p.focus),
    activity: p.activity,
    equipment: p.equipment ?? [],
  };
}

/** The profile the draft describes, or the first thing still missing. */
export function profileFrom(d: Draft, units: Units): ProfileIn | string {
  const imperial = units === "imperial";
  const age = Number(d.age);
  const height = Number(d.height);
  const weight = Number(d.weight);
  if (!d.age || !(age >= 13 && age <= 100)) return "Enter your age (13 or older).";
  if (!d.sex) return "Pick the body type for the calorie formula.";
  if (!d.height || height <= 0) return "Enter your height.";
  if (!d.weight || weight <= 0) return "Enter your weight.";
  const goal = GOALS.find((g) => g.id === d.goalId) ?? GOALS[GOALS.length - 1];
  const target = d.target === "" ? null : Math.round(fromDisplayWeight(Number(d.target), units) * 10) / 10;
  return {
    name: d.name.trim(),
    age: Math.round(age),
    sex: d.sex,
    height_cm: imperial ? Math.round(height * CM_PER_IN * 10) / 10 : height,
    weight_kg: Math.round(fromDisplayWeight(weight, units) * 10) / 10,
    target_weight_kg: target,
    goal: goal.goal,
    focus: goal.focus,
    activity: d.activity || "light",
    equipment: d.equipment,
  };
}

function BodyFields({ d, put, units }: { d: Draft; put: <K extends keyof Draft>(k: K, v: Draft[K]) => void; units: Units }) {
  const imperial = units === "imperial";
  return (
    <>
      <div className="grid grid-cols-3 gap-3">
        <NumberField label="Age" unit="yrs" value={d.age} onChange={(s) => put("age", s)} />
        <NumberField label="Height" unit={imperial ? "in" : "cm"} value={d.height} onChange={(s) => put("height", s)} />
        <NumberField label="Weight" unit={weightUnit(units)} step={0.1} value={d.weight} onChange={(s) => put("weight", s)} />
      </div>
      <Choice legend="Body type (for the calorie formula)" value={d.sex} options={[{ id: "male", label: "Male" }, { id: "female", label: "Female" }]} onChange={(v) => put("sex", v)} />
      <div className="w-1/2 pr-1.5">
        <NumberField label="Goal weight" unit={weightUnit(units)} step={0.1} value={d.target} onChange={(s) => put("target", s)} required={false} optional />
      </div>
    </>
  );
}

/** Profile form, used in Settings (onboarding asks the same over three steps). */
export function ProfileForm({ initial, onSaved, submitLabel }: { initial?: ProfileIn; onSaved: (p: Profile) => void; submitLabel: string }) {
  const units = useOptionalPrefs()?.settings.units ?? "metric";
  const [d, setD] = useState<Draft>(initial ? draftFrom(initial, units) : EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const put = <K extends keyof Draft>(k: K, v: Draft[K]) => setD((x) => ({ ...x, [k]: v }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    const body = profileFrom(d, units);
    if (typeof body === "string") {
      setError(body);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      onSaved(await api.saveProfile(body));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <label className="block">
        <span className="mb-1.5 block text-xs text-muted">Name (optional)</span>
        <input className="input" value={d.name} onChange={(e) => put("name", e.target.value)} placeholder="What should your trainer call you?" />
      </label>
      <BodyFields d={d} put={put} units={units} />
      <GoalChoice value={d.goalId} onChange={(id) => put("goalId", id)} />
      <label className="block">
        <span className="mb-1.5 block text-xs text-muted">How active are you?</span>
        <select className="input" value={d.activity} onChange={(e) => put("activity", e.target.value as ProfileIn["activity"])}>
          {ACTIVITY.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
        </select>
      </label>
      <EquipmentPicker value={d.equipment} onChange={(v) => put("equipment", v)} />
      {error && <p className="text-sm text-bad" role="alert">{error}</p>}
      <button className="btn-primary w-full" disabled={saving}>{saving ? "Saving…" : submitLabel}</button>
    </form>
  );
}

const TITLES = ["Your body", "Your goal", "Your kit"];
const SUBTITLES = [
  "Free, offline, no account. Everything stays on this PC.",
  "Pick what matters most. You can change it any time.",
  "Nothing you can't do with what you have will be suggested.",
];

type Stage = "landing" | "restore" | 1 | 2 | 3 | "reveal";

export function Onboarding({ onDone }: { onDone: () => void }) {
  const { settings, update } = usePrefs();
  const [stage, setStage] = useState<Stage>("landing");
  const [d, setD] = useState<Draft>(EMPTY);
  const [units, setUnits] = useState<Units>(settings.units);
  const [days, setDays] = useState(settings.sessions_per_week || 3);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const put = <K extends keyof Draft>(k: K, v: Draft[K]) => setD((x) => ({ ...x, [k]: v }));

  // Each step moves focus to its heading, so a screen reader announces the new step.
  useEffect(() => {
    if (typeof stage === "number") heading.current?.focus();
  }, [stage]);

  async function saveProfile() {
    const body = profileFrom(d, units);
    if (typeof body === "string") {
      setError(body);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const p = await api.saveProfile(body);
      await update({ units, sessions_per_week: days });
      // The weight just entered is the first weigh-in, so Progress has a start from day 1.
      await api.logWeight(body.weight_kg).catch(() => undefined);
      setProfile(p);
      setStage("reveal");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const next = (e: FormEvent) => {
    e.preventDefault();
    if (stage === 1) {
      const body = profileFrom({ ...d, goalId: d.goalId || "fit" }, units);
      if (typeof body === "string") return setError(body);
    }
    if (stage === 2 && !d.goalId) return setError("Pick a goal (or “Just get fit”).");
    setError(null);
    if (stage === 3) void saveProfile();
    else if (typeof stage === "number") setStage((stage + 1) as Stage);
  };
  const back = () => {
    setError(null);
    setStage((s) => (s === 1 ? "landing" : typeof s === "number" ? ((s - 1) as Stage) : s));
  };

  if (stage === "landing" || stage === "restore") {
    return <Landing restoring={stage === "restore"} onBegin={() => setStage(1)} onRestore={() => setStage("restore")} onBack={() => setStage("landing")} />;
  }

  return (
    <main className="relative grid min-h-full place-items-center overflow-hidden bg-bg p-8">
      <LandingArt dim />
      <div className={`relative w-full ${stage === "reveal" ? "max-w-[640px]" : "max-w-[560px]"}`}>
        {stage !== "reveal" ? (
          <div className="card panel-in p-8" key={stage}>
            <div className="mb-6">
              <div className="flex items-center justify-between">
                <div className="font-display text-sm font-bold tracking-[0.3em] text-accent">ASCEND</div>
                <Steps current={stage} />
              </div>
              <h1 ref={heading} tabIndex={-1} className="text-display-l mt-3 text-ink focus:outline-none">{TITLES[stage - 1]}</h1>
              <p className="mt-1 text-sm text-muted">{SUBTITLES[stage - 1]}</p>
            </div>
            <form onSubmit={next} noValidate className="space-y-5" aria-label={TITLES[stage - 1]}>
              {stage === 1 && (
                <>
                  <label className="block">
                    <span className="mb-1.5 block text-xs text-muted">Name (optional)</span>
                    <input className="input" value={d.name} onChange={(e) => put("name", e.target.value)} placeholder="What should your trainer call you?" autoFocus />
                  </label>
                  <Choice legend="Units" value={units} options={[{ id: "metric", label: "Metric (kg, cm)" }, { id: "imperial", label: "Imperial (lb, in)" }]} onChange={setUnits} />
                  <BodyFields d={d} put={put} units={units} />
                </>
              )}
              {stage === 2 && (
                <>
                  <GoalChoice value={d.goalId} onChange={(id) => put("goalId", id)} />
                  <label className="block">
                    <span className="mb-1.5 block text-xs text-muted">How active are you now?</span>
                    <select className="input" value={d.activity || "light"} onChange={(e) => put("activity", e.target.value as ProfileIn["activity"])}>
                      {ACTIVITY.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
                    </select>
                  </label>
                  <label className="block">
                    <span className="mb-1.5 block text-xs text-muted">Days a week you can train</span>
                    <select className="input" value={days} onChange={(e) => setDays(Number(e.target.value))}>
                      {[2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>{n} days{n === 3 ? " (a great start)" : ""}</option>)}
                    </select>
                  </label>
                </>
              )}
              {stage === 3 && <EquipmentPicker value={d.equipment} onChange={(v) => put("equipment", v)} />}
              {error && <p className="text-sm text-bad" role="alert">{error}</p>}
              <div className="flex items-center gap-2 pt-2">
                <button type="button" className="btn-ghost" onClick={back} disabled={busy}>Back</button>
                <button type="submit" className="btn-primary ml-auto px-6" disabled={busy}>
                  {stage === 3 ? (busy ? "Saving…" : "Finish") : "Next"}
                </button>
              </div>
            </form>
          </div>
        ) : (
          profile && <Awakened profile={profile} equipment={d.equipment} onDone={onDone} />
        )}
      </div>
    </main>
  );
}

/** The theme's landing art behind the first-run screens, under a scrim (none on Light/Dark). */
function LandingArt({ dim = false }: { dim?: boolean }) {
  const art = themeArt(useAppTheme(), "landing");
  if (!art) return null;
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0"
      style={{ backgroundImage: `linear-gradient(90deg, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.7) 45%, rgba(0,0,0,${dim ? 0.6 : 0.2}) 100%), url("${art}")`, backgroundSize: "cover", backgroundPosition: "center" }} />
  );
}

/** The System intro: the trainer big on screen, Begin or Restore my data. */
function Landing({ restoring, onBegin, onRestore, onBack }: {
  restoring: boolean; onBegin: () => void; onRestore: () => void; onBack: () => void;
}) {
  const trainer = useTrainer();
  const begin = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (!restoring) begin.current?.focus(); }, [restoring]);
  return (
    <main className="relative flex min-h-full items-center overflow-hidden bg-bg" data-testid="landing">
      <LandingArt />
      <div className="relative z-[1] grid w-full grid-cols-12 items-center gap-6 px-12 py-10">
        <div className="col-span-12 max-w-[520px] lg:col-span-6">
          <div className="font-display text-sm font-bold tracking-[0.3em] text-accent">[ SYSTEM ]</div>
          {!restoring ? (
            <>
              <h1 className="text-display-xl event-title mt-3 text-white">A new Hunter has awakened.</h1>
              <p className="event-title mt-3 text-base text-white/90">
                {trainer.name} will train you from where you are today: a daily quest, a plan for your kit and a rank that climbs with every set.
                Free, offline, and everything stays on this PC.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <button ref={begin} type="button" className="btn-primary px-8 py-3 text-base" onClick={onBegin}>Begin</button>
                <button type="button" className="btn-ghost border-white/40 bg-black/40 px-6 py-3 text-base text-white" onClick={onRestore}>Restore my data</button>
              </div>
            </>
          ) : (
            <div className="card mt-4 space-y-3 p-5">
              <h1 className="text-h2 text-ink">Restore my data</h1>
              <p className="text-sm text-muted">
                Backups ASCEND saved on this PC are listed below. To use a backup from another PC, copy its .ascendbak file into the
                backups folder inside ASCEND&apos;s data folder, then come back here. Your Strong or Hevy history can be imported later in Settings &gt; Data &amp; backups.
              </p>
              {/* A restore reloads the app, which then opens on the restored profile. */}
              <BackupsPanel />
              <button type="button" className="btn-ghost" onClick={onBack}>Back</button>
            </div>
          )}
        </div>
        {!restoring && (
          <div className="col-span-12 hidden justify-center lg:col-span-6 lg:flex">
            <TrainerPortrait mood="proud" size={320} />
          </div>
        )}
      </div>
    </main>
  );
}

function Awakened({ profile, equipment, onDone }: { profile: Profile; equipment: EquipmentChoice[]; onDone: () => void }) {
  const [quest, setQuest] = useState<QuestItem[] | null>(null);
  const [rank, setRank] = useState<{ rank: string; level: number } | null>(null);
  const [result, setResult] = useState<BaselineOut | null>(null);
  const [testing, setTesting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadGame = () => api.game().then((g) => {
    setQuest(g.quest);
    setRank({ rank: g.xp.rank, level: g.xp.level });
  }).catch(() => setQuest([]));
  useEffect(() => { void loadGame(); }, []);

  async function runBaseline(b: BaselineIn | null) {
    setError(null);
    if (!b) {
      setTesting(false);
      return;
    }
    setBusy(true);
    try {
      const r = await api.baseline(b);
      setResult(r);
      setRank({ rank: r.rank, level: r.level });
      setTesting(false);
      void loadGame();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (testing) {
    return (
      <div className="card panel-in p-8">
        <h1 className="text-display-l text-ink">Baseline test</h1>
        <p className="mb-5 mt-1 text-sm text-muted">One max effort each, rested in between. It seeds your rank, skill trees and plan targets. Leave out anything you can&apos;t do.</p>
        <BaselineStep equipment={equipment} busy={busy} error={error} onBack={() => setTesting(false)} onSubmit={(b) => void runBaseline(b)} />
      </div>
    );
  }
  return (
    <SystemWindow variant="notice" title="System" rank={rank?.rank} testId="awakened"
      actions={<button type="button" className="btn-primary px-6" onClick={onDone}>Enter ASCEND</button>}>
      <h1 className="text-display-l text-ink">You have been selected.</h1>
      <div className="mt-4 flex items-center gap-4">
        {rank && <RankBadge rank={rank.rank} size={52} />}
        <div className="text-sm text-muted">
          {rank ? <>Level <span className="font-semibold text-ink">{rank.level}</span> · Rank <span className="font-semibold text-ink">{rank.rank}</span></> : "Reading your rank…"}
          {result && (
            <div className="mt-0.5">Baseline logged: {result.sets_logged} test{result.sets_logged === 1 ? "" : "s"}, +{result.xp_awarded} XP{result.steps_unlocked.length ? ` · unlocked ${result.steps_unlocked.join(", ")}` : ""}.</div>
          )}
        </div>
      </div>
      {!result && (
        <div className="mt-4 rounded-lg border border-line-2 bg-panel-2 p-3">
          <p className="text-sm text-ink">Take the 5-minute baseline test? <span className="text-muted">(optional)</span></p>
          <p className="text-xs text-muted">Push-ups, a plank, squats and (with a bar) pull-ups. Your plan&apos;s targets then start from what you can really do.</p>
          <button type="button" className="btn-ghost mt-2 px-3 py-1.5 text-xs" onClick={() => setTesting(true)}>Take the test</button>
        </div>
      )}
      <div className="mt-5 grid grid-cols-2 gap-2">
        <Stat label="Daily target" value={profile.energy.kcal_target} unit="kcal" accent />
        <Stat label="Protein" value={profile.energy.protein_target_g} unit="g" />
      </div>
      <details className="mt-2 text-xs text-muted">
        <summary className="cursor-pointer text-accent">How is this worked out?</summary>
        <p className="mt-1">Resting burn (BMR) {kcal(profile.energy.bmr)} kcal × your activity = daily burn (TDEE) {kcal(profile.energy.tdee)} kcal, then adjusted for your goal. An estimate: real needs vary by a few hundred kcal, and it adapts to your weigh-ins.</p>
      </details>
      <div className="mt-5">
        <p className="text-sm font-semibold text-ink">Pick your trainer</p>
        <p className="mb-2 text-xs text-muted">Same advice from each, different voice. Change it any time in Settings.</p>
        <TrainerPicker />
      </div>
      <h2 className="mt-5 text-xs font-semibold uppercase tracking-wider text-faint">Your first daily quest</h2>
      {quest === null ? <p className="mt-2 text-sm text-muted">Generating…</p> : quest.length === 0 ? <p className="mt-2 text-sm text-muted">It appears on Today.</p> : (
        <ul className="mt-2 space-y-1.5">
          {quest.map((q) => (
            <li key={q.id} className="flex items-baseline justify-between gap-3 text-sm">
              <span className="text-ink">{q.title}</span>
              <span className="shrink-0 text-xs text-xp">+{q.xp} XP</span>
            </li>
          ))}
        </ul>
      )}
    </SystemWindow>
  );
}

/** "Step 1 of 3" with three small bars; the current and done steps are filled. */
function Steps({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-2 text-[11px] text-muted" aria-label={`Step ${current} of 3`} role="img">
      <span aria-hidden="true">Step {current} of 3</span>
      {[1, 2, 3].map((n) => (
        <span key={n} aria-hidden="true" className={`h-1 w-5 rounded-full transition-colors duration-200 ${n <= current ? "bg-accent" : "bg-line-2"}`} />
      ))}
    </div>
  );
}

/** A countdown (squats in 60 s) or a stopwatch (holds) that fills its field when stopped. */
function TestTimer({ mode, onDone, label }: { mode: "countdown" | "stopwatch"; onDone: (seconds: number) => void; label: string }) {
  const [running, setRunning] = useState(false);
  const [t, setT] = useState(0);
  const tick = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => () => { if (tick.current) clearInterval(tick.current); }, []);
  useEffect(() => {
    if (mode === "countdown" && running && t >= 60) {
      if (tick.current) clearInterval(tick.current);
      setRunning(false);
    }
  }, [mode, running, t]);
  const start = () => {
    setT(0);
    setRunning(true);
    tick.current = setInterval(() => setT((s) => s + 1), 1000);
  };
  const stop = () => {
    if (tick.current) clearInterval(tick.current);
    setRunning(false);
    if (mode === "stopwatch") onDone(t);
  };
  const shown = mode === "countdown" ? 60 - Math.min(60, t) : t;
  return (
    <span className="flex items-center gap-2">
      <span className="w-10 text-right font-mono text-xs tabular-nums text-muted" aria-live="off">{shown}s</span>
      <button type="button" className="btn-ghost px-2.5 py-1 text-xs" onClick={running ? stop : start}>
        {running ? "Stop" : mode === "countdown" ? (t >= 60 ? "Again" : "Start 60 s") : "Start"}
        <span className="sr-only"> {label}</span>
      </button>
    </span>
  );
}

function BaselineStep({ equipment, busy, error, onBack, onSubmit }: {
  equipment: EquipmentChoice[];
  busy: boolean;
  error: string | null;
  onBack: () => void;
  onSubmit: (b: BaselineIn | null) => void;
}) {
  const hasBar = equipment.length === 0 || equipment.some((e) => e === "pullup_bar" || e === "rings" || e === "gym");
  const [v, setV] = useState<Record<string, string>>({ pushups: "", pullups: "", dead_hang_s: "", plank_s: "", squats_60s: "" });
  const put = (k: string, s: string) => setV((x) => ({ ...x, [k]: s }));
  const n = (k: string) => (v[k] === "" ? null : Math.max(0, Math.round(Number(v[k]))));
  const row = (k: string, label: string, hint: string, unit: string, extra?: ReactNode) => (
    <div className="flex items-end gap-3">
      <label className="block flex-1">
        <span className="mb-1 block text-sm text-ink">{label}</span>
        <span className="mb-1.5 block text-xs text-muted">{hint}</span>
        <div className="relative">
          <input className="input pr-12" type="number" min={0} inputMode="numeric" value={v[k]} onChange={(e) => put(k, e.target.value)} placeholder="Skip" />
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-faint">{unit}</span>
        </div>
      </label>
      {extra && <div className="pb-1.5">{extra}</div>}
    </div>
  );
  function submit(e: FormEvent) {
    e.preventDefault();
    const body: BaselineIn = {
      pushups: n("pushups"),
      pullups: hasBar ? n("pullups") : null,
      dead_hang_s: hasBar ? n("dead_hang_s") : null,
      plank_s: n("plank_s"),
      squats_60s: n("squats_60s"),
    };
    const any = [body.pushups, body.pullups, body.dead_hang_s, body.plank_s, body.squats_60s].some((x) => x);
    onSubmit(any ? body : null);
  }
  return (
    <form onSubmit={submit} className="space-y-4" aria-label="Baseline test">
      {row("pushups", "Max strict push-ups", "Chest to a fist's height, full lockout. Stop at the first bad rep.", "reps")}
      {hasBar && row("pullups", "Max pull-ups", "Dead hang to chin over the bar.", "reps")}
      {hasBar && row("dead_hang_s", "Dead hang", "If pull-ups are not there yet: hang as long as you can.", "s",
        <TestTimer mode="stopwatch" label="dead hang timer" onDone={(s) => put("dead_hang_s", String(s))} />)}
      {row("plank_s", "Plank hold", "Forearms, straight line from head to heels.", "s",
        <TestTimer mode="stopwatch" label="plank timer" onDone={(s) => put("plank_s", String(s))} />)}
      {row("squats_60s", "Bodyweight squats in 60 s", "Hips to knee height, stand tall each rep.", "reps",
        <TestTimer mode="countdown" label="squat timer" onDone={() => undefined} />)}
      {error && <p className="text-sm text-bad" role="alert">{error}</p>}
      <div className="flex items-center gap-2 pt-2">
        <button type="button" className="btn-ghost ml-auto" onClick={onBack} disabled={busy}>Not now</button>
        <button type="submit" className="btn-primary px-6" disabled={busy}>{busy ? "Logging…" : "Log my baseline"}</button>
      </div>
    </form>
  );
}

function Stat({ label, value, unit, accent }: { label: string; value: number; unit: string; accent?: boolean }) {
  return (
    <div className="rounded-md border border-line bg-panel-2 p-3">
      <div className="text-[11px] uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-1 text-lg font-semibold ${accent ? "text-accent" : "text-ink"}`}>
        <CountUp value={value} format={kcal} /> <span className="text-xs font-normal text-muted">{unit}</span>
      </div>
    </div>
  );
}
