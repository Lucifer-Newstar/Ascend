import type { Profile, ProfileIn } from "@ascend/shared";
import { useState, type FormEvent } from "react";

import { api } from "../api/client";
import { kcal } from "../lib/format";
import { CountUp } from "../lib/motion";

const DEFAULTS: ProfileIn = { name: "", age: 21, sex: "male", height_cm: 172, weight_kg: 68, goal: "maintain", activity: "moderate" };

const ACTIVITY: { id: ProfileIn["activity"]; label: string }[] = [
  { id: "sedentary", label: "Sedentary (desk, little exercise)" },
  { id: "light", label: "Light (1–3 sessions a week)" },
  { id: "moderate", label: "Moderate (3–5 sessions a week)" },
  { id: "active", label: "Active (6–7 sessions a week)" },
  { id: "very_active", label: "Very active (physical job + training)" },
];

/** Profile form, used for first-run onboarding and in Settings. */
export function ProfileForm({ initial, onSaved, submitLabel }: { initial?: ProfileIn; onSaved: (p: Profile) => void; submitLabel: string }) {
  const [form, setForm] = useState<ProfileIn>(initial ?? DEFAULTS);
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

  const num = (k: "age" | "height_cm" | "weight_kg", label: string, unit: string) => (
    <label className="block">
      <span className="mb-1.5 block text-xs text-muted">{label}</span>
      <div className="relative">
        <input className="input pr-10" type="number" value={form[k]} onChange={(e) => set(k, Number(e.target.value))} required />
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-faint">{unit}</span>
      </div>
    </label>
  );

  return (
    <form onSubmit={submit} className="space-y-4">
      <label className="block">
        <span className="mb-1.5 block text-xs text-muted">Name (optional)</span>
        <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="What should the coach call you?" />
      </label>
      <div className="grid grid-cols-3 gap-3">
        {num("age", "Age", "yrs")}
        {num("height_cm", "Height", "cm")}
        {num("weight_kg", "Weight", "kg")}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <fieldset>
          <legend className="mb-1.5 text-xs text-muted">Sex (for the BMR formula)</legend>
          <div className="flex gap-2">
            {(["male", "female"] as const).map((s) => (
              <button key={s} type="button" aria-pressed={form.sex === s} onClick={() => set("sex", s)} className={`btn flex-1 border capitalize ${form.sex === s ? "border-accent bg-accent/10 text-accent" : "border-line-2 text-muted"}`}>{s}</button>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend className="mb-1.5 text-xs text-muted">Goal</legend>
          <div className="flex gap-2">
            {(["cut", "maintain", "bulk"] as const).map((g) => (
              <button key={g} type="button" aria-pressed={form.goal === g} onClick={() => set("goal", g)} className={`btn flex-1 border capitalize ${form.goal === g ? "border-accent bg-accent/10 text-accent" : "border-line-2 text-muted"}`}>{g}</button>
            ))}
          </div>
        </fieldset>
      </div>
      <label className="block">
        <span className="mb-1.5 block text-xs text-muted">Activity level</span>
        <select className="input" value={form.activity} onChange={(e) => set("activity", e.target.value as ProfileIn["activity"])}>
          {ACTIVITY.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
        </select>
      </label>
      {error && <p className="text-sm text-bad">{error}</p>}
      <button className="btn-primary w-full" disabled={saving}>{saving ? "Saving…" : submitLabel}</button>
    </form>
  );
}

export function Onboarding({ onDone }: { onDone: () => void }) {
  const [result, setResult] = useState<Profile | null>(null);
  return (
    <div className="grid h-full place-items-center bg-[radial-gradient(ellipse_at_top,rgba(34,211,238,0.08),transparent_60%)] p-8">
      <div className="card panel-in w-full max-w-[520px] p-8">
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div className="font-display text-sm font-bold tracking-[0.3em] text-accent">ASCEND</div>
            <Steps current={result ? 2 : 1} />
          </div>
          <h1 className="mt-2 text-2xl font-semibold text-ink">{result ? "Your starting targets" : "Set up your profile"}</h1>
          <p className="mt-1 text-sm text-muted">
            {result ? "Calculated on this PC. You can change any of this later in Settings." : "Used only to estimate your calorie and protein targets. Stored locally."}
          </p>
        </div>
        {result ? (
          <div key="targets" className="page-enter space-y-5">
            <div className="grid grid-cols-3 gap-3">
              <Stat label="BMR" value={result.energy.bmr} unit="kcal" />
              <Stat label="TDEE" value={result.energy.tdee} unit="kcal" />
              <Stat label="Daily target" value={result.energy.kcal_target} unit="kcal" accent />
            </div>
            <Stat label="Protein target" value={result.energy.protein_target_g} unit="g / day" />
            <p className="rounded-lg border border-warn/30 bg-warn/[0.06] p-3 text-xs leading-relaxed text-warn">
              These are estimates from the Mifflin-St Jeor equation × an activity factor. Real needs vary by a few hundred kcal;
              later versions adapt the target to your weight trend.
            </p>
            <button type="button" className="btn-primary w-full" onClick={onDone}>Enter ASCEND</button>
          </div>
        ) : (
          <ProfileForm onSaved={setResult} submitLabel="Calculate my targets" />
        )}
      </div>
    </div>
  );
}

/** "Step 1 of 2" with two small bars; the current and done steps are filled. */
function Steps({ current }: { current: 1 | 2 }) {
  return (
    <div className="flex items-center gap-2 text-[11px] text-muted" aria-label={`Step ${current} of 2`} role="img">
      <span aria-hidden="true">Step {current} of 2</span>
      {[1, 2].map((n) => (
        <span key={n} aria-hidden="true" className={`h-1 w-6 rounded-full ${n <= current ? "bg-accent" : "bg-line-2"}`} />
      ))}
    </div>
  );
}

function Stat({ label, value, unit, accent }: { label: string; value: number; unit: string; accent?: boolean }) {
  return (
    <div className="rounded-lg border border-line bg-panel-2 p-3">
      <div className="text-[11px] uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-1 text-xl font-semibold ${accent ? "text-accent" : "text-ink"}`}>
        <CountUp value={value} format={kcal} /> <span className="text-xs font-normal text-muted">{unit}</span>
      </div>
    </div>
  );
}
