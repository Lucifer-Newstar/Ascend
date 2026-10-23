/**
 * History (12-column grid): a KPI strip for the range, the day-by-day log (8 columns) and a
 * side rail with an activity calendar (click a day to jump to it) and where sessions came
 * from. A filter narrows the log to training days or meal days.
 */
import type { HistoryDay, Units, WorkoutSet, WorkoutSource } from "@ascend/shared";
import { useState, type CSSProperties } from "react";

import { api } from "../api/client";
import { IconTrophy } from "../components/Icons";
import type { Page } from "../components/Layout";
import { KpiStrip, KpiTile, PageGrid, Panel } from "../components/Page";
import { Segmented } from "../components/Segmented";
import { LoadingLayout, SkeletonCard } from "../components/Skeleton";
import { Empty, ErrorState, StaleNotice } from "../components/States";
import { count, dateLabel, dayLabel, kcal, timeLabel } from "../lib/format";
import { usePrefs } from "../lib/prefs";
import { formatDistance, formatDuration, toDisplayWeight, weightUnit } from "../lib/units";
import { isOffline, useApi } from "../lib/useApi";

const SOURCE_LABEL: Record<WorkoutSource, string> = { app: "ASCEND", strong: "Strong", hevy: "Hevy" };
const stagger = (i: number): CSSProperties => ({ ["--i" as string]: Math.min(i + 4, 10) }) as CSSProperties;

type Range = "30" | "90";
type Filter = "all" | "training" | "meals";

