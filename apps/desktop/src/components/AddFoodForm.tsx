/**
 * Add your own food (v1.3): a home recipe or a packet the food table does not have. The
 * sidecar keeps it as a custom food, searchable and loggable at once; the trainer chat
 * does the same with "add food <name> <kcal> kcal".
 */
import type { Food } from "@ascend/shared";
import { useState } from "react";

import { api } from "../api/client";
import { useToast } from "./Toast";

interface Draft {
  name: string;
  portion_label: string;
  portion_g: string;
  kcal: string;
  protein_g: string;
  carbs_g: string;
  fat_g: string;
}

const EMPTY: Draft = { name: "", portion_label: "1 serving", portion_g: "100", kcal: "", protein_g: "", carbs_g: "", fat_g: "" };
const num = (s: string) => (s.trim() === "" ? 0 : Number(s));

export function AddFoodForm({ initialName = "", onAdded, onCancel }: {
  initialName?: string;
  onAdded: (food: Food) => void;
  onCancel: () => void;
}) {
  const [d, setD] = useState<Draft>({ ...EMPTY, name: initialName });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  const set = (k: keyof Draft) => (e: React.ChangeEvent<HTMLInputElement>) => setD({ ...d, [k]: e.target.value });

  const numbers = [d.portion_g, d.kcal, d.protein_g, d.carbs_g, d.fat_g].map(num);
  const invalid = !d.name.trim()
    ? "Give the food a name."
    : !(num(d.kcal) > 0)
      ? "Calories per portion are needed."
      : numbers.some((n) => Number.isNaN(n) || n < 0)
        ? "Numbers can't be negative."
        : null;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (invalid) return setError(invalid);
    setBusy(true);
    setError(null);
    try {
      const food = await api.addFood({
        name: d.name.trim(),
        portion_label: d.portion_label.trim() || "1 serving",
        portion_g: num(d.portion_g) || 100,
        kcal: num(d.kcal),
        protein_g: num(d.protein_g),
        carbs_g: num(d.carbs_g),
        fat_g: num(d.fat_g),
      });
      toast(`${food.name} added to your foods`, "info");
      onAdded(food);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const field = (k: keyof Draft, label: string, props: React.InputHTMLAttributes<HTMLInputElement> = {}) => (
    <label className="block text-xs text-muted">
      {label}
      <input className="input mt-1" value={d[k]} onChange={set(k)} {...props} />
    </label>
  );
  return (
    <form onSubmit={save} className="space-y-3 border-b border-line p-3" aria-label="Add your own food" data-testid="add-food-form">
      <h3 className="text-xs font-medium uppercase tracking-wider text-muted">Add your own food</h3>
      {field("name", "Name", { placeholder: "Amma's sundal", maxLength: 80, autoFocus: true })}
      <div className="grid grid-cols-2 gap-2">
        {field("portion_label", "Portion", { placeholder: "1 katori", maxLength: 40 })}
        {field("portion_g", "Grams per portion", { inputMode: "decimal" })}
      </div>
      <div className="grid grid-cols-4 gap-2">
        {field("kcal", "kcal", { inputMode: "decimal" })}
        {field("protein_g", "Protein g", { inputMode: "decimal" })}
        {field("carbs_g", "Carbs g", { inputMode: "decimal" })}
        {field("fat_g", "Fat g", { inputMode: "decimal" })}
      </div>
      <p className="text-[11px] text-muted">Per portion. A packet's label or a recipe app gives these; rough numbers are fine.</p>
      {error && <p role="alert" className="text-xs text-bad">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className="btn-primary" disabled={busy}>{busy ? "Saving…" : "Save food"}</button>
        <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
