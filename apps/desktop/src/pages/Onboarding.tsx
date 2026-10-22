/**
 * First run ("Awakening"): five short steps, every one skippable, nothing behind a wall.
 *
 * 1. Name, units and body data.  2. Focus, calorie goal, activity and days per week.
 * 3. Equipment checklist (quests and skill suggestions only use what is ticked).
 * 4. Baseline test: max push-ups, pull-ups or a dead hang, a plank and squats in 60 s,
 *    logged as one real session, so it seeds XP and rank, the skill trees and the stats.
 * 5. "[SYSTEM] You have been selected": rank, starting targets and the first daily quest.
 *
 * `ProfileForm` (the same fields on one form) is also used in Settings.
 */
import type { BaselineIn, BaselineOut, EquipmentChoice, Focus, Profile, ProfileIn, QuestItem, Units } from "@ascend/shared";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";

import { api } from "../api/client";
import { SystemWindow } from "../components/SystemWindow";
import { RankBadge } from "../components/XpBar";
import { kcal } from "../lib/format";
import { CountUp } from "../lib/motion";
import { usePrefs } from "../lib/prefs";
import { CM_PER_IN, fromDisplayWeight, toDisplayWeight, weightUnit } from "../lib/units";

const DEFAULTS: ProfileIn = { name: "", age: 21, sex: "male", height_cm: 172, weight_kg: 68, goal: "maintain", activity: "moderate", focus: "strength", equipment: [] };

const ACTIVITY: { id: ProfileIn["activity"]; label: string }[] = [
  { id: "sedentary", label: "Sedentary (desk, little exercise)" },
  { id: "light", label: "Light (1–3 sessions a week)" },
  { id: "moderate", label: "Moderate (3–5 sessions a week)" },
  { id: "active", label: "Active (6–7 sessions a week)" },
  { id: "very_active", label: "Very active (physical job + training)" },
];

export const FOCUS: { id: Focus; label: string; hint: string; goal: ProfileIn["goal"] }[] = [
  { id: "strength", label: "Strength", hint: "Heavier lifts, low reps", goal: "maintain" },
  { id: "muscle", label: "Muscle", hint: "Size: more volume, a small surplus", goal: "bulk" },
  { id: "skills", label: "Skills", hint: "Calisthenics: levers, handstands, muscle-ups", goal: "maintain" },
  { id: "fat_loss", label: "Fat loss", hint: "Keep strength in a deficit", goal: "cut" },
];

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
                <span className={`block text-sm ${on ? "text-ink" : "text-ink"}`}>{e.label}</span>
                <span className="block text-xs text-muted">{e.hint}</span>
              </span>
            </label>
          );
        })}
      </div>
      <p className="mt-2 text-xs text-muted">Quests and skill suggestions only use what you tick. Nothing ticked: nothing is filtered.</p>
    </fieldset>
  );
}

function Choice<T extends string>({ legend, value, options, onChange }: { legend: string; value: T; options: { id: T; label: string }[]; onChange: (v: T) => void }) {
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

function BodyFields({ form, set, units }: { form: ProfileIn; set: <K extends keyof ProfileIn>(k: K, v: ProfileIn[K]) => void; units: Units }) {
  const imperial = units === "imperial";
  const height = imperial ? Math.round(form.height_cm / CM_PER_IN) : form.height_cm;
  const weight = toDisplayWeight(form.weight_kg, units);
  // Keyed by units: switching units re-reads the stored kg/cm; typing never round-trips.
  return (
    <div className="grid grid-cols-3 gap-3">
      <NumberInput label="Age" unit="yrs" initial={form.age} onChange={(n) => set("age", n)} />
      <NumberInput key={`h-${units}`} label="Height" unit={imperial ? "in" : "cm"} initial={height} onChange={(n) => set("height_cm", imperial ? Math.round(n * CM_PER_IN * 10) / 10 : n)} />
      <NumberInput key={`w-${units}`} label="Weight" unit={weightUnit(units)} step={0.1} initial={weight} onChange={(n) => set("weight_kg", Math.round(fromDisplayWeight(n, units) * 10) / 10)} />
    </div>
  );
}

function NumberInput({ label, unit, initial, onChange, step = 1 }: { label: string; unit: string; initial: number; onChange: (n: number) => void; step?: number }) {
  const [text, setText] = useState(String(initial));
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs text-muted">{label}</span>
      <div className="relative">
        <input className="input pr-10" type="number" step={step} value={text} required
          onChange={(e) => { setText(e.target.value); if (e.target.value !== "") onChange(Number(e.target.value)); }} />
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-faint">{unit}</span>
      </div>
    </label>
  );
}

