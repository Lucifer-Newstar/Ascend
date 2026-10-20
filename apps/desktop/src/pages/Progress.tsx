/**
 * Progress: body weight with its trend line and an ETA to the goal weight,
 * weekly training volume, personal records and tape measurements.
 */
import type { BodyMetric, Eta, Measurement, MeasurementSite, PersonalRecord, Profile, Units, WeekSummary } from "@ascend/shared";
import { useState } from "react";

import { api } from "../api/client";
import { BarChart, LineChart } from "../components/charts";
import { IconTrophy } from "../components/Icons";
import { Segmented } from "../components/Segmented";
import { Skeleton } from "../components/Skeleton";
import { Empty, ErrorState } from "../components/States";
import { useToast } from "../components/Toast";
import { usePrefs } from "../lib/prefs";
import { formatLength, formatWeight, fromDisplayWeight, toDisplayWeight, weightUnit } from "../lib/units";
import { isOffline, useApi } from "../lib/useApi";

function ChartSkeleton({ height = "h-48" }: { height?: string }) {
  return (
    <div role="status" aria-busy="true">
      <span className="sr-only">Loading…</span>
      <Skeleton className={`${height} w-full`} />
    </div>
  );
}

const shortDate = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

export function ProgressPage({ refreshKey, onChanged }: { refreshKey: number; onChanged: () => void }) {
  const { settings } = usePrefs();
  const units = settings.units;
  const [tick, setTick] = useState(0);
  const reload = () => {
    setTick((t) => t + 1);
    onChanged();
  };
  const metrics = useApi(() => api.bodyMetrics(90), [refreshKey, tick]);
  const eta = useApi(api.eta, [refreshKey, tick]);
  const profile = useApi(api.profile, [refreshKey, tick]);

  return (
    <div className="grid grid-cols-12 gap-5">
      <section className="card col-span-12 p-5 xl:col-span-8" aria-labelledby="weight-title">
        <div className="mb-3 flex items-center justify-between">
          <h2 id="weight-title" className="card-title">Body weight · 90 days</h2>
          <span className="text-[11px] text-faint">dots = weigh-ins · line = trend (smooths water swings)</span>
        </div>
        {metrics.loading && !metrics.data ? <ChartSkeleton /> : !metrics.data ? <ErrorState message={metrics.error ?? "No data"} onRetry={metrics.reload} offline={isOffline(metrics.status)} /> : (
          <WeightChart metrics={metrics.data ?? []} units={units} />
        )}
        <WeighInForm units={units} lastKg={metrics.data?.at(-1)?.weight_kg} onSaved={reload} />
      </section>

      <section className="card col-span-12 p-5 xl:col-span-4" aria-labelledby="eta-title">
        <h2 id="eta-title" className="card-title mb-3">Goal weight ETA</h2>
        {eta.loading && !eta.data ? <ChartSkeleton height="h-40" /> : !eta.data ? <ErrorState message={eta.error ?? "No data"} onRetry={eta.reload} offline={isOffline(eta.status)} /> : (
          <EtaCard eta={eta.data} units={units} profile={profile.data ?? null} onSaved={reload} />
        )}
      </section>

      <WeeklyCard refreshKey={refreshKey + tick} units={units} />
      <PrCard refreshKey={refreshKey} units={units} />
      <MeasurementsCard refreshKey={refreshKey} units={units} />
    </div>
  );
}

function WeightChart({ metrics, units }: { metrics: BodyMetric[]; units: Units }) {
  if (metrics.length === 0) return <Empty title="No weigh-ins yet." hint="Log your weight below; three or more give a trend." />;
  const labels = metrics.map((m) => shortDate(m.measured_at));
  const latest = metrics[metrics.length - 1];
  const first = metrics[0];
  const change = latest.trend_kg - first.trend_kg;
  return (
    <>
      <div className="mb-2 flex items-baseline gap-4">
        <span className="font-display text-3xl font-bold text-ink">{formatWeight(latest.trend_kg, units)}</span>
        <span className="text-xs text-muted">trend · last weigh-in {formatWeight(latest.weight_kg, units)}</span>
        {metrics.length > 1 && (
          <span className="text-xs text-muted">
            {change > 0 ? "+" : ""}{toDisplayWeight(change, units)} {weightUnit(units)} in {metrics.length} weigh-ins
          </span>
        )}
      </div>
      <LineChart
        labels={labels}
        summary={`Body weight trend from ${formatWeight(first.trend_kg, units)} to ${formatWeight(latest.trend_kg, units)}`}
        series={[
          { label: "Weigh-in", values: metrics.map((m) => toDisplayWeight(m.weight_kg, units)), className: "stroke-faint", dots: true, dashed: true },
          { label: "Trend", values: metrics.map((m) => toDisplayWeight(m.trend_kg, units)), className: "stroke-accent" },
        ]}
      />
    </>
  );
}

