/**
 * Planner (v1.1): build a week of training from rules, check a goal
 * before you commit to it, and keep what you build. Every plan comes from the sidecar's
 * deterministic planner (workout-gen); the meal planner lives on Fuel (v1.2). With the AI on, the local model may
 * reword the notes, never the numbers. Flags come from the goal checks (ICMR-NIN 2024,
 * ISSN, ACSM): a "block" flag means the plan was adjusted to stay safe.
 */
import type { CustomProgram, GoalCheck, PlanEquipment, PlanExperience, PlanFlag, PlanFocus, PlanSlot, WorkoutPlan } from "@ascend/shared";
import { useEffect, useState, type FormEvent } from "react";

import { api } from "../api/client";
import { PageGrid, Panel } from "../components/Page";
import { useToast } from "../components/Toast";
import { useLoadout } from "../lib/loadout";
import { usePrefs } from "../lib/prefs";
import { useApi } from "../lib/useApi";

const FOCUS: { value: PlanFocus; label: string }[] = [
  { value: "general", label: "General fitness" },
  { value: "strength", label: "Strength" },
  { value: "muscle", label: "Muscle" },
  { value: "fat_loss", label: "Fat loss" },
  { value: "skills", label: "Calisthenics skills" },
];
const EQUIPMENT: { value: PlanEquipment; label: string }[] = [
  { value: "none", label: "No equipment" },
  { value: "pullup_bar", label: "Pull-up bar" },
  { value: "rings", label: "Rings" },
  { value: "dumbbells", label: "Dumbbells" },
  { value: "bench", label: "Bench" },
  { value: "gym", label: "Full gym" },
];
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** "3×8–12", or "3×30–45 s" for a hold (v1.3: holds are dosed in seconds). */
export function slotTarget(s: PlanSlot): string {
  const range = `${s.rep_low}${s.rep_high !== s.rep_low ? `–${s.rep_high}` : ""}`;
  return `${s.sets}×${range}${s.measure === "hold" ? " s" : ""}`;
}
const TONE: Record<PlanFlag["severity"], string> = { info: "border-line-2 text-muted", warn: "border-warn/60 text-warn", block: "border-bad/60 text-bad" };

export function Flags({ flags }: { flags: PlanFlag[] }) {
  if (!flags.length) return null;
  return (
    <ul className="space-y-1.5" aria-label="Checks">
      {flags.map((f) => (
        <li key={f.code} className={`rounded-md border px-2.5 py-1.5 text-xs ${TONE[f.severity]}`} data-severity={f.severity}>
          <span className="font-semibold uppercase tracking-wider">{f.severity === "block" ? "Adjusted" : f.severity === "warn" ? "Careful" : "Note"}</span> · {f.message}
        </li>
      ))}
    </ul>
  );
}

export function PlannerPage({ onChanged }: { onChanged: () => void }) {
  return (
    <PageGrid label="Planner">
      <WorkoutPlanner onChanged={onChanged} />
      <GoalChecker />
    </PageGrid>
  );
}