export function HistoryPage({ refreshKey, onNavigate }: { refreshKey: number; onNavigate: (p: Page) => void }) {
  const [range, setRange] = useState<Range>("30");
  const [filter, setFilter] = useState<Filter>("all");
  const { data, error, status, loading, reload } = useApi(() => api.history(Number(range)), [refreshKey, range]);
  const { settings } = usePrefs();
  if (loading && !data) {
    return (
      <LoadingLayout label="Loading history…">
        <div className="grid grid-cols-12 gap-5">
          {[0, 1, 2, 3].map((i) => <SkeletonCard key={`k${i}`} className="col-span-6 md:col-span-3" lines={1} />)}
          <div className="col-span-12 space-y-4 xl:col-span-8">{[0, 1, 2].map((i) => <SkeletonCard key={i} lines={3} />)}</div>
          <SkeletonCard className="col-span-12 xl:col-span-4" lines={6} />
        </div>
      </LoadingLayout>
    );
  }
  if (!data) return <ErrorState message={error ?? "No data"} onRetry={reload} offline={isOffline(status)} />;
  if (data.length === 0) {
    return (
      <PageGrid label="History">
        <div className="card rise-in col-span-12 p-8 text-center xl:col-span-8">
          <h2 className="text-base font-semibold text-ink">Nothing logged in the last {range} days</h2>
          <p className="mt-1 text-sm text-muted">Workouts and meals appear here, grouped by day.</p>
          <div className="mt-5 flex justify-center gap-3">
            <button type="button" className="btn-primary" onClick={() => onNavigate("workout")}>Log a workout</button>
            <button type="button" className="btn-ghost" onClick={() => onNavigate("diet")}>Log a meal</button>
          </div>
        </div>
      </PageGrid>
    );
  }

  const shown = data.filter((d) => filter === "all" || (filter === "training" ? d.workouts.length > 0 : d.meals.length > 0));
  const trainingDays = data.filter((d) => d.workouts.length > 0).length;
  const mealDays = data.filter((d) => d.meals.length > 0);
  const totalSets = data.reduce((s, d) => s + d.sets, 0);
  const totalXp = data.reduce((s, d) => s + d.xp, 0);
  const avgKcal = mealDays.length ? mealDays.reduce((s, d) => s + d.kcal_in, 0) / mealDays.length : 0;

  return (
    <PageGrid label="History">
      {error && <div className="col-span-12"><StaleNotice message={error} onRetry={reload} /></div>}
      <KpiStrip label={`Last ${range} days`}>
        <KpiTile index={0} label="Training days" value={String(trainingDays)} sub={`out of ${count(data.length, "day")} with a log`} />
        <KpiTile index={1} label="Sets" value={count(totalSets, "set")} sub={trainingDays ? `≈ ${Math.round(totalSets / trainingDays)} per training day` : undefined} />
        <KpiTile index={2} label="Avg logged intake" value={mealDays.length ? `${kcal(avgKcal)} kcal` : "–"} sub={mealDays.length ? `over ${count(mealDays.length, "logged day")}` : "No meals logged"} />
        <KpiTile index={3} label="XP earned" tone="xp" value={`+${totalXp.toLocaleString("en-IN")}`} />
      </KpiStrip>

      <div className="col-span-12 space-y-4 xl:col-span-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Segmented label="Show" value={filter} onChange={setFilter}
            options={[{ value: "all", label: "Everything" }, { value: "training", label: "Training days" }, { value: "meals", label: "Meal days" }]} />
          <Segmented label="Range" value={range} onChange={setRange} options={[{ value: "30", label: "30 days" }, { value: "90", label: "90 days" }]} />
        </div>
        {shown.length === 0 && <Empty title={filter === "training" ? "No training days in this range." : "No meal days in this range."} action={{ label: "Show everything", onClick: () => setFilter("all") }} />}
        {shown.map((d, i) => (
        <section key={d.day} id={`day-${d.day}`} className="card card-hover rise-in p-5" style={stagger(i)} aria-label={dayLabel(d.day)}>
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-sm font-semibold text-ink">
              {dayLabel(d.day)}
              {dayLabel(d.day) !== dateLabel(d.day) && <span className="ml-2 text-xs font-normal text-muted">{dateLabel(d.day)}</span>}
            </h2>
            <span className="text-xs text-muted">{count(d.sets, "set")} · {kcal(d.kcal_in)} kcal eaten · <span className="text-xp">+{d.xp} XP</span></span>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="mb-1.5 text-[11px] uppercase tracking-wider text-faint">Workouts</div>
              {d.workouts.length === 0 ? <p className="text-xs text-muted">Rest day</p> : d.workouts.map((w) => (
                <div key={w.id} className="mb-2 last:mb-0">
                  {w.source !== "app" && (
                    <div className="mb-1 flex items-center gap-2 text-xs text-muted">
                      <span className="chip">Imported from {SOURCE_LABEL[w.source]}</span>
                      {w.title && <span className="truncate">{w.title}</span>}
                    </div>
                  )}
                  <ul className="space-y-1 text-sm">
                    {summarise(w.sets, settings.units).map((row) => (
                      <li key={row.name} className="flex justify-between gap-2">
                        <span className="text-ink">{row.name}{row.pr && <IconTrophy className="ml-1.5 inline text-warn" width={13} height={13} aria-label="personal record" />}</span>
                        <span className="text-muted">{row.sets} × {row.best}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <div>
              <div className="mb-1.5 text-[11px] uppercase tracking-wider text-faint">Meals</div>
              {d.meals.length === 0 ? <p className="text-xs text-muted">No meals logged</p> : (
                <ul className="space-y-1 text-sm">
                  {d.meals.map((m) => (
                    <li key={m.id} className="flex justify-between gap-2">
                      <span className="truncate text-ink" title={m.items.map((i) => i.food_name).join(", ")}><span className="capitalize text-muted">{m.meal_type}</span> · {m.items.map((i) => i.food_name).join(", ")}</span>
                      <span className="shrink-0 text-muted">{timeLabel(m.logged_at)} · {kcal(m.kcal)} kcal</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>
      ))}
      </div>

      <div className="col-span-12 space-y-5 xl:col-span-4">
        <ActivityCalendar days={data} range={Number(range)} />
        {/* v1.2: only for players who imported sessions from another app. */}
        {data.some((d) => d.workouts.some((w) => w.source !== "app")) && <SourcesPanel days={data} />}
      </div>
    </PageGrid>
  );
}

/** One square per day, shaded by sets logged; days with a log jump to that day's card. */
function ActivityCalendar({ days, range }: { days: HistoryDay[]; range: number }) {
  const byDay = new Map(days.map((d) => [d.day, d]));
  const today = new Date();
  const cells = Array.from({ length: range }, (_, i) => {
    const dt = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (range - 1 - i));
    const iso = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
    return { iso, d: byDay.get(iso) };
  });
  const maxSets = Math.max(1, ...days.map((d) => d.sets));
  const shade = (sets: number) => (sets === 0 ? 0 : sets <= maxSets / 3 ? 1 : sets <= (2 * maxSets) / 3 ? 2 : 3);
  const SHADES = ["bg-panel-3", "bg-accent/35", "bg-accent/65", "bg-accent"];
  return (
    <Panel id="calendar" index={5} title="Activity" hint="Shade = sets logged that day; a dot = meals logged">
      <ul className="grid grid-cols-10 gap-1.5" aria-label={`Activity over the last ${range} days`}>
        {cells.map(({ iso, d }) => {
          const label = `${dateLabel(iso)}: ${d ? `${count(d.sets, "set")}, ${count(d.meals.length, "meal")}` : "nothing logged"}`;
          const dot = d && d.meals.length > 0 ? <span className="absolute bottom-0.5 right-0.5 h-1 w-1 rounded-full bg-good" aria-hidden="true" /> : null;
          return (
            <li key={iso} className="aspect-square">
              {d ? (
                <a href={`#day-${iso}`} title={label} aria-label={label}
                  className={`relative block h-full w-full rounded-sm ${SHADES[shade(d.sets)]} ring-accent hover:ring-2`}
                  onClick={(e) => { e.preventDefault(); document.getElementById(`day-${iso}`)?.scrollIntoView?.({ block: "start" }); }}>{dot}</a>
              ) : (
                <span title={label} className={`block h-full w-full rounded-sm ${SHADES[0]}`}><span className="sr-only">{label}</span></span>
              )}
            </li>
          );
        })}
      </ul>
      <div className="mt-3 flex items-center gap-1.5 text-[11px] text-muted" aria-hidden="true">
        less {SHADES.map((s) => <span key={s} className={`h-2.5 w-2.5 rounded-sm ${s}`} />)} more
      </div>
    </Panel>
  );
}

function SourcesPanel({ days }: { days: HistoryDay[] }) {
  const counts = new Map<WorkoutSource, number>();
  for (const d of days) for (const w of d.workouts) counts.set(w.source, (counts.get(w.source) ?? 0) + 1);
  const total = [...counts.values()].reduce((a, b) => a + b, 0);
  return (
    <Panel id="sources" index={6} title="Sessions by source"
      empty={total === 0 ? { title: "No sessions in this range." } : null}>
      <ul className="space-y-2 text-sm">
        {[...counts.entries()].map(([src, n]) => (
          <li key={src}>
            <div className="flex justify-between"><span className="text-ink">{SOURCE_LABEL[src]}</span><span className="text-muted">{count(n, "session")}</span></div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-line"><div className="h-full rounded-full bg-accent" style={{ width: `${(n / total) * 100}%` }} /></div>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

/** One line per exercise: set count and the best set, in the user's units. */
export function summarise(sets: WorkoutSet[], units: Units) {
  const map = new Map<string, { name: string; sets: number; best: string; top: number; pr: boolean }>();
  for (const s of sets) {
    const row = map.get(s.exercise_name) ?? { name: s.exercise_name, sets: 0, best: "", top: -1, pr: false };
    row.sets += 1;
    row.pr ||= s.is_pr;
    // Timed sets rank by duration, lifts by weight, bodyweight by reps.
    const score = s.duration_s ? s.duration_s : s.weight_kg > 0 ? s.weight_kg : s.reps;
    if (score > row.top) {
      row.top = score;
      row.best = s.measure === "hold" && s.duration_s
        ? `${s.duration_s} s hold${s.weight_kg > 0 ? ` +${toDisplayWeight(s.weight_kg, units)} ${weightUnit(units)}` : ""}`
        : s.duration_s
        ? `${formatDuration(s.duration_s)}${s.distance_m ? ` · ${formatDistance(s.distance_m, units)}` : ""}`
        : s.weight_kg > 0
          ? `${toDisplayWeight(s.weight_kg, units)} ${weightUnit(units)} × ${s.reps}`
          : count(s.reps, "rep");
    }
    map.set(s.exercise_name, row);
  }
  return [...map.values()];
}
