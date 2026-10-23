/**
 * Progress (12-column grid, spec §8.4): a KPI strip, then body weight with its trend and the
 * goal-weight ETA, this week's diet insights (insights-v1), estimated 1RM / best hold per key movement, weekly sets per muscle against
 * its band, the 8-week totals, a PR timeline and tape measurements. Every card owns its
 * loading, error and empty state through <Panel>.
 */
import type { BodyMetric, Eta, Measurement, MeasurementSite, MuscleState, PersonalRecord, Profile, Units, WeekSummary } from "@ascend/shared";
import { useState } from "react";

import { api } from "../api/client";
import { BarChart, LineChart } from "../components/charts";
import { InsightsPanel } from "../components/DietCards";
import { IconTrophy } from "../components/Icons";
import { MuscleMap } from "../components/MuscleMap";
import { KpiStrip, KpiTile, Panel, PageGrid } from "../components/Page";
import { DeloadCard, WeeklyReviewCard } from "../components/PlanCards";
import { Segmented } from "../components/Segmented";
import { Empty } from "../components/States";
import { useToast } from "../components/Toast";
import { WeeklyRecapPanel } from "../components/WeeklyRecap";
import { count } from "../lib/format";
import { usePrefs } from "../lib/prefs";
import { formatLength, formatWeight, fromDisplayWeight, toDisplayWeight, weightUnit } from "../lib/units";
import { useApi } from "../lib/useApi";

const shortDate = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
const DAY_MS = 86_400_000;

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
  const weeks = useApi(() => api.weekly(8), [refreshKey, tick]);
  const prs = useApi(api.prs, [refreshKey]);

  const series = metrics.data ?? [];
  const latest = series.at(-1);
  const first = series[0];
  const thisWeek = weeks.data?.at(-1);
  const recentPrs = (prs.data ?? []).filter((p) => Date.now() - new Date(p.achieved_at).getTime() <= 30 * DAY_MS);

  return (
    <PageGrid label="Progress">
      <KpiStrip>
        <KpiTile index={0} label="Trend weight" loading={metrics.loading && !metrics.data}
          value={latest ? formatWeight(latest.trend_kg, units) : "–"}
          sub={latest && first && series.length > 1 ? `${signed(toDisplayWeight(latest.trend_kg - first.trend_kg, units))} ${weightUnit(units)} over ${count(series.length, "weigh-in")}` : "Log a weigh-in to start the trend"} />
        <KpiTile index={1} label="Goal ETA (estimate)" loading={eta.loading && !eta.data} tone={eta.data?.eta_from ? "accent" : "ink"}
          value={eta.data?.eta_from && eta.data.eta_to ? `${shortDate(eta.data.eta_from)} – ${shortDate(eta.data.eta_to)}` : "–"}
          sub={eta.data?.goal_kg ? `to ${formatWeight(eta.data.goal_kg, units)}` : "No goal weight set"} />
        <KpiTile index={2} label="This week" loading={weeks.loading && !weeks.data}
          value={thisWeek ? count(thisWeek.sessions, "session") : "–"}
          sub={thisWeek ? `${count(thisWeek.sets, "set")} · ${thisWeek.active_minutes} min` : undefined} />
        <KpiTile index={3} label="PRs · 30 days" loading={prs.loading && !prs.data} tone={recentPrs.length ? "warn" : "ink"}
          value={prs.data ? String(recentPrs.length) : "–"}
          sub={recentPrs[0] ? `latest: ${recentPrs[0].exercise}` : "Weighted sets of 1–10 reps count"} />
      </KpiStrip>

      <WeeklyRecapPanel refreshKey={refreshKey + tick} index={4} />

      <Panel id="weight" index={4} className="col-span-12 xl:col-span-8" title="Body weight · 90 days"
        action={<span className="text-[11px] text-muted">dots = weigh-ins · line = trend</span>}
        loading={metrics.loading && !metrics.data} error={!metrics.data ? metrics.error ?? null : null} onRetry={metrics.reload} skeletonLines={6}>
        <WeightChart metrics={series} units={units} />
        <WeighInForm units={units} lastKg={latest?.weight_kg} onSaved={reload} />
      </Panel>

      <Panel id="eta" index={5} className="col-span-12 xl:col-span-4" title="Goal weight ETA"
        loading={eta.loading && !eta.data} error={!eta.data ? eta.error ?? null : null} onRetry={eta.reload} skeletonLines={5}>
        {eta.data && <EtaCard eta={eta.data} units={units} profile={profile.data ?? null} onSaved={reload} />}
      </Panel>

      <InsightsPanel refreshKey={refreshKey + tick} index={6} />

      <RecoveryPanel refreshKey={refreshKey + tick} />

      <KeyLiftsPanel prs={prs.data ?? null} loading={prs.loading && !prs.data} error={!prs.data ? prs.error ?? null : null} onRetry={prs.reload} units={units} refreshKey={refreshKey} />
      <MuscleBandPanel refreshKey={refreshKey + tick} />

      <WeeklyPanel weeks={weeks.data ?? null} loading={weeks.loading && !weeks.data} error={!weeks.data ? weeks.error ?? null : null} onRetry={weeks.reload} units={units} />
      <PrTimeline prs={prs.data ?? null} loading={prs.loading && !prs.data} error={!prs.data ? prs.error ?? null : null} onRetry={prs.reload} units={units} />

      <MeasurementsCard refreshKey={refreshKey} units={units} />

      {/* v1.1: moved here from the retired Coach page. */}
      <div className="col-span-12 grid gap-5 xl:grid-cols-2" data-testid="review-cards">
        <WeeklyReviewCard refreshKey={refreshKey} />
        <DeloadCard refreshKey={refreshKey} />
      </div>
    </PageGrid>
  );
}

