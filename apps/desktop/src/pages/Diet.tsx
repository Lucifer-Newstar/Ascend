/**
 * Fuel (12-column grid, spec §8.4): a KPI strip, then today's intake and meal list (8 columns)
 * beside the adaptive TDEE card (4 columns, tdee-v1), then the meal builder: the Indian food table and the
 * plate side by side, then the meal planner (moved here from Planner in v1.2). Every card owns its loading, error and empty state through <Panel>.
 */
import type { Food, MealType } from "@ascend/shared";
import { useMemo, useState } from "react";

import { api } from "../api/client";
import { IconMinus, IconPlus, IconSearch, IconTrash } from "../components/Icons";
import { TdeePanel } from "../components/DietCards";
import { FoodGuidePanel } from "../components/FoodGuide";
import { DietPlanner } from "../components/MealPlanner";
import { KpiStrip, KpiTile, PageGrid, Panel } from "../components/Page";
import { Empty } from "../components/States";
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
  const [tick, setTick] = useState(0);
  const [query, setQuery] = useState("");
  const [mealType, setMealType] = useState<MealType>(defaultMealType());
  const [plate, setPlate] = useState<{ food: Food; portions: number }[]>([]);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (foods.data ?? []).filter((f) => !q || f.name.toLowerCase().includes(q));
  }, [foods.data, query]);

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
      setTick((t) => t + 1);
      onChanged();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function del(id: number, mealName: string) {
    try {
      await api.deleteMeal(id);
      toast(`${mealName[0].toUpperCase() + mealName.slice(1)} deleted`, "info");
      day.reload();
      setTick((t) => t + 1);
      onChanged();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  const d = day.data;
  const dayLoading = day.loading && !d;
  const dayError = !d ? day.error ?? null : null;
  const target = d?.kcal_target ?? 2000;
  const proteinTarget = d?.protein_target_g ?? 0;
  const left = d ? Math.round(target - d.totals.kcal) : 0;
  return (
    <PageGrid label="Fuel">
      <KpiStrip>
        <KpiTile index={0} label="Calories today" loading={dayLoading} value={d ? `${kcal(d.totals.kcal)} kcal` : "–"} sub={d ? `of ${kcal(target)} kcal ${d.kcal_target_source === "adaptive" ? "adaptive target" : "target (estimate)"}` : undefined} />
        <KpiTile index={1} label="Protein" loading={dayLoading} tone={d && proteinTarget && d.totals.protein_g >= proteinTarget ? "good" : "ink"}
          value={d ? grams(d.totals.protein_g) : "–"} sub={d && proteinTarget ? `of ${grams(proteinTarget)} target` : undefined} />
        <KpiTile index={2} label={left >= 0 ? "Left today" : "Over today"} loading={dayLoading} tone={left < 0 ? "warn" : "ink"}
          value={d ? `${kcal(Math.abs(left))} kcal` : "–"} sub={d ? `${pct(d.totals.kcal, target) >= 1 ? "target reached" : `${Math.round(pct(d.totals.kcal, target) * 100)}% of target`}` : undefined} />
        <KpiTile index={3} label="Meals logged" loading={dayLoading} value={d ? String(d.meals.length) : "–"}
          sub={d?.meals.at(-1) ? `last: ${d.meals.at(-1)!.meal_type} at ${timeLabel(d.meals.at(-1)!.logged_at)}` : "Nothing logged yet today"} />
      </KpiStrip>

      <Panel id="today" index={4} className="col-span-12 xl:col-span-8" title="Today"
        action={<span className="text-xs text-muted">targets are estimates</span>}
        loading={dayLoading} error={dayError} onRetry={day.reload} skeletonLines={5}>
        {d && (
          <>
            <div className="mb-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Bar label="Calories" value={d.totals.kcal} target={target} unit="kcal" color="var(--color-ring-in)" />
              <Bar label="Protein" value={d.totals.protein_g} target={proteinTarget} unit="g" color="var(--color-accent)" />
              <Bar label="Carbs" value={d.totals.carbs_g} unit="g" color="var(--color-xp)" />
              <Bar label="Fat" value={d.totals.fat_g} unit="g" color="var(--color-warn)" />
            </div>
            {d.meals.length === 0 ? (
              <Empty title="No meals logged today." hint="Build a plate below, or type “lunch chicken rice” in Ctrl+K." />
            ) : (
              <ul className="space-y-2" aria-label="Meals logged today">
                {d.meals.map((m) => (
                  <li key={m.id} className="flex items-center gap-4 rounded-lg border border-line bg-panel-2 px-4 py-2.5">
                    <div className="w-20 shrink-0">
                      <div className="text-sm capitalize text-ink">{m.meal_type}</div>
                      <div className="text-xs text-muted">{timeLabel(m.logged_at)}</div>
                    </div>
                    <div className="min-w-0 flex-1 truncate text-sm text-muted" title={m.items.map((i) => i.food_name).join(", ")}>
                      {m.items.map((i) => `${i.food_name}${i.portions !== 1 ? ` ×${i.portions}` : ""}`).join(", ")}
                    </div>
                    <span className="shrink-0 text-sm font-medium text-ink">{kcal(m.kcal)} kcal</span>
                    <button type="button" className="text-faint hover:text-bad" onClick={() => del(m.id, m.meal_type)} aria-label={`Delete ${m.meal_type} at ${timeLabel(m.logged_at)}`}><IconTrash width={16} height={16} /></button>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </Panel>

      <TdeePanel refreshKey={tick} />

      <FoodGuidePanel refreshKey={tick} index={5} />

      <Panel id="builder" index={6} className="col-span-12" title="Add a meal" hover={false}
        action={
          <div className="flex gap-1 rounded-lg border border-line p-0.5" role="group" aria-label="Meal type">
            {MEAL_TYPES.map((t) => (
              <button key={t} type="button" aria-pressed={mealType === t} onClick={() => setMealType(t)}
                className={`rounded-md px-3 py-1 text-xs capitalize ${mealType === t ? "bg-accent/15 text-accent" : "text-muted hover:text-ink"}`}>{t}</button>
            ))}
          </div>
        }
        loading={foods.loading && !foods.data} error={!foods.data ? foods.error ?? null : null} onRetry={foods.reload} skeletonLines={6}>
        <div className="grid grid-cols-12 gap-5">
          <div className="col-span-12 flex flex-col rounded-lg border border-line lg:col-span-5">
            <div className="border-b border-line p-3">
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted">Indian food table</h3>
              <div className="relative">
                <IconSearch className="absolute left-3 top-2.5 text-faint" width={16} height={16} />
                <input className="input pl-9" aria-label="Search foods" placeholder="idli, sambar, dal…" value={query} onChange={(e) => setQuery(e.target.value)} />
              </div>
            </div>
            <ul className="max-h-80 overflow-y-auto p-2">
              {filtered.length === 0 && (
                <li className="p-4 text-sm text-muted">
                  No food matches “{query}”.{" "}
                  <button type="button" className="text-accent hover:underline" onClick={() => setQuery("")}>Clear search</button>
                  <p className="mt-1 text-xs text-muted">The table has about 30 common dishes; more arrive with the full INDB import.</p>
                </li>
              )}
              {filtered.map((f) => (
                <li key={f.id}>
                  <button type="button" onClick={() => add(f)} className="group flex w-full items-center justify-between rounded-lg px-3 py-2 text-left hover:bg-panel-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm text-ink">{f.name}</div>
                      <div className="text-xs text-muted">{f.portion_label} · {f.portion_g} g · P {f.protein_g} g</div>
                    </div>
                    <span className="flex shrink-0 items-center gap-2 text-xs text-muted">
                      {Math.round(f.kcal)} kcal <IconPlus width={14} height={14} className="text-faint group-hover:text-accent" />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <p className="border-t border-line p-3 text-[11px] leading-relaxed text-muted">
              Values are approximate, rounded home-style figures (IFCT 2017 / INDB-style). Recipes and oil vary.
            </p>
          </div>

          <div className="col-span-12 lg:col-span-7">
            {plate.length === 0 ? (
              <Empty title="Click foods on the left to build your plate." hint="Portions use katori / piece / tbsp. Use − and + for half portions." />
            ) : (
              <>
                <ul className="divide-y divide-line/70" aria-label="Your plate">
                  {plate.map((x) => (
                    <li key={x.food.id} className="panel-in flex items-center gap-3 py-2">
                      <div className="min-w-0 flex-1">
                        <div className="text-sm text-ink">{x.food.name}</div>
                        <div className="text-xs text-muted">{portionLabel(x.portions, x.food.portion_label)}</div>
                      </div>
                      <div className="flex items-center gap-1">
                        <button type="button" className="grid h-7 w-7 place-items-center rounded-md border border-line-2 text-muted hover:text-ink" onClick={() => change(x.food.id, -0.5)} aria-label={`Less ${x.food.name}`}><IconMinus width={14} height={14} /></button>
                        <span className="w-10 text-center text-sm text-ink">{x.portions}</span>
                        <button type="button" className="grid h-7 w-7 place-items-center rounded-md border border-line-2 text-muted hover:text-ink" onClick={() => change(x.food.id, 0.5)} aria-label={`More ${x.food.name}`}><IconPlus width={14} height={14} /></button>
                      </div>
                      <span className="w-20 text-right text-sm text-muted">{Math.round(x.food.kcal * x.portions)} kcal</span>
                      <button type="button" className="text-faint hover:text-bad" onClick={() => remove(x.food.id)} aria-label={`Remove ${x.food.name}`}><IconTrash width={16} height={16} /></button>
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
        </div>
      </Panel>
      <DietPlanner index={7} />
    </PageGrid>
  );
}

function Bar({ label, value, target, unit, color }: { label: string; value: number; target?: number; unit: string; color: string }) {
  return (
    <div>
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-0.5 text-lg font-semibold text-ink">{kcal(value)} <span className="text-xs font-normal text-muted">{unit}</span></div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-line">
        <div className="h-full rounded-full" style={{ width: `${(target ? pct(value, target) : Math.min(1, value / 300)) * 100}%`, background: color }} />
      </div>
      {target ? <div className="mt-1 truncate text-[11px] text-faint">of {kcal(target)} {unit}</div> : null}
    </div>
  );
}
