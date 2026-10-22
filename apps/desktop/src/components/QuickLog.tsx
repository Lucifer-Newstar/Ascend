/**
 * Quick log on Today (v8 hardening): one set, one meal or a weigh-in in a few keystrokes,
 * without opening Train or Fuel. Any of them keeps the streak alive for the day
 * (gamification active_days counts logged sets, meals and weigh-ins since v8).
 * A set goes into today's open workout, or starts one.
 */
import type { Exercise, Food, MealType } from "@ascend/shared";
import { forwardRef, useEffect, useId, useState, type FormEvent } from "react";

import { api } from "../api/client";
import { useOptionalPrefs } from "../lib/prefs";
import { fromDisplayWeight, weightUnit } from "../lib/units";
import { Segmented } from "./Segmented";

type Kind = "set" | "meal" | "weight";

export function mealTypeFor(hour: number): MealType {
  if (hour < 11) return "breakfast";
  if (hour < 15) return "lunch";
  if (hour < 21) return "dinner";
  return "snack";
}

function useSearch<T extends { name: string }>(q: string, search: (q: string) => Promise<T[]>): T[] {
  const [items, setItems] = useState<T[]>([]);
  useEffect(() => {
    if (q.trim().length < 2) {
      setItems([]);
      return;
    }
    let live = true;
    const t = window.setTimeout(() => {
      search(q.trim()).then((r) => live && setItems(r.slice(0, 8))).catch(() => live && setItems([]));
    }, 150);
    return () => {
      live = false;
      window.clearTimeout(t);
    };
  }, [q, search]);
  return items;
}

const searchExercises = (q: string) => api.exercises(q);
const searchFoods = (q: string) => api.foods(q);

export const QuickLogCard = forwardRef<HTMLElement, { onLogged: (what: string) => void }>(function QuickLogCard({ onLogged }, ref) {
  const units = useOptionalPrefs()?.settings.units ?? "metric";
  const [kind, setKind] = useState<Kind>("set");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [count, setCount] = useState("");
  const ids = { list: useId(), name: useId(), amount: useId(), count: useId(), title: useId() };

  const exercises = useSearch<Exercise>(kind === "set" ? name : "", searchExercises);
  const foods = useSearch<Food>(kind === "meal" ? name : "", searchFoods);
  const options = kind === "set" ? exercises : foods;
  const chosenEx = exercises.find((e) => e.name.toLowerCase() === name.trim().toLowerCase());
  const chosenFood = foods.find((f) => f.name.toLowerCase() === name.trim().toLowerCase());
  const measure = chosenEx?.measure ?? "reps";

  function reset(next: Kind) {
    setKind(next);
    setName("");
    setAmount("");
    setCount("");
    setError(null);
    setDone(null);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setDone(null);
    setBusy(true);
    try {
      let what = "";
      if (kind === "weight") {
        const v = Number(amount);
        if (!(v > 0)) throw new Error("Enter your weight.");
        await api.logWeight(fromDisplayWeight(v, units));
        what = `Weigh-in: ${v} ${weightUnit(units)}`;
      } else if (kind === "meal") {
        if (!chosenFood) throw new Error("Pick a food from the list.");
        const portions = Number(count || "1");
        if (!(portions > 0)) throw new Error("Portions must be more than 0.");
        await api.logMeal(mealTypeFor(new Date().getHours()), [{ food_id: chosenFood.id, portions }]);
        what = `Meal: ${chosenFood.name}`;
      } else {
        if (!chosenEx) throw new Error("Pick an exercise from the list.");
        const n = Number(count);
        if (!(n > 0)) throw new Error(measure === "reps" ? "Enter the reps." : "Enter the time.");
        const workout = (await api.activeWorkout()) ?? (await api.startWorkout(chosenEx.section === "calisthenics" ? "calisthenics" : "gym"));
        const weight = amount ? fromDisplayWeight(Number(amount), units) : 0;
        if (measure === "reps") await api.logSet(workout.id, { exercise_id: chosenEx.id, weight_kg: weight, reps: n });
        else await api.logSet(workout.id, { exercise_id: chosenEx.id, weight_kg: weight, duration_s: measure === "hold" ? n : n * 60 });
        what = `Set: ${chosenEx.name}`;
      }
      setDone(`${what}. Logged, and today counts for your streak.`);
      setName("");
      setAmount("");
      setCount("");
      onLogged(what);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not log that.");
    } finally {
      setBusy(false);
    }
  }

  const unit = weightUnit(units);
  return (
    <section ref={ref} id="quick-log" tabIndex={-1} className="card h-full p-5 outline-none" aria-labelledby={ids.title}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id={ids.title} className="card-title">Quick log</h2>
        <Segmented
          label="What to log"
          value={kind}
          onChange={reset}
          options={[{ value: "set", label: "Set" }, { value: "meal", label: "Meal" }, { value: "weight", label: "Weigh-in" }]}
        />
      </div>
      <form className="flex flex-wrap items-end gap-2" onSubmit={submit}>
        {kind !== "weight" && (
          <label className="min-w-[12rem] flex-1 text-xs text-muted" htmlFor={ids.name}>
            {kind === "set" ? "Exercise" : "Food"}
            <input id={ids.name} className="input mt-1 w-full" list={ids.list} value={name} onChange={(e) => setName(e.target.value)}
              placeholder={kind === "set" ? "e.g. Bench Press" : "e.g. Banana"} autoComplete="off" />
            <datalist id={ids.list}>{options.map((o) => <option key={o.id} value={o.name} />)}</datalist>
          </label>
        )}
        {(kind === "weight" || kind === "set") && (
          <label className="w-24 text-xs text-muted" htmlFor={ids.amount}>
            {kind === "weight" ? `Weight (${unit})` : `Load (${unit})`}
            <input id={ids.amount} className="input mt-1 w-full" type="number" inputMode="decimal" min={0} step="0.5" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </label>
        )}
        {kind !== "weight" && (
          <label className="w-24 text-xs text-muted" htmlFor={ids.count}>
            {kind === "meal" ? "Portions" : measure === "reps" ? "Reps" : measure === "hold" ? "Seconds" : "Minutes"}
            <input id={ids.count} className="input mt-1 w-full" type="number" inputMode="decimal" min={0} step={kind === "meal" ? "0.5" : "1"} value={count}
              placeholder={kind === "meal" ? "1" : ""} onChange={(e) => setCount(e.target.value)} />
          </label>
        )}
        <button type="submit" className="btn-primary px-4 py-2 text-sm" disabled={busy}>Log</button>
      </form>
      <p className="mt-2 min-h-[1.25rem] text-xs" role="status">
        {error ? <span className="text-warn">{error}</span> : done ? <span className="text-good">{done}</span> : <span className="text-muted">One set, one meal or a weigh-in. Any of them keeps your streak.</span>}
      </p>
    </section>
  );
});

/** One line on Today when nothing is logged yet today, pointing at Quick log. */
export function NotLoggedBanner({ onOpen }: { onOpen: () => void }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-warn/40 bg-warn/10 px-4 py-2 text-sm text-ink" role="note" data-testid="not-logged-banner">
      <span>You haven't logged anything today.</span>
      <button type="button" className="text-sm font-medium text-accent hover:underline" onClick={onOpen}>Quick log →</button>
    </div>
  );
}