const signed = (n: number) => `${n > 0 ? "+" : ""}${n}`;

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

/**
 * Estimated 1RM (Epley) or best hold per key movement, from prog-v1's per-exercise series.
 * The key movements are the lifts with the most recent PRs (up to four).
 */
function KeyLiftsPanel({ prs, loading, error, onRetry, units, refreshKey }: {
  prs: PersonalRecord[] | null; loading: boolean; error: string | null; onRetry: () => void; units: Units; refreshKey: number;
}) {
  const lifts = [...(prs ?? [])].sort((a, b) => b.achieved_at.localeCompare(a.achieved_at)).slice(0, 4);
  const [picked, setPicked] = useState<string | null>(null);
  const current = lifts.find((l) => String(l.exercise_id) === picked) ?? lifts[0];
  const target = useApi(() => (current ? api.progression(current.exercise_id) : Promise.resolve(null)), [current?.exercise_id, refreshKey]);
  const e1rm = target.data?.e1rm ?? null;
  const points = e1rm?.series ?? [];
  const isKg = e1rm?.unit === "kg";
  const show = (v: number) => (isKg ? toDisplayWeight(v, units) : v);
  const unit = isKg ? ` ${weightUnit(units)}` : e1rm?.unit === "s" ? " s" : " reps";
  return (
    <Panel id="lifts" index={6} className="col-span-12 xl:col-span-8" title="Key movements"
      hint={isKg ? "Estimated one-rep max (Epley), an estimate" : e1rm?.unit === "s" ? "Best hold per session" : "Best set per session"}
      action={lifts.length > 1 ? (
        <Segmented label="Movement" value={String(current?.exercise_id ?? "")} onChange={setPicked}
          options={lifts.map((l) => ({ value: String(l.exercise_id), label: l.exercise.length > 18 ? `${l.exercise.slice(0, 17)}…` : l.exercise }))} />
      ) : undefined}
      loading={loading} error={error} onRetry={onRetry} skeletonLines={6}
      empty={lifts.length === 0 ? { title: "No key movements yet.", hint: "Log weighted sets of 1–10 reps; each lift with a PR gets a chart here." } : null}>
      {target.loading && !target.data ? (
        <div role="status" aria-busy="true" className="h-48"><span className="sr-only">Loading…</span></div>
      ) : target.error && !target.data ? (
        <Empty title="Couldn't load this movement." hint={target.error} action={{ label: "Retry", onClick: target.reload }} />
      ) : points.length < 2 ? (
        <Empty title={`Only ${count(points.length, "session")} logged for ${current?.exercise ?? "this movement"}.`} hint="Two or more sessions draw a line." />
      ) : (
        <>
          <div className="mb-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <span className="font-display text-3xl font-bold text-ink">{e1rm?.current != null ? `${show(e1rm.current)}${unit}` : "–"}</span>
            {e1rm?.best != null && <span className="text-xs text-muted">best {show(e1rm.best)}{unit}</span>}
            {e1rm?.trend_pct_week != null && <span className="text-xs text-muted">{signed(Math.round(e1rm.trend_pct_week * 10) / 10)}% per week (trend)</span>}
          </div>
          <LineChart
            labels={points.map((p) => shortDate(p.at))}
            unit={unit}
            summary={`${current?.exercise}: ${points.length} sessions from ${show(points[0].value)}${unit} to ${show(points[points.length - 1].value)}${unit}`}
            series={[{ label: current?.exercise ?? "Value", values: points.map((p) => show(p.value)), className: "stroke-accent", dots: true }]}
          />
        </>
      )}
    </Panel>
  );
}

