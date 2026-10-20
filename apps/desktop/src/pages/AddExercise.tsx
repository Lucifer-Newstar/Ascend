/**
 * "Add your own exercise": type a name, ASCEND proposes every field (library match,
 * rules, the local model if installed, wger.de only if allowed and asked), the user
 * reviews and confirms. Every field shows where its value came from; anything the
 * user changes becomes "You".
 */
import type { CustomExerciseIn, Difficulty, ExerciseAnalysis, FieldSource, Measure, Section } from "@ascend/shared";
import { useState, type ReactNode } from "react";

import { api } from "../api/client";
import { IconPlus, IconTrash } from "../components/Icons";
import { useToast } from "../components/Toast";
import { MUSCLE_LABEL } from "../lib/muscles";
import { usePrefs } from "../lib/prefs";
import { SECTION_TYPE_LABEL, SOURCE_LABEL } from "./Library";

export const EQUIPMENT_OPTIONS = [
  "bodyweight", "barbell", "dumbbell", "kettlebell", "cable", "machine", "band", "rings",
  "bar", "bench", "medicine_ball", "exercise_ball", "none", "other",
] as const;
const PATTERNS = ["push", "pull", "squat", "hinge", "lunge", "core", "isometric", "carry", "olympic", "locomotion", "mobility", "other"] as const;
const SECTIONS: Section[] = ["gym", "calisthenics", "cardio", "martial_arts", "flexibility", "meditation"];
const label = (s: string) => s.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

const AI_TEXT: Record<string, string> = {
  ok: "Local AI filled in",
  off: "Local AI is off in Settings: rules only",
  unavailable: "Local AI model not installed: rules only",
  error: "Local AI did not answer: rules only",
  invalid: "Local AI's answer did not pass the checks: rules only",
};
const ONLINE_TEXT: Record<string, string> = {
  ok: "wger.de filled in",
  not_found: "wger.de has no exercise with this exact name",
  error: "wger.de could not be reached",
};

export function toPayload(a: ExerciseAnalysis): CustomExerciseIn {
  return { name: a.name, ...a.proposal, field_sources: { ...a.field_sources }, attribution: a.attribution };
}

