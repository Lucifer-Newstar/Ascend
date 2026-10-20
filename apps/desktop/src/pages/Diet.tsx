import type { Food, MealType } from "@ascend/shared";
import { useMemo, useState } from "react";

import { api } from "../api/client";
import { IconMinus, IconPlus, IconSearch, IconTrash } from "../components/Icons";
import { Empty, ErrorState, Loading } from "../components/States";
import { useToast } from "../components/Toast";
import { grams, kcal, pct, portionLabel, timeLabel } from "../lib/format";
import { useApi } from "../lib/useApi";

const MEAL_TYPES: MealType[] = ["breakfast", "lunch", "dinner", "snack"];

function defaultMealType(): MealType {
  const h = new Date().getHours();
  return h < 11 ? "breakfast" : h < 16 ? "lunch" : h < 19 ? "snack" : "dinner";
}

export function DietPage({ onChanged }: { onChanged: () => void }) {
  const foods = useApi(() => api.foods(), []);
  const day = useApi(api.dayLog, []);
  const [query, setQuery] = useState("");
  const [mealType, setMealType] = useState<MealType>(defaultMealType());
  const [plate, setPlate] = useState<{ food: Food; portions: number }[]>([]);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (foods.data ?? []).filter((f) => !q || f.name.toLowerCase().includes(q));
  }, [foods.data, query]);

  if ((foods.loading && !foods.data) || (day.loading && !day.data)) return <Loading label="Loading food table…" />;
  if (foods.error || day.error) return <ErrorState message={(foods.error ?? day.error) as string} onRetry={() => { foods.reload(); day.reload(); }} />;

  const add = (food: Food) =>
    setPlate((p) => (p.some((x) => x.food.id === food.id) ? p.map((x) => (x.food.id === food.id ? { ...x, portions: x.portions + 1 } : x)) : [...p, { food, portions: 1 }]));
  const change = (id: number, delta: number) =>
    setPlate((p) => p.map((x) => (x.food.id === id ? { ...x, portions: Math.max(0.5, x.portions + delta) } : x)));
  const remove = (id: number) => setPlate((p) => p.filter((x) => x.food.id !== id));
  const plateKcal = plate.reduce((s, x) => s + x.food.kcal * x.portions, 0);
  const plateProtein = plate.reduce((s, x) => s + x.food.protein_g * x.portions, 0);

  async function save() {
    setBusy(true);
    try {
      const res = await api.logMeal(mealType, plate.map((x) => ({ food_id: x.food.id, portions: x.portions })));
      toast(`${mealType[0].toUpperCase() + mealType.slice(1)} logged${res.xp_awarded ? ` · +${res.xp_awarded} XP` : ""}`, "xp");
      setPlate([]);
      day.reload();
      onChanged();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function del(id: number) {
    await api.deleteMeal(id);
    day.reload();
    onChanged();
  }

  const d = day.data!;
  const target = d.kcal_target ?? 2000;
  const proteinTarget = d.protein_target_g ?? 0;
  return (
    <div className="grid grid-cols-12 gap-5">
      <section className="card col-span-12 flex flex-col lg:col-span-4">
        <div className="border-b border-line p-4">
          <h2 className="card-title mb-3">Indian food table</h2>
          <div className="relative">
            <IconSearch className="absolute left-3 top-2.5 text-faint" width={16} height={16} />
            <input className="input pl-9" placeholder="idli, sambar, dal…" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
        </div>
        <ul className="max-h-[calc(100vh-300px)] overflow-y-auto p-2">
          {filtered.map((f) => (
            <li key={f.id}>
              <button type="button" onClick={() => add(f)} className="group flex w-full items-center justify-between rounded-lg px-3 py-2 text-left hover:bg-panel-2">
                <div className="min-w-0">
                  <div className="truncate text-sm text-ink">{f.name}</div>
                  <div className="text-xs text-faint">{f.portion_label} · {f.portion_g} g · P {f.protein_g} g</div>
                </div>
                <span className="flex shrink-0 items-center gap-2 text-xs text-muted">
                  {Math.round(f.kcal)} kcal <IconPlus width={14} height={14} className="text-faint group-hover:text-accent" />
                </span>
              </button>
            </li>
          ))}
          {filtered.length === 0 && <li className="p-4 text-sm text-faint">Not in the starter table yet.</li>}
        </ul>
        <p className="border-t border-line p-3 text-[11px] leading-relaxed text-faint">
          Values are approximate, rounded home-style figures (IFCT 2017 / INDB-style). Recipes and oil vary.
        </p>
      </section>

      <section className="col-span-12 space-y-5 lg:col-span-8">
        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="card-title">Add a meal</h2>
            <div className="flex gap-1 rounded-lg border border-line p-0.5">
              {MEAL_TYPES.map((t) => (
                <button key={t} type="button" onClick={() => setMealType(t)}
                  className={`rounded-md px-3 py-1 text-xs capitalize ${mealType === t ? "bg-accent/15 text-accent" : "text-muted hover:text-ink"}`}>{t}</button>
              ))}
            </div>
          </div>
          {plate.length === 0 ? (
            <Empty title="Click foods on the left to build your plate." hint="Portions use katori / piece / tbsp. Use − and + for half portions." />
          ) : (
            <>
              <ul className="divide-y divide-line/70">
                {plate.map((x) => (
                  <li key={x.food.id} className="flex items-center gap-3 py-2">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-ink">{x.food.name}</div>
                      <div className="text-xs text-faint">{portionLabel(x.portions, x.food.portion_label)}</div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button type="button" className="grid h-7 w-7 place-items-center rounded-md border border-line-2 text-muted hover:text-ink" onClick={() => change(x.food.id, -0.5)} aria-label="less"><IconMinus width={14} height={14} /></button>
                      <span className="w-10 text-center text-sm text-ink">{x.portions}</span>
                      <button type="button" className="grid h-7 w-7 place-items-center rounded-md border border-line-2 text-muted hover:text-ink" onClick={() => change(x.food.id, 0.5)} aria-label="more"><IconPlus width={14} height={14} /></button>
                    </div>
                    <span className="w-20 text-right text-sm text-muted">{Math.round(x.food.kcal * x.portions)} kcal</span>
                    <button type="button" className="text-faint hover:text-bad" onClick={() => remove(x.food.id)} aria-label="remove"><IconTrash width={16} height={16} /></button>
                  </li>
                ))}
              </ul>
              <div className="mt-4 flex items-center justify-between border-t border-line pt-4">
                <span className="text-sm text-muted">≈ <span className="font-semibold text-ink">{kcal(plateKcal)} kcal</span> · {grams(plateProtein)} protein</span>
                <button type="button" className="btn-primary" onClick={save} disabled={busy}>Add {mealType}</button>
              </div>
            </>
          )}
        </div>

        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="card-title">Today</h2>
            <span className="text-xs text-muted">target is an estimate</span>
          </div>
          <div className="mb-5 grid grid-cols-4 gap-4">
            <Bar label="Calories" value={d.totals.kcal} target={target} unit="kcal" color="var(--color-ring-in)" />
            <Bar label="Protein" value={d.totals.protein_g} target={proteinTarget} unit="g" color="var(--color-accent)" />
            <Bar label="Carbs" value={d.totals.carbs_g} unit="g" color="#a78bfa" />
            <Bar label="Fat" value={d.totals.fat_g} unit="g" color="#fbbf24" />
          </div>
          {d.meals.length === 0 ? (
            <Empty title="No meals logged today." />
          ) : (
            <ul className="space-y-2">
              {d.meals.map((m) => (
                <li key={m.id} className="flex items-center gap-4 rounded-lg border border-line bg-panel-2 px-4 py-2.5">
                  <div className="w-20 shrink-0">
                    <div className="text-sm capitalize text-ink">{m.meal_type}</div>
                    <div className="text-xs text-faint">{timeLabel(m.logged_at)}</div>
                  </div>
                  <div className="min-w-0 flex-1 truncate text-sm text-muted">
                    {m.items.map((i) => `${i.food_name}${i.portions !== 1 ? ` ×${i.portions}` : ""}`).join(", ")}
                  </div>
                  <span className="shrink-0 text-sm font-medium text-ink">{kcal(m.kcal)} kcal</span>
                  <button type="button" className="text-faint hover:text-bad" onClick={() => del(m.id)} aria-label="delete meal"><IconTrash width={16} height={16} /></button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}

function Bar({ label, value, target, unit, color }: { label: string; value: number; target?: number; unit: string; color: string }) {
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="text-faint">{target ? `/ ${kcal(target)}` : ""}</span>
      </div>
      <div className="mt-0.5 text-lg font-semibold text-ink">{kcal(value)} <span className="text-xs font-normal text-muted">{unit}</span></div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-line">
        <div className="h-full rounded-full" style={{ width: `${(target ? pct(value, target) : Math.min(1, value / 300)) * 100}%`, background: color }} />
      </div>
    </div>
  );
}