/** Effective sets in the last 7 days per muscle, drawn against its weekly band (recovery-v2). */
function MuscleBandPanel({ refreshKey }: { refreshKey: number }) {
  const muscles = useApi(api.muscles, [refreshKey], { cacheKey: "muscles" });
  // readiness-only muscles (rotator cuff, neck...) have no weekly band to draw against
  const list: MuscleState[] = [...(muscles.data ?? [])].filter((m) => !m.readiness_only).sort((a, b) => b.es_7d - a.es_7d);
  const trained = list.filter((m) => m.es_7d > 0).length;
  return (
    <Panel id="bands" index={7} className="col-span-12 xl:col-span-4" title="Weekly sets vs band"
      hint={muscles.data ? `${trained} of ${list.length} muscles trained in 7 days` : undefined}
      loading={muscles.loading && !muscles.data} error={!muscles.data ? muscles.error ?? null : null} onRetry={muscles.reload} skeletonLines={8}
      empty={muscles.data && trained === 0 ? { title: "No sets in the last 7 days.", hint: "Each muscle's effective sets appear here against its weekly band." } : null}>
      <ul className="space-y-1.5" aria-label="Effective sets per muscle in the last 7 days">
        {list.slice(0, 12).map((m) => <BandRow key={m.key} m={m} />)}
      </ul>
      {list.length > 12 && <p className="mt-2 text-[11px] text-muted">Top 12 by sets. The muscle map on Today shows all {list.length}.</p>}
      <p className="mt-3 flex flex-wrap gap-3 text-[11px] text-muted">
        <span><span className="mr-1 inline-block h-2 w-3 rounded-sm bg-under align-middle" />under</span>
        <span><span className="mr-1 inline-block h-2 w-3 rounded-sm bg-good align-middle" />in band</span>
        <span><span className="mr-1 inline-block h-2 w-3 rounded-sm bg-warn align-middle" />over</span>
      </p>
    </Panel>
  );
}

function BandRow({ m }: { m: MuscleState }) {
  const max = Math.max(m.weekly_high * 1.3, m.es_7d, 1);
  const pos = (v: number) => `${Math.min(100, (v / max) * 100)}%`;
  const state = m.es_7d < m.weekly_low ? "under" : m.es_7d > m.weekly_high ? "over" : "in band";
  const fill = state === "under" ? "bg-under" : state === "over" ? "bg-warn" : "bg-good";
  const sets = Math.round(m.es_7d * 10) / 10;
  return (
    <li className="grid grid-cols-[6.5rem_1fr_2.5rem] items-center gap-2 text-xs" aria-label={`${m.label}: ${sets} sets, band ${m.weekly_low} to ${m.weekly_high}, ${state}`}>
      <span className="truncate text-ink">{m.label}</span>
      <span className="relative h-2 rounded-full bg-line" aria-hidden="true">
        <span className="absolute inset-y-0 rounded-full bg-panel-3 ring-1 ring-line-2" style={{ left: pos(m.weekly_low), width: `calc(${pos(m.weekly_high)} - ${pos(m.weekly_low)})` }} />
        <span className={`absolute inset-y-0 left-0 rounded-full ${fill}`} style={{ width: pos(m.es_7d) }} />
      </span>
      <span className="text-right tabular-nums text-muted">{sets}</span>
    </li>
  );
}