/** Profile form, used in Settings (onboarding asks the same over several steps). */
export function ProfileForm({ initial, onSaved, submitLabel }: { initial?: ProfileIn; onSaved: (p: Profile) => void; submitLabel: string }) {
  const [form, setForm] = useState<ProfileIn>({ ...DEFAULTS, focus: null, ...initial });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = <K extends keyof ProfileIn>(k: K, v: ProfileIn[K]) => setForm((f) => ({ ...f, [k]: v }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      onSaved(await api.saveProfile(form));
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
        <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="What should the coach call you?" />
      </label>
      <BodyFields form={form} set={set} units="metric" />
      <div className="grid grid-cols-2 gap-3">
        <Choice legend="Sex (for the BMR formula)" value={form.sex} options={[{ id: "male", label: "Male" }, { id: "female", label: "Female" }]} onChange={(v) => set("sex", v)} />
        <Choice legend="Calorie goal" value={form.goal} options={[{ id: "cut", label: "Cut" }, { id: "maintain", label: "Maintain" }, { id: "bulk", label: "Bulk" }]} onChange={(v) => set("goal", v)} />
      </div>
      <label className="block">
        <span className="mb-1.5 block text-xs text-muted">Activity level</span>
        <select className="input" value={form.activity} onChange={(e) => set("activity", e.target.value as ProfileIn["activity"])}>
          {ACTIVITY.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
        </select>
      </label>
      <EquipmentPicker value={form.equipment ?? []} onChange={(v) => set("equipment", v)} />
      {error && <p className="text-sm text-bad">{error}</p>}
      <button className="btn-primary w-full" disabled={saving}>{saving ? "Saving…" : submitLabel}</button>
    </form>
  );
}

const TITLES = ["Who is training?", "What are you training for?", "What can you train with?", "Baseline test", "Awakened"];
const SUBTITLES = [
  "Free, offline, no account. Everything stays on this PC.",
  "This sets your calorie estimate and what the daily quest leans towards.",
  "Never suggested: anything you cannot do with what you have.",
  "One max effort each, rested in between. It seeds your rank, skill trees and stats. Skip what you cannot do.",
  "",
];

type Step = 1 | 2 | 3 | 4 | 5;

export function Onboarding({ onDone }: { onDone: () => void }) {
  const { settings, update } = usePrefs();
  const [step, setStep] = useState<Step>(1);
  const [form, setForm] = useState<ProfileIn>(DEFAULTS);
  const [units, setUnits] = useState<Units>(settings.units);
  const [days, setDays] = useState(settings.sessions_per_week || 3);
  const [goalTouched, setGoalTouched] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [result, setResult] = useState<BaselineOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const set = <K extends keyof ProfileIn>(k: K, v: ProfileIn[K]) => setForm((f) => ({ ...f, [k]: v }));

  // Each step moves focus to its heading, so a screen reader announces the new step.
  useEffect(() => {
    if (step > 1) heading.current?.focus();
  }, [step]);

  async function saveProfile() {
    setBusy(true);
    setError(null);
    try {
      const p = await api.saveProfile(form);
      await update({ units, sessions_per_week: days });
      setProfile(p);
      setStep(4);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function runBaseline(b: BaselineIn | null) {
    setError(null);
    if (!b) {
      setStep(5);
      return;
    }
    setBusy(true);
    try {
      setResult(await api.baseline(b));
      setStep(5);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const next = (e: FormEvent) => {
    e.preventDefault();
    if (step === 3) void saveProfile();
    else setStep((s) => (s + 1) as Step);
  };
  const back = () => setStep((s) => Math.max(1, s - 1) as Step);

  return (
    <main className="grid min-h-full place-items-center bg-[radial-gradient(ellipse_at_top,color-mix(in_srgb,var(--color-accent)_9%,transparent),transparent_60%)] p-8">
      <div className={`w-full ${step === 5 ? "max-w-[620px]" : "max-w-[560px]"}`}>
        {step < 5 ? (
          <div className="card panel-in p-8" key={step}>
            <div className="mb-6">
              <div className="flex items-center justify-between">
                <div className="font-display text-sm font-bold tracking-[0.3em] text-accent">ASCEND</div>
                <Steps current={step} />
              </div>
              <h1 ref={heading} tabIndex={-1} className="text-display-l mt-3 text-ink focus:outline-none">{TITLES[step - 1]}</h1>
              <p className="mt-1 text-sm text-muted">{SUBTITLES[step - 1]}</p>
            </div>
            {step === 4 ? (
              <BaselineStep form={form} units={units} equipment={form.equipment ?? []} busy={busy} error={error} onBack={back} onSubmit={runBaseline} />
            ) : (
              <form onSubmit={next} className="space-y-5" aria-label={TITLES[step - 1]}>
                {step === 1 && (
                  <>
                    <label className="block">
                      <span className="mb-1.5 block text-xs text-muted">Name (optional)</span>
                      <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="What should the coach call you?" autoFocus />
                    </label>
                    <Choice legend="Units" value={units} options={[{ id: "metric", label: "Metric (kg, cm)" }, { id: "imperial", label: "Imperial (lb, in)" }]} onChange={setUnits} />
                    <BodyFields form={form} set={set} units={units} />
                    <Choice legend="Sex (for the BMR formula)" value={form.sex} options={[{ id: "male", label: "Male" }, { id: "female", label: "Female" }]} onChange={(v) => set("sex", v)} />
                  </>
                )}
                {step === 2 && (
                  <>
                    <fieldset>
                      <legend className="mb-1.5 text-xs text-muted">Focus</legend>
                      <div className="grid grid-cols-2 gap-2">
                        {FOCUS.map((f) => (
                          <button key={f.id} type="button" aria-pressed={form.focus === f.id}
                            onClick={() => { set("focus", f.id); if (!goalTouched) set("goal", f.goal); }}
                            className={`rounded-md border p-3 text-left transition-colors duration-150 ${form.focus === f.id ? "border-accent bg-accent/10" : "border-line-2 hover:border-line-input"}`}>
                            <span className={`block text-sm font-medium ${form.focus === f.id ? "text-accent" : "text-ink"}`}>{f.label}</span>
                            <span className="block text-xs text-muted">{f.hint}</span>
                          </button>
                        ))}
                      </div>
                    </fieldset>
                    <Choice legend="Calorie goal" value={form.goal} options={[{ id: "cut", label: "Cut" }, { id: "maintain", label: "Maintain" }, { id: "bulk", label: "Bulk" }]} onChange={(v) => { setGoalTouched(true); set("goal", v); }} />
                    <div className="grid grid-cols-[1.7fr_1fr] gap-3">
                      <label className="block">
                        <span className="mb-1.5 block text-xs text-muted">Activity level</span>
                        <select className="input" value={form.activity} onChange={(e) => set("activity", e.target.value as ProfileIn["activity"])}>
                          {ACTIVITY.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
                        </select>
                      </label>
                      <label className="block">
                        <span className="mb-1.5 block text-xs text-muted">Training days per week</span>
                        <select className="input" value={days} onChange={(e) => setDays(Number(e.target.value))}>
                          {[1, 2, 3, 4, 5, 6, 7].map((n) => <option key={n} value={n}>{n}</option>)}
                        </select>
                      </label>
                    </div>
                  </>
                )}
                {step === 3 && <EquipmentPicker value={form.equipment ?? []} onChange={(v) => set("equipment", v)} />}
                {error && <p className="text-sm text-bad" role="alert">{error}</p>}
                <Nav step={step} busy={busy} onBack={back} onSkip={step > 1 ? () => (step === 3 ? void saveProfile() : setStep((s) => (s + 1) as Step)) : undefined}
                  nextLabel={step === 3 ? (busy ? "Saving…" : "Save and continue") : "Continue"} />
              </form>
            )}
          </div>
        ) : (
          profile && <Awakened profile={profile} result={result} onDone={onDone} />
        )}
      </div>
    </main>
  );
}

function Nav({ step, busy, onBack, onSkip, nextLabel }: { step: number; busy: boolean; onBack: () => void; onSkip?: () => void; nextLabel: string }) {
  return (
    <div className="flex items-center gap-2 pt-2">
      {step > 1 && <button type="button" className="btn-ghost" onClick={onBack} disabled={busy}>Back</button>}
      {onSkip && <button type="button" className="btn-ghost ml-auto" onClick={onSkip} disabled={busy}>Skip</button>}
      <button type="submit" className={`btn-primary px-6 ${onSkip ? "" : "ml-auto"}`} disabled={busy}>{nextLabel}</button>
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

function BaselineStep({ form, units, equipment, busy, error, onBack, onSubmit }: {
  form: ProfileIn;
  units: Units;
  equipment: EquipmentChoice[];
  busy: boolean;
  error: string | null;
  onBack: () => void;
  onSubmit: (b: BaselineIn | null) => void;
}) {
  const hasBar = equipment.length === 0 || equipment.some((e) => e === "pullup_bar" || e === "rings" || e === "gym");
  const [v, setV] = useState<Record<string, string>>({ pushups: "", pullups: "", dead_hang_s: "", plank_s: "", squats_60s: "", bodyweight: String(toDisplayWeight(form.weight_kg, units)) });
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
    const bw = v.bodyweight === "" ? null : fromDisplayWeight(Number(v.bodyweight), units);
    const body: BaselineIn = {
      pushups: n("pushups"),
      pullups: hasBar ? n("pullups") : null,
      dead_hang_s: hasBar ? n("dead_hang_s") : null,
      plank_s: n("plank_s"),
      squats_60s: n("squats_60s"),
      bodyweight_kg: bw && Math.abs(bw - form.weight_kg) > 0.05 ? Math.round(bw * 10) / 10 : null,
    };
    const any = [body.pushups, body.pullups, body.dead_hang_s, body.plank_s, body.squats_60s, body.bodyweight_kg].some((x) => x);
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
      <label className="block">
        <span className="mb-1.5 block text-xs text-muted">Body weight today (optional)</span>
        <div className="relative w-40">
          <input className="input pr-10" type="number" step={0.1} value={v.bodyweight} onChange={(e) => put("bodyweight", e.target.value)} />
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-faint">{weightUnit(units)}</span>
        </div>
      </label>
      {error && <p className="text-sm text-bad" role="alert">{error}</p>}
      <div className="flex items-center gap-2 pt-2">
        <button type="button" className="btn-ghost" onClick={onBack} disabled={busy}>Back</button>
        <button type="button" className="btn-ghost ml-auto" onClick={() => onSubmit(null)} disabled={busy}>Skip the test</button>
        <button type="submit" className="btn-primary px-6" disabled={busy}>{busy ? "Logging…" : "Log my baseline"}</button>
      </div>
    </form>
  );
}

function Awakened({ profile, result, onDone }: { profile: Profile; result: BaselineOut | null; onDone: () => void }) {
  const [quest, setQuest] = useState<QuestItem[] | null>(null);
  const [rank, setRank] = useState<{ rank: string; level: number } | null>(result ? { rank: result.rank, level: result.level } : null);
  useEffect(() => {
    api.game().then((g) => {
      setQuest(g.quest);
      setRank({ rank: g.xp.rank, level: g.xp.level });
    }).catch(() => setQuest([]));
  }, []);
  const enter = useRef<HTMLButtonElement>(null);
  return (
    <SystemWindow variant="notice" title="System" rank={rank?.rank} testId="awakened"
      actions={<button ref={enter} type="button" className="btn-primary px-6" onClick={onDone}>Enter ASCEND</button>}>
      <h1 className="text-display-l text-ink">You have been selected.</h1>
      <div className="mt-4 flex items-center gap-4">
        {rank && <RankBadge rank={rank.rank} size={52} />}
        <div className="text-sm text-muted">
          {rank ? <>Level <span className="font-semibold text-ink">{rank.level}</span> · Rank <span className="font-semibold text-ink">{rank.rank}</span></> : "Reading your rank…"}
          {result ? (
            <div className="mt-0.5">Baseline logged: {result.sets_logged} test{result.sets_logged === 1 ? "" : "s"}, +{result.xp_awarded} XP{result.steps_unlocked.length ? ` · unlocked ${result.steps_unlocked.join(", ")}` : ""}.</div>
          ) : (
            <div className="mt-0.5">No baseline yet: your first logged sets will seed your rank and skill trees.</div>
          )}
        </div>
      </div>
      <div className="mt-5 grid grid-cols-4 gap-2">
        <Stat label="BMR" value={profile.energy.bmr} unit="kcal" />
        <Stat label="TDEE" value={profile.energy.tdee} unit="kcal" />
        <Stat label="Daily target" value={profile.energy.kcal_target} unit="kcal" accent />
        <Stat label="Protein" value={profile.energy.protein_target_g} unit="g" />
      </div>
      <p className="mt-2 text-xs text-muted">Estimates from the Mifflin-St Jeor equation × an activity factor. Real needs vary by a few hundred kcal.</p>
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

/** "Step 1 of 5" with five small bars; the current and done steps are filled. */
function Steps({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-2 text-[11px] text-muted" aria-label={`Step ${current} of 5`} role="img">
      <span aria-hidden="true">Step {current} of 5</span>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} aria-hidden="true" className={`h-1 w-5 rounded-full transition-colors duration-200 ${n <= current ? "bg-accent" : "bg-line-2"}`} />
      ))}
    </div>
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
