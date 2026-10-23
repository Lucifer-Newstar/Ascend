/**
 * Your own skill trees (v1.1): up to 8 steps, each an exercise from the library with a
 * target (sets × reps or a hold, optional added weight). They unlock from logged sets with
 * the same two-session rule as the built-in trees, and pay no XP so XP stays comparable.
 */
import type { Exercise, SkillFamily } from "@ascend/shared";
import { useState, type FormEvent } from "react";

import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import { useToast } from "./Toast";

const FAMILIES: SkillFamily[] = ["pull", "push", "core", "balance", "legs", "levers"];

interface Row {
  exercise: Exercise | null;
  query: string;
  sets: number;
  target: number;
  hold: boolean;
}

const blank = (): Row => ({ exercise: null, query: "", sets: 3, target: 8, hold: false });

export function CustomSkills({ onChanged }: { onChanged: () => void }) {
  const toast = useToast();
  const list = useApi(api.customSkills, []);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [family, setFamily] = useState<SkillFamily>("core");
  const [rows, setRows] = useState<Row[]>([blank()]);
  const [error, setError] = useState<string | null>(null);

  const set = (i: number, patch: Partial<Row>) => setRows((r) => r.map((x, j) => (j === i ? { ...x, ...patch } : x)));

  async function save(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (rows.some((r) => !r.exercise)) {
      setError("Pick an exercise from the list for every step.");
      return;
    }
    try {
      await api.createCustomSkill({
        name: name.trim(), family,
        steps: rows.map((r) => ({ exercise_id: r.exercise!.id, sets: r.sets, reps: r.hold ? null : r.target, hold_s: r.hold ? r.target : null })),
      });
      toast(`${name.trim()} added to your skill trees`, "info");
      setName("");
      setRows([blank()]);
      setOpen(false);
      list.reload();
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function remove(id: number, label: string) {
    if (!window.confirm(`Delete ${label}? Your logged sets stay.`)) return;
    await api.deleteCustomSkill(id).then(() => { list.reload(); onChanged(); }).catch((e: Error) => toast(e.message, "error"));
  }

  return (
    <section className="card p-4" aria-labelledby="custom-skills-title" data-testid="custom-skills">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 id="custom-skills-title" className="text-h3 text-ink">Your own skills</h2>
          <p className="text-xs text-muted">Make a tree from library exercises. It unlocks from your logged sets and pays no XP.</p>
        </div>
        {!open && <button type="button" className="btn-ghost" onClick={() => setOpen(true)}>Make a skill</button>}
      </div>
      {(list.data ?? []).length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {list.data!.map((s) => (
            <li key={s.id} className="flex items-center justify-between text-sm text-ink">
              <span>{s.name} <span className="text-xs text-muted">· {s.steps.length} steps · {s.family}</span></span>
              <button type="button" className="btn-ghost px-2 py-1 text-xs" aria-label={`Delete ${s.name}`} onClick={() => void remove(s.id, s.name)}>Delete</button>
            </li>
          ))}
        </ul>
      )}
      {open && (
        <form onSubmit={save} className="mt-4 space-y-3" aria-label="Make a skill">
          <div className="flex flex-wrap gap-3">
            <label className="text-xs text-muted">Name<input className="input mt-1 w-56" required maxLength={60} value={name} onChange={(e) => setName(e.target.value)} /></label>
            <label className="text-xs text-muted">Family
              <select className="input mt-1" value={family} onChange={(e) => setFamily(e.target.value as SkillFamily)}>
                {FAMILIES.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            </label>
          </div>
          <ol className="space-y-2">
            {rows.map((r, i) => <StepRow key={i} index={i} row={r} onChange={(p) => set(i, p)} onRemove={rows.length > 1 ? () => setRows((x) => x.filter((_, j) => j !== i)) : undefined} />)}
          </ol>
          {error && <p role="alert" className="text-xs text-bad">{error}</p>}
          <div className="flex gap-2">
            <button type="button" className="btn-ghost" disabled={rows.length >= 8} onClick={() => setRows((x) => [...x, blank()])}>Add a step</button>
            <button type="submit" className="btn-primary">Save skill</button>
            <button type="button" className="btn-ghost" onClick={() => setOpen(false)}>Cancel</button>
          </div>
        </form>
      )}
    </section>
  );
}

function StepRow({ index, row, onChange, onRemove }: { index: number; row: Row; onChange: (p: Partial<Row>) => void; onRemove?: () => void }) {
  const found = useApi(() => (row.query.trim().length >= 2 && !row.exercise ? api.exercises(row.query.trim()) : Promise.resolve([] as Exercise[])), [row.query, row.exercise]);
  return (
    <li className="rounded-lg border border-line-2 p-2" aria-label={`Step ${index + 1}`}>
      <div className="flex flex-wrap items-end gap-2">
        <span className="pb-2 text-xs font-semibold text-muted">{index + 1}.</span>
        <label className="text-xs text-muted">Exercise
          <input className="input mt-1 w-56" value={row.exercise ? row.exercise.name : row.query}
            onChange={(e) => onChange({ query: e.target.value, exercise: null })} aria-label={`Step ${index + 1} exercise`} />
        </label>
        <label className="text-xs text-muted">Sets<input type="number" min={1} max={10} className="input mt-1 w-16" value={row.sets} onChange={(e) => onChange({ sets: Number(e.target.value) })} aria-label={`Step ${index + 1} sets`} /></label>
        <label className="text-xs text-muted">{row.hold ? "Seconds" : "Reps"}<input type="number" min={1} max={row.hold ? 600 : 200} className="input mt-1 w-20" value={row.target} onChange={(e) => onChange({ target: Number(e.target.value) })} aria-label={`Step ${index + 1} ${row.hold ? "seconds" : "reps"}`} /></label>
        <label className="flex items-center gap-1 pb-2 text-xs text-muted"><input type="checkbox" checked={row.hold} onChange={(e) => onChange({ hold: e.target.checked })} />Hold</label>
        {onRemove && <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={onRemove} aria-label={`Remove step ${index + 1}`}>Remove</button>}
      </div>
      {(found.data ?? []).length > 0 && (
        <ul className="mt-1 flex flex-wrap gap-1" aria-label="Matching exercises">
          {found.data!.slice(0, 6).map((ex) => (
            <li key={ex.id}><button type="button" className="chip" onClick={() => onChange({ exercise: ex, query: ex.name })}>{ex.name}</button></li>
          ))}
        </ul>
      )}
    </li>
  );
}