function WeighInForm({ units, lastKg, onSaved }: { units: Units; lastKg?: number; onSaved: () => void }) {
  const [weight, setWeight] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const v = Number(weight);
    if (!weight || Number.isNaN(v) || v <= 0) return toast("Enter your weight", "error");
    setBusy(true);
    try {
      await api.logWeight(fromDisplayWeight(v, units));
      setWeight("");
      toast("Weigh-in saved", "info");
      onSaved();
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={save} className="mt-4 flex items-end gap-3 border-t border-line pt-4">
      <label className="block">
        <span className="mb-1.5 block text-xs text-muted">Today's weight ({weightUnit(units)})</span>
        <input className="input w-36" inputMode="decimal" value={weight} onChange={(e) => setWeight(e.target.value)} placeholder={lastKg ? toDisplayWeight(lastKg, units).toFixed(1) : units === "imperial" ? "165.0" : "75.0"} />
      </label>
      <button type="submit" className="btn-primary" disabled={busy}>Log weigh-in</button>
      <span className="pb-2 text-[11px] text-faint">Same time each morning gives the cleanest trend.</span>
    </form>
  );
}

function EtaCard({ eta, units, profile, onSaved }: { eta: Eta; units: Units; profile: Profile | null; onSaved: () => void }) {
  const [goal, setGoal] = useState("");
  const toast = useToast();

  async function saveGoal(e: React.FormEvent) {
    e.preventDefault();
    if (!profile) return;
    const v = Number(goal);
    if (!goal || Number.isNaN(v) || v <= 0) return toast("Enter a goal weight", "error");
    try {
      const { name, age, sex, height_cm, weight_kg, goal: g, activity } = profile;
      await api.saveProfile({ name, age, sex, height_cm, weight_kg, goal: g, activity, target_weight_kg: fromDisplayWeight(v, units) });
      setGoal("");
      toast("Goal weight saved", "info");
      onSaved();
    } catch (err) {
      toast((err as Error).message, "error");
    }
  }

  const goalForm = (
    <form onSubmit={saveGoal} className="mt-4 flex items-end gap-2">
      <label className="block flex-1">
        <span className="mb-1.5 block text-xs text-muted">{eta.goal_kg ? "Change goal" : "Set a goal weight"} ({weightUnit(units)})</span>
        <input className="input" inputMode="decimal" value={goal} onChange={(e) => setGoal(e.target.value)} />
      </label>
      <button type="submit" className="btn-ghost" disabled={!profile}>Save</button>
    </form>
  );

  if (!eta.goal_kg) {
    return (
      <>
        <Empty title="No goal weight set." hint="Set one to see an estimated date range." />
        {goalForm}
      </>
    );
  }

  const rate = eta.rate_kg_per_week;
  return (
    <div>
      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div><dt className="text-xs text-muted">Goal</dt><dd className="font-display text-xl font-bold text-ink">{formatWeight(eta.goal_kg, units)}</dd></div>
        <div><dt className="text-xs text-muted">Trend now</dt><dd className="font-display text-xl font-bold text-ink">{eta.current_trend_kg !== null ? formatWeight(eta.current_trend_kg, units) : "–"}</dd></div>
        <div><dt className="text-xs text-muted">Rate</dt><dd className="text-ink">{rate !== null ? `${rate > 0 ? "+" : ""}${toDisplayWeight(rate, units, 2)} ${weightUnit(units)}/week` : "–"}</dd></div>
        <div><dt className="text-xs text-muted">Confidence</dt><dd className="capitalize text-ink">{eta.confidence}</dd></div>
      </dl>
      <div className="mt-4 rounded-lg border border-line bg-panel-2 p-3">
        {eta.eta_from && eta.eta_to ? (
          <>
            <div className="text-xs text-muted">Estimated arrival</div>
            <div className="mt-0.5 text-lg font-semibold text-accent">{shortDate(eta.eta_from)} – {shortDate(eta.eta_to)}</div>
          </>
        ) : (
          <div className="text-sm text-muted">{eta.reason ?? "Not enough data for an estimate yet."}</div>
        )}
        <div className="mt-1 text-[11px] text-faint">{eta.note}</div>
      </div>
      {goalForm}
    </div>
  );
}

type WeeklyMetric = "volume_kg" | "sessions" | "active_minutes";

function WeeklyCard({ refreshKey, units }: { refreshKey: number; units: Units }) {
  const weeks = useApi(() => api.weekly(8), [refreshKey]);
  const [metric, setMetric] = useState<WeeklyMetric>("volume_kg");
  const unit = metric === "volume_kg" ? ` ${weightUnit(units)}` : metric === "active_minutes" ? " min" : "";
  const value = (w: WeekSummary) => Math.round(metric === "volume_kg" ? toDisplayWeight(w.volume_kg, units, 0) : w[metric]);
  const data: WeekSummary[] = weeks.data ?? [];
  return (
    <section className="card col-span-12 p-5 xl:col-span-8" aria-labelledby="weekly-title">
      <div className="mb-3 flex items-center justify-between gap-4">
        <h2 id="weekly-title" className="card-title">Last 8 weeks</h2>
        <Segmented
          label="Weekly metric"
          value={metric}
          onChange={setMetric}
          options={[{ value: "volume_kg", label: "Volume" }, { value: "sessions", label: "Sessions" }, { value: "active_minutes", label: "Minutes" }]}
        />
      </div>
      {weeks.loading && !weeks.data ? <ChartSkeleton /> : !weeks.data ? <ErrorState message={weeks.error ?? "No data"} onRetry={weeks.reload} offline={isOffline(weeks.status)} /> :
        data.every((w) => w.sessions === 0) ? <Empty title="No training logged in the last 8 weeks." /> : (
          <BarChart
            labels={data.map((w) => shortDate(w.week_start))}
            values={data.map(value)}
            unit={unit}
            summary={`Weekly ${metric.replace("_", " ")} for the last ${data.length} weeks`}
            valueLabel={metric === "volume_kg" ? "Volume" : metric === "sessions" ? "Sessions" : "Minutes"}
          />
        )}
    </section>
  );
}