export function AddExerciseView({ onBack, onCreated, onOpenExisting }: {
  onBack: () => void;
  onCreated: (id: number) => void;
  onOpenExisting: (id: number) => void;
}) {
  const { settings } = usePrefs();
  const toast = useToast();
  const [name, setName] = useState("");
  const [equipment, setEquipment] = useState("");
  const [notes, setNotes] = useState("");
  const [online, setOnline] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<ExerciseAnalysis | null>(null);
  const [draft, setDraft] = useState<CustomExerciseIn | null>(null);

  async function analyse(e: React.FormEvent) {
    e.preventDefault();
    if (name.trim().length < 2) return;
    setBusy(true);
    setError(null);
    try {
      const a = await api.analyzeExercise({ name: name.trim(), equipment: equipment || null, notes, online: online && Boolean(settings.online_lookup) });
      setAnalysis(a);
      setDraft(toPayload(a));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!draft) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createExercise(draft);
      toast(`Added ${created.name} to your library`, "xp");
      onCreated(created.id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-4xl space-y-4">
      <button type="button" className="btn-ghost" onClick={onBack}>← All exercises</button>
      <section className="card p-5" aria-labelledby="add-title">
        <h2 id="add-title" className="card-title">Add your own exercise</h2>
        <p className="mt-1 text-xs text-muted">ASCEND suggests the details and shows where each one came from. You check them before anything is saved.</p>
        <form className="mt-4 grid gap-3 md:grid-cols-[2fr_1fr]" onSubmit={analyse}>
          <label className="block">
            <span className="mb-1.5 block text-xs text-muted">Exercise name</span>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Banded Pallof hold" maxLength={80} required minLength={2} />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs text-muted">Equipment (optional)</span>
            <select className="input" value={equipment} onChange={(e) => setEquipment(e.target.value)}>
              <option value="">Let ASCEND guess</option>
              {EQUIPMENT_OPTIONS.map((x) => <option key={x} value={x}>{label(x)}</option>)}
            </select>
          </label>
          <label className="block md:col-span-2">
            <span className="mb-1.5 block text-xs text-muted">Notes for the local AI (optional)</span>
            <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={300} placeholder="e.g. anti-rotation core hold with a band" />
          </label>
          <div className="flex flex-wrap items-center gap-3 md:col-span-2">
            {settings.online_lookup ? (
              <label className="flex items-center gap-2 text-xs text-muted">
                <input type="checkbox" className="accent-[var(--color-accent)]" checked={online} onChange={(e) => setOnline(e.target.checked)} />
                Also look up on wger.de (sends only the name)
              </label>
            ) : (
              <span className="text-xs text-faint">Online lookup is off (Settings). Everything runs on this PC.</span>
            )}
            <button type="submit" className="btn btn-primary ml-auto" disabled={busy || name.trim().length < 2}>
              {busy && !analysis ? "Checking…" : analysis ? "Check again" : "Suggest details"}
            </button>
          </div>
        </form>
        {error && <p role="alert" className="mt-3 text-sm text-bad">{error}</p>}
      </section>

      {analysis && draft && (
        <Review analysis={analysis} draft={draft} setDraft={setDraft} onSave={save} busy={busy} onOpenExisting={onOpenExisting} />
      )}
    </div>
  );
}

function Review({ analysis: a, draft, setDraft, onSave, busy, onOpenExisting }: {
  analysis: ExerciseAnalysis;
  draft: CustomExerciseIn;
  setDraft: (d: CustomExerciseIn) => void;
  onSave: () => void;
  busy: boolean;
  onOpenExisting: (id: number) => void;
}) {
  // Any edit makes that field the user's own.
  const edit = <K extends keyof CustomExerciseIn>(key: K, value: CustomExerciseIn[K], source = String(key)) =>
    setDraft({ ...draft, [key]: value, field_sources: { ...draft.field_sources, [source]: "user" } });
  const src = (key: string) => draft.field_sources[key] as FieldSource | undefined;
  const unit = draft.measure === "hold" ? "seconds" : "reps";
  const others = a.matches.filter((m) => m.id !== a.duplicate_of?.id);
  return (
    <>
      {a.duplicate_of && (
        <section className="card border-warn/50 p-4" role="alert">
          <p className="text-sm text-ink"><strong>{a.duplicate_of.name}</strong> is already in the library under this name.</p>
          <button type="button" className="btn-ghost mt-2" onClick={() => onOpenExisting(a.duplicate_of!.id)}>Open {a.duplicate_of.name}</button>
        </section>
      )}
      {others.length > 0 && (
        <section className="card p-4" aria-labelledby="similar-title">
          <h3 id="similar-title" className="text-[11px] uppercase tracking-wider text-faint">Similar exercises already in the library</h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {others.map((m) => (
              <li key={m.id}>
                <button type="button" className="chip hover:border-accent hover:text-accent" onClick={() => onOpenExisting(m.id)}>
                  {m.name} <span className="text-faint">· {Math.round(m.score * 100)}% match</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      <section className="card p-5" aria-labelledby="review-title">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 id="review-title" className="card-title">Check the details</h3>
          <p className="text-xs text-muted" role="status">
            {AI_TEXT[a.ai.status] ?? a.ai.status}{a.ai.status === "ok" ? ` ${a.ai.applied.length} field${a.ai.applied.length === 1 ? "" : "s"}` : ""}
            {ONLINE_TEXT[a.online.status] ? ` · ${ONLINE_TEXT[a.online.status]}` : ""}
          </p>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Field label="Name" source={src("name") ?? "user"}>
            <input className="input" value={draft.name} maxLength={80} onChange={(e) => edit("name", e.target.value)} />
          </Field>
          <Field label="Type" source={src("section")}>
            <select className="input" value={draft.section} onChange={(e) => edit("section", e.target.value as Section)}>
              {SECTIONS.map((s) => <option key={s} value={s}>{SECTION_TYPE_LABEL[s]}</option>)}
            </select>
          </Field>
          <Field label="Equipment" source={src("equipment")}>
            <select className="input" value={draft.equipment} onChange={(e) => edit("equipment", e.target.value)}>
              {[...new Set([draft.equipment, ...EQUIPMENT_OPTIONS])].map((x) => <option key={x} value={x}>{label(x)}</option>)}
            </select>
          </Field>
          <Field label="Measured in" source={src("measure")}>
            <select className="input" value={draft.measure} onChange={(e) => edit("measure", e.target.value as Measure)}>
              <option value="reps">Reps</option>
              <option value="hold">Seconds held (isometric)</option>
              <option value="time">Time (cardio, stretching, mind)</option>
            </select>
          </Field>
          <Field label="Movement pattern" source={src("pattern")}>
            <select className="input" value={draft.pattern} onChange={(e) => edit("pattern", e.target.value)}>
              {PATTERNS.map((p) => <option key={p} value={p}>{label(p)}</option>)}
            </select>
          </Field>
          <Field label="Difficulty" source={src("difficulty")}>
            <select className="input" value={draft.difficulty ?? ""} onChange={(e) => edit("difficulty", (e.target.value || null) as Difficulty | null)}>
              <option value="">Not set</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="expert">Expert</option>
            </select>
          </Field>
          {draft.measure !== "time" && (
            <Field label={`Target range (${unit})`} source={src("rep_low")}>
              <div className="flex items-center gap-2">
                <input className="input w-24" type="number" min={1} aria-label={`Lowest ${unit}`} value={draft.rep_low ?? ""} onChange={(e) => edit("rep_low", e.target.value ? Number(e.target.value) : null, "rep_low")} />
                <span className="text-faint">to</span>
                <input className="input w-24" type="number" min={1} aria-label={`Highest ${unit}`} value={draft.rep_high ?? ""} onChange={(e) => edit("rep_high", e.target.value ? Number(e.target.value) : null, "rep_low")} />
              </div>
            </Field>
          )}
          {draft.measure === "time" && (
            <Field label="MET (energy, optional)" source={src("met")}>
              <input className="input w-28" type="number" min={1} max={23} step={0.1} value={draft.met ?? ""} onChange={(e) => edit("met", e.target.value ? Number(e.target.value) : null)} />
            </Field>
          )}
        </div>
        <Muscles draft={draft} source={src("muscles")} onChange={(muscles) => edit("muscles", muscles)} />
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Field label="How to do it (one step per line)" source={src("instructions")}>
            <textarea className="input min-h-24" value={draft.instructions.join("\n")} onChange={(e) => edit("instructions", e.target.value.split("\n").map((s) => s.trimStart()).filter((s, i, all) => s || i < all.length - 1).slice(0, 12))} />
          </Field>
          <Field label="Other names (comma-separated)" source={src("aliases")}>
            <input className="input" value={draft.aliases.join(", ")} onChange={(e) => edit("aliases", e.target.value.split(",").map((s) => s.trim()).filter(Boolean).slice(0, 10))} />
          </Field>
        </div>
        {draft.attribution.length > 0 && (
          <p className="mt-3 text-xs text-muted">
            Details from {draft.attribution.map((x) => <a key={x.url} href={x.url} target="_blank" rel="noreferrer" className="text-accent underline-offset-2 hover:underline">{x.title}</a>)} ({draft.attribution[0].license}).
          </p>
        )}
        <div className="mt-5 flex flex-wrap items-center justify-end gap-3">
          <p className="mr-auto text-xs text-faint">Sources: Library = a similar library exercise, Rules = keyword rules, Local AI = the model on this PC, wger = wger.de, You = your edit.</p>
          <button type="button" className="btn btn-primary" onClick={onSave} disabled={busy || Boolean(a.duplicate_of) || draft.name.trim().length < 2}>
            {busy ? "Saving…" : "Add to my library"}
          </button>
        </div>
      </section>
    </>
  );
}

function Field({ label: text, source, children }: { label: string; source: FieldSource | undefined; children: ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-2 text-xs text-muted">
        <span>{text}</span>
        {source && <span className="rounded border border-line-2 px-1.5 py-px text-[10px] uppercase tracking-wide text-faint">{SOURCE_LABEL[source] ?? source}</span>}
      </div>
      {/* The control inside carries its own accessible name via the wrapping label. */}
      <label className="block"><span className="sr-only">{text}</span>{children}</label>
    </div>
  );
}

function Muscles({ draft, source, onChange }: { draft: CustomExerciseIn; source: FieldSource | undefined; onChange: (m: CustomExerciseIn["muscles"]) => void }) {
  const used = new Set(draft.muscles.map((m) => m.muscle));
  const free = Object.keys(MUSCLE_LABEL).filter((k) => !used.has(k));
  const set = (i: number, patch: Partial<{ muscle: string; weight: number }>) => onChange(draft.muscles.map((m, j) => (j === i ? { ...m, ...patch } : m)));
  return (
    <fieldset className="mt-4">
      <legend className="mb-1.5 flex items-center gap-2 text-xs text-muted">
        Muscles worked
        {source && <span className="rounded border border-line-2 px-1.5 py-px text-[10px] uppercase tracking-wide text-faint">{SOURCE_LABEL[source] ?? source}</span>}
      </legend>
      {draft.muscles.length === 0 && <p className="text-xs text-warn">No muscles yet: add at least one so it counts toward muscle load and quests.</p>}
      <ul className="space-y-2">
        {draft.muscles.map((m, i) => (
          <li key={m.muscle} className="flex items-center gap-2">
            <select className="input w-52" aria-label={`Muscle ${i + 1}`} value={m.muscle} onChange={(e) => set(i, { muscle: e.target.value })}>
              {[m.muscle, ...free].map((k) => <option key={k} value={k}>{MUSCLE_LABEL[k as keyof typeof MUSCLE_LABEL] ?? k}</option>)}
            </select>
            <select className="input w-36" aria-label={`Role of muscle ${i + 1}`} value={m.weight >= 1 ? "1" : "0.5"} onChange={(e) => set(i, { weight: Number(e.target.value) })}>
              <option value="1">Primary</option>
              <option value="0.5">Secondary</option>
            </select>
            <button type="button" className="btn-ghost px-2 py-1" aria-label={`Remove ${MUSCLE_LABEL[m.muscle as keyof typeof MUSCLE_LABEL] ?? m.muscle}`} onClick={() => onChange(draft.muscles.filter((_, j) => j !== i))}>
              <IconTrash width={14} />
            </button>
          </li>
        ))}
      </ul>
      {free.length > 0 && draft.muscles.length < 8 && (
        <button type="button" className="btn-ghost mt-2 px-2 py-1 text-xs" onClick={() => onChange([...draft.muscles, { muscle: free[0], weight: 1 }])}>
          <IconPlus width={14} className="mr-1 inline" /> Add muscle
        </button>
      )}
    </fieldset>
  );
}