function WorkoutPlanner({ onChanged }: { onChanged: () => void }) {
  const toast = useToast();
  const { settings } = usePrefs();
  const [focus, setFocus] = useState<PlanFocus>("general");
  const [experience, setExperience] = useState<PlanExperience | "">("");
  const [days, setDays] = useState(3);
  const [minutes, setMinutes] = useState(60);
  const [equipment, setEquipment] = useState<PlanEquipment[]>(["gym"]);
  // v1.2: start from the loadout chosen at setup, not "Full gym".
  const loadout = useLoadout();
  const [kitApplied, setKitApplied] = useState(false);
  useEffect(() => {
    if (kitApplied || !loadout.loaded) return;
    setKitApplied(true);
    const fromKit = (loadout.choices ?? []).filter((c): c is PlanEquipment => EQUIPMENT.some((q) => q.value === c));
    if (fromKit.length) setEquipment(fromKit);
  }, [kitApplied, loadout.loaded, loadout.choices]);
  const [plan, setPlan] = useState<WorkoutPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const saved = useApi(api.customPrograms, []);

  async function build(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      setPlan(await api.planWorkout({ focus, experience: experience || null, days_per_week: days, minutes, equipment, use_ai: Boolean(settings.ai_enabled) }));
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function keep(follow: boolean) {
    if (!plan) return;
    try {
      const p = await api.saveProgram(plan.draft);
      if (follow) await api.followProgram(p.id);
      toast(follow ? `Following ${p.name}. Train shows today's session.` : `Saved ${p.name}`, "info");
      setPlan(null);
      saved.reload();
      onChanged();
    } catch (err) {
      toast((err as Error).message, "error");
    }
  }

  const toggle = (v: PlanEquipment) => setEquipment((list) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]));

  return (
    <Panel id="plan-workout" index={0} className="col-span-12 xl:col-span-7" title="Workout planner"
      hint="A week built from the exercise library for your days, time and equipment.">
      <form onSubmit={build} className="grid gap-3 sm:grid-cols-2" aria-label="Workout planner">
        <label className="text-xs text-muted">Goal
          <select className="input mt-1 w-full" value={focus} onChange={(e) => setFocus(e.target.value as PlanFocus)}>
            {FOCUS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
        </label>
        <label className="text-xs text-muted">Experience
          <select className="input mt-1 w-full" value={experience} onChange={(e) => setExperience(e.target.value as PlanExperience | "")}>
            <option value="">From my profile</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </label>
        <label className="text-xs text-muted">Days a week
          <input type="number" className="input mt-1 w-full" min={1} max={7} value={days} onChange={(e) => setDays(Number(e.target.value))} />
        </label>
        <label className="text-xs text-muted">Minutes a session
          <input type="number" className="input mt-1 w-full" min={15} max={180} step={5} value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} />
        </label>
        <fieldset className="sm:col-span-2">
          <legend className="text-xs text-muted">Equipment</legend>
          <div className="mt-1 flex flex-wrap gap-2">
            {EQUIPMENT.map((q) => (
              <label key={q.value} className={`chip cursor-pointer ${equipment.includes(q.value) ? "border-accent text-ink" : ""}`}>
                <input type="checkbox" className="sr-only" checked={equipment.includes(q.value)} onChange={() => toggle(q.value)} />
                {q.label}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="sm:col-span-2">
          <button type="submit" className="btn-primary" disabled={busy || !equipment.length}>{busy ? "Building…" : "Build my week"}</button>
        </div>
      </form>

      {plan && (
        <div className="mt-4 space-y-3" data-testid="workout-draft">
          <div>
            <h3 className="text-sm font-semibold text-ink">{plan.draft.name}</h3>
            {plan.draft.summary && <p className="text-xs text-muted">{plan.draft.summary}</p>}
          </div>
          <Flags flags={plan.flags} />
          <div className="grid gap-3 md:grid-cols-2">
            {plan.draft.days.map((d) => (
              <section key={d.key} className="rounded-lg border border-line-2 p-3" aria-label={`${DAYS[d.weekday] ?? ""} ${d.name}`}>
                <p className="text-[11px] uppercase tracking-wider text-accent">{DAYS[d.weekday] ?? ""} · {d.name}</p>
                <ul className="mt-1 space-y-0.5 text-xs text-ink">
                  {d.slots.map((s, i) => <li key={`${s.exercise}-${i}`}>{slotTarget(s)} {s.exercise}</li>)}
                </ul>
              </section>
            ))}
          </div>
          {(plan.draft.notes ?? []).length > 0 && <ul className="list-disc pl-4 text-xs text-muted">{plan.draft.notes!.map((n) => <li key={n}>{n}</li>)}</ul>}
          <p className="text-[11px] text-muted">{plan.phrased_by === "ollama" ? "Notes worded by the local AI · plan from rules" : "Built by rules"}</p>
          <div className="flex gap-2">
            <button type="button" className="btn-primary" onClick={() => void keep(true)}>Save and follow</button>
            <button type="button" className="btn-ghost" onClick={() => void keep(false)}>Save only</button>
          </div>
        </div>
      )}

      <SavedPrograms list={saved.data ?? []} onChanged={() => { saved.reload(); onChanged(); }} />
    </Panel>
  );
}

function SavedPrograms({ list, onChanged }: { list: CustomProgram[]; onChanged: () => void }) {
  const toast = useToast();
  if (!list.length) return null;
  return (
    <div className="mt-5 border-t border-line pt-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Your programs</h3>
      <ul className="mt-2 space-y-2">
        {list.map((p) => (
          <li key={p.id} className="flex items-center justify-between gap-2 text-sm text-ink">
            <span>{p.name} <span className="text-xs text-muted">· {p.days.length} days</span>{p.following && <span className="chip ml-2 border-good/60 text-good">Following</span>}</span>
            <span className="flex gap-2">
              {!p.following && <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={() => void api.followProgram(p.id).then(onChanged).catch((e: Error) => toast(e.message, "error"))}>Follow</button>}
              <button type="button" className="btn-ghost px-2 py-1 text-xs" aria-label={`Delete ${p.name}`} onClick={() => void api.deleteProgram(p.id).then(onChanged).catch((e: Error) => toast(e.message, "error"))}>Delete</button>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function GoalChecker() {
  const [weight, setWeight] = useState("");
  const [target, setTarget] = useState("");
  const [weeks, setWeeks] = useState("");
  const [result, setResult] = useState<GoalCheck | null>(null);
  const [error, setError] = useState<string | null>(null);
  const num = (s: string) => (s.trim() ? Number(s) : null);

  async function check(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      setResult(await api.goalCheck({ weight_kg: num(weight), target_weight_kg: num(target), weeks: num(weeks) }));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <Panel id="plan-goal" index={1} className="col-span-12 xl:col-span-5" title="Is my goal realistic?"
      hint="Checked against published rates: about 0.5 kg a week down is the safe pace (ICMR-NIN 2024).">
      <form onSubmit={check} className="grid grid-cols-3 gap-2" aria-label="Goal check">
        <label className="text-xs text-muted">Now (kg)<input className="input mt-1 w-full" inputMode="decimal" value={weight} onChange={(e) => setWeight(e.target.value)} /></label>
        <label className="text-xs text-muted">Goal (kg)<input className="input mt-1 w-full" inputMode="decimal" value={target} onChange={(e) => setTarget(e.target.value)} /></label>
        <label className="text-xs text-muted">In weeks<input className="input mt-1 w-full" inputMode="decimal" value={weeks} onChange={(e) => setWeeks(e.target.value)} /></label>
        <div className="col-span-3"><button type="submit" className="btn-primary">Check</button></div>
      </form>
      {error && <p role="alert" className="mt-2 text-xs text-bad">{error}</p>}
      {result && (
        <div className="mt-3 space-y-2" data-testid="goal-result">
          {result.flags.length ? <Flags flags={result.flags} /> : <p className="text-sm text-good">Realistic. Nothing to flag.</p>}
        </div>
      )}
    </Panel>
  );
}