function PrCard({ refreshKey, units }: { refreshKey: number; units: Units }) {
  const prs = useApi(api.prs, [refreshKey]);
  const list: PersonalRecord[] = (prs.data ?? []).slice(0, 8);
  return (
    <section className="card col-span-12 p-5 xl:col-span-4" aria-labelledby="pr-title">
      <h2 id="pr-title" className="card-title mb-3 flex items-center gap-2"><IconTrophy width={14} height={14} /> Personal records</h2>
      {prs.loading && !prs.data ? <ChartSkeleton height="h-40" /> : !prs.data ? <ErrorState message={prs.error ?? "No data"} onRetry={prs.reload} offline={isOffline(prs.status)} /> : list.length === 0 ? (
        <Empty title="No PRs yet." hint="Log weighted sets of 1–10 reps." />
      ) : (
        <ul className="divide-y divide-line/70">
          {list.map((p) => (
            <li key={p.exercise_id} className="flex items-center justify-between py-2 text-sm">
              <span className="min-w-0">
                <span className="block truncate text-ink">{p.exercise}</span>
                <span className="text-[11px] text-faint">{toDisplayWeight(p.weight_kg, units)} {weightUnit(units)} × {p.reps} · {shortDate(p.achieved_at)}</span>
              </span>
              <span className="font-display text-lg font-bold text-warn" title="Estimated one-rep max (Epley)">{formatWeight(p.value, units)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

const SITES: MeasurementSite[] = ["waist", "hips", "chest", "arm", "thigh", "calf", "neck"];

function MeasurementsCard({ refreshKey, units }: { refreshKey: number; units: Units }) {
  const [tick, setTick] = useState(0);
  const list = useApi(api.measurements, [refreshKey, tick]);
  const [site, setSite] = useState<MeasurementSite>("waist");
  const [value, setValue] = useState("");
  const toast = useToast();
  const latest = new Map<string, Measurement>();
  for (const m of list.data ?? []) {
    const cur = latest.get(m.site);
    if (!cur || cur.measured_at <= m.measured_at) latest.set(m.site, m);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const v = Number(value);
    if (!value || Number.isNaN(v) || v <= 0) return toast("Enter a measurement", "error");
    try {
      await api.logMeasurement(site, units === "imperial" ? Math.round(v * 2.54 * 10) / 10 : v);
      setValue("");
      setTick((t) => t + 1);
      toast(`${site} saved`, "info");
    } catch (err) {
      toast((err as Error).message, "error");
    }
  }

  return (
    <section className="card col-span-12 p-5" aria-labelledby="measure-title">
      <h2 id="measure-title" className="card-title mb-3">Measurements</h2>
      {list.loading && !list.data ? <ChartSkeleton height="h-20" /> : !list.data ? <ErrorState message={list.error ?? "No data"} onRetry={list.reload} offline={isOffline(list.status)} /> : (
        <div className="grid grid-cols-12 gap-5">
          <ul className="col-span-12 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:col-span-8 lg:grid-cols-7">
            {SITES.map((s) => {
              const m = latest.get(s);
              return (
                <li key={s} className="rounded-lg border border-line bg-panel-2 p-3">
                  <div className="text-[11px] uppercase tracking-wider text-muted">{s}</div>
                  <div className="mt-1 text-sm font-semibold text-ink">{m ? formatLength(m.cm, units) : "–"}</div>
                  {m?.change_cm != null && m.change_cm !== 0 && (
                    <div className="text-[11px] text-faint">{m.change_cm > 0 ? "+" : ""}{formatLength(m.change_cm, units)}</div>
                  )}
                </li>
              );
            })}
          </ul>
          <form onSubmit={save} className="col-span-12 flex items-end gap-2 lg:col-span-4">
            <label className="block">
              <span className="mb-1.5 block text-xs text-muted">Site</span>
              <select className="input" value={site} onChange={(e) => setSite(e.target.value as MeasurementSite)}>
                {SITES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
            <label className="block flex-1">
              <span className="mb-1.5 block text-xs text-muted">{units === "imperial" ? "in" : "cm"}</span>
              <input className="input" inputMode="decimal" value={value} onChange={(e) => setValue(e.target.value)} aria-label="Measurement value" />
            </label>
            <button type="submit" className="btn-ghost">Add</button>
          </form>
        </div>
      )}
    </section>
  );
}