type WeeklyMetric = "volume_kg" | "sessions" | "active_minutes";

function WeeklyPanel({ weeks, loading, error, onRetry, units }: { weeks: WeekSummary[] | null; loading: boolean; error: string | null; onRetry: () => void; units: Units }) {
  const [metric, setMetric] = useState<WeeklyMetric>("volume_kg");
  const unit = metric === "volume_kg" ? ` ${weightUnit(units)}` : metric === "active_minutes" ? " min" : "";
  const value = (w: WeekSummary) => Math.round(metric === "volume_kg" ? toDisplayWeight(w.volume_kg, units, 0) : w[metric]);
  const data: WeekSummary[] = weeks ?? [];
  return (
    <Panel id="weekly" index={8} className="col-span-12 xl:col-span-7" title="Last 8 weeks"
      action={<Segmented label="Weekly metric" value={metric} onChange={setMetric}
        options={[{ value: "volume_kg", label: "Volume" }, { value: "sessions", label: "Sessions" }, { value: "active_minutes", label: "Minutes" }]} />}
      loading={loading} error={error} onRetry={onRetry} skeletonLines={6}
      empty={weeks && data.every((w) => w.sessions === 0) ? { title: "No training logged in the last 8 weeks." } : null}>
      <BarChart
        labels={data.map((w) => shortDate(w.week_start))}
        values={data.map(value)}
        unit={unit}
        summary={`Weekly ${metric.replace("_", " ")} for the last ${data.length} weeks`}
        valueLabel={metric === "volume_kg" ? "Volume" : metric === "sessions" ? "Sessions" : "Minutes"}
      />
    </Panel>
  );
}

function PrTimeline({ prs, loading, error, onRetry, units }: { prs: PersonalRecord[] | null; loading: boolean; error: string | null; onRetry: () => void; units: Units }) {
  const list = [...(prs ?? [])].sort((a, b) => b.achieved_at.localeCompare(a.achieved_at)).slice(0, 8);
  return (
    <Panel id="pr" index={9} className="col-span-12 xl:col-span-5"
      title={<span className="flex items-center gap-2"><IconTrophy width={14} height={14} /> PR timeline</span>}
      loading={loading} error={error} onRetry={onRetry} skeletonLines={6}
      empty={prs && list.length === 0 ? { title: "No PRs yet.", hint: "Log weighted sets of 1–10 reps." } : null}>
      <ol className="relative ml-1.5 border-l border-line-2">
        {list.map((p) => (
          <li key={`${p.exercise_id}-${p.set_id}`} className="relative flex items-center justify-between gap-3 py-2 pl-4 text-sm">
            <span aria-hidden="true" className="absolute -left-[5px] top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full border-2 border-panel bg-warn" />
            <span className="min-w-0">
              <span className="block truncate text-ink">{p.exercise}</span>
              <span className="text-[11px] text-muted">{shortDate(p.achieved_at)} · {toDisplayWeight(p.weight_kg, units)} {weightUnit(units)} × {p.reps}</span>
            </span>
            <span className="font-display text-lg font-bold text-warn" title="Estimated one-rep max (Epley)">{formatWeight(p.value, units)}</span>
          </li>
        ))}
      </ol>
    </Panel>
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
    <Panel id="measure" index={10} title="Measurements" loading={list.loading && !list.data} error={!list.data ? list.error ?? null : null} onRetry={list.reload} skeletonLines={2}>
      {list.data && (
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
    </Panel>
  );
}

/** v1.2: the muscle recovery map moved here from Today. */
function RecoveryPanel({ refreshKey }: { refreshKey: number }) {
  const muscles = useApi(api.muscles, [refreshKey]);
  return (
    <Panel id="recovery" index={7} className="col-span-12" title="Muscle recovery"
      action={<span className="text-[11px] text-muted">Hover for sets and last trained · click for details (estimates)</span>}
      loading={muscles.loading && !muscles.data} error={!muscles.data ? muscles.error ?? null : null} onRetry={muscles.reload} skeletonLines={6}>
      {muscles.data && <MuscleMap muscles={muscles.data} refreshKey={refreshKey} />}
    </Panel>
  );
}
