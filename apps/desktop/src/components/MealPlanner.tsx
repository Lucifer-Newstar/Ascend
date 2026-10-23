/**
 * The meal planner (moved from Planner to Fuel in v1.2): a day of Indian meals from the
 * food table, sized to your targets by the sidecar's diet planner (fixed rules; with the
 * AI on, the local model may reword the notes, never the numbers).
 */
import type { DietKind, DietPlan, SavedDiet } from "@ascend/shared";
import { useState, type FormEvent } from "react";

import { api } from "../api/client";
import { Flags } from "../pages/Planner";
import { Panel } from "./Page";
import { useToast } from "./Toast";
import { usePrefs } from "../lib/prefs";
import { useApi } from "../lib/useApi";

export function DietPlanner({ index = 2 }: { index?: number }) {
  const toast = useToast();
  const { settings } = usePrefs();
  const hide = Boolean(settings.hide_calories);
  const [diet, setDiet] = useState<DietKind>("nonveg");
  const [plan, setPlan] = useState<DietPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const saved = useApi(api.savedDiets, []);

  async function build(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      setPlan(await api.planDiet({ diet, use_ai: Boolean(settings.ai_enabled) }));
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function keep() {
    if (!plan) return;
    try {
      await api.saveDiet("My meal plan", plan);
      toast("Meal plan saved", "info");
      saved.reload();
    } catch (err) {
      toast((err as Error).message, "error");
    }
  }

  const day = plan?.days[0];
  return (
    <Panel id="plan-diet" index={index} className="col-span-12" title="Meal planner"
      hint="Indian foods from the food table, sized to your targets. Under 18 it plans at maintenance, never a deficit.">
      <form onSubmit={build} className="flex flex-wrap items-end gap-3" aria-label="Meal planner">
        <label className="text-xs text-muted">Diet
          <select className="input mt-1" value={diet} onChange={(e) => setDiet(e.target.value as DietKind)}>
            <option value="nonveg">Non-veg</option>
            <option value="egg">Eggetarian</option>
            <option value="veg">Vegetarian</option>
          </select>
        </label>
        <button type="submit" className="btn-primary" disabled={busy}>{busy ? "Planning…" : "Plan my meals"}</button>
      </form>
      {plan && day && (
        <div className="mt-4 space-y-3" data-testid="diet-draft">
          <p className="text-sm text-ink">
            {hide ? "Sized to your targets" : `${plan.kcal_target} kcal`} · {plan.protein_target_g} g protein a day
          </p>
          <Flags flags={plan.flags} />
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {day.meals.map((m) => (
              <section key={m.meal} className="rounded-lg border border-line-2 p-3" aria-label={m.meal}>
                <p className="text-[11px] uppercase tracking-wider text-accent">{m.meal}</p>
                <ul className="mt-1 space-y-0.5 text-xs text-ink">
                  {m.items.map((f) => <li key={f.food}>{f.portions} {f.portion_label} {f.food}</li>)}
                </ul>
                <p className="mt-1 text-[11px] text-muted">{hide ? "" : `${m.kcal} kcal · `}{Math.round(m.protein_g)} g protein</p>
              </section>
            ))}
          </div>
          {plan.notes.length > 0 && <ul className="list-disc pl-4 text-xs text-muted">{plan.notes.map((n) => <li key={n}>{n}</li>)}</ul>}
          <button type="button" className="btn-ghost" onClick={() => void keep()}>Save this plan</button>
        </div>
      )}
      {(saved.data ?? []).length > 0 && <SavedDiets list={saved.data as SavedDiet[]} onChanged={saved.reload} />}
    </Panel>
  );
}

function SavedDiets({ list, onChanged }: { list: SavedDiet[]; onChanged: () => void }) {
  return (
    <div className="mt-4 border-t border-line pt-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Saved meal plans</h3>
      <ul className="mt-2 space-y-1 text-sm text-ink">
        {list.map((d) => (
          <li key={d.id} className="flex items-center justify-between">
            <span>{d.name} <span className="text-xs text-muted">· {d.plan.diet} · {new Date(d.created_at).toLocaleDateString()}</span></span>
            <button type="button" className="btn-ghost px-2 py-1 text-xs" aria-label={`Delete ${d.name}`} onClick={() => void api.deleteDiet(d.id).then(onChanged)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
