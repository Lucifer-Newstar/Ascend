/**
 * Diet intelligence cards (ADR-0018, ADR-0019): the adaptive TDEE card for Fuel and the
 * weekly insights card for Progress. Every number comes from the engines and carries a
 * "Why?" with its formula and inputs; the plain-language line is the local model's only
 * when the coach guard passed it, else the template.
 */
import type { DietInsights, InsightCheck, InsightFinding, TdeeReport } from "@ascend/shared";
import { useCallback, useState } from "react";

import { api } from "../api/client";
import { LineChart } from "./charts";
import { Panel } from "./Page";
import { RoughBadge } from "./RoughBadge";
import { WhyButton } from "./WhyPanel";
import { kcal } from "../lib/format";
import { useApi } from "../lib/useApi";

const STATUS_LABEL: Record<TdeeReport["status"], string> = {
  cold_start: "Formula estimate",
  learning: "Learning",
  adaptive: "Adaptive",
};

const shortDate = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

/** Fuel's energy card: expenditure as a range, this week's target and how complete the data is. */
export function TdeePanel({ refreshKey = 0, index = 5, className = "col-span-12 xl:col-span-4" }: { refreshKey?: number; index?: number; className?: string }) {
  const r = useApi(() => api.tdee(56), [refreshKey]);
  const d = r.data;
  const series = d?.series ?? [];
  return (
    <Panel id="tdee" index={index} className={className} title="Energy & expenditure"
      hint={d ? STATUS_LABEL[d.status] : undefined}
      action={d && <span className={`chip ${d.status === "adaptive" ? "border-good/50 text-good" : ""}`}>{STATUS_LABEL[d.status]}</span>}
      loading={r.loading && !d} error={!d ? (r.status === 404 ? null : r.error ?? null) : null} onRetry={r.reload} skeletonLines={6}
      empty={!d && r.status === 404 ? { title: "No profile yet.", hint: "Finish onboarding to get an estimate." } : null}>
      {d && (
        <>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="flex flex-wrap items-center gap-1.5 text-xs text-muted">You burn about {d.status !== "adaptive" && <RoughBadge n={d.days_of_data} unit="days" enough={14} />}</dt>
              <dd className="font-display text-2xl font-bold text-ink">{kcal(d.tdee_kcal)} <span className="text-xs font-normal text-muted">kcal/day</span></dd>
              <dd className="text-xs text-muted">likely {kcal(d.low_kcal)}–{kcal(d.high_kcal)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">This week's target</dt>
              <dd className="font-display text-2xl font-bold text-ink">{kcal(d.target_kcal)} <span className="text-xs font-normal text-muted">kcal</span></dd>
              <dd className="text-xs text-muted">{d.target_source === "adaptive" ? "adaptive, set on Monday" : "formula (Mifflin-St Jeor)"}</dd>
            </div>
          </dl>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <Completeness label="Days with meals" value={d.intake_days_7} of={7} need={d.gate_days} />
            <Completeness label="Weigh-ins" value={d.weigh_ins_7} of={7} />
          </div>
          <p className={`mt-3 rounded-md border px-3 py-2 text-xs ${d.paused ? "border-warn/50 bg-warn/10 text-ink" : "border-line bg-panel-2 text-muted"}`} role="status">{d.reason}</p>
          {series.length >= 7 && (
            <div className="mt-3">
              <LineChart
                height={150}
                unit=""
                table={false}
                labels={series.map((p) => shortDate(p.day))}
                summary={`Expenditure estimate over ${series.length} days, from ${kcal(series[0].tdee_kcal)} to ${kcal(d.tdee_kcal)} kcal`}
                series={[
                  { label: "Estimate", values: series.map((p) => Math.round(p.tdee_kcal)), className: "stroke-accent" },
                  { label: "+1 SD", values: series.map((p) => Math.round(p.tdee_kcal + p.sd_kcal)), className: "stroke-faint", dashed: true },
                  { label: "−1 SD", values: series.map((p) => Math.round(p.tdee_kcal - p.sd_kcal)), className: "stroke-faint", dashed: true },
                ]}
              />
            </div>
          )}
          <div className="mt-3 flex flex-wrap gap-4 border-t border-line pt-3">
            <WhyButton label="Why this expenditure?" title="tdee-v1 (Kalman filter)" why={d.why} explain={api.tdeeExplanation} />
          </div>
        </>
      )}
    </Panel>
  );
}

function Completeness({ label, value, of, need }: { label: string; value: number; of: number; need?: number }) {
  const short = need !== undefined && value < need;
  return (
    <div className="rounded-md border border-line bg-panel-2 px-3 py-2">
      <div className="text-muted">{label} · last {of}</div>
      <div className={`mt-0.5 font-semibold ${short ? "text-warn" : "text-ink"}`}>{value}/{of}{need !== undefined && <span className="font-normal text-muted"> (needs {need})</span>}</div>
    </div>
  );
}

function FindingCard({ f }: { f: InsightFinding }) {
  // Stable per finding, so the Why panel asks for the plain-language line once.
  const explain = useCallback(() => api.insightExplanation(f.code), [f.code]);
  return (
    <li className="panel-in rounded-lg border border-line bg-panel-2 p-4">
      <div className="text-[11px] uppercase tracking-wider text-muted">{CHECK_LABEL[f.code] ?? f.code}</div>
      <div className="mt-1 text-sm font-semibold text-ink">{f.title}</div>
      <p className="mt-1 text-xs leading-relaxed text-muted">{f.text}</p>
      <div className="mt-2">
        <WhyButton label={`Why: ${f.title}`} why={f.why} explain={explain} />
      </div>
    </li>
  );
}

const CHECK_LABEL: Record<string, string> = {
  intake_vs_target: "Intake vs target",
  protein_short: "Protein",
  weekend_gap: "Weekend vs weekday",
  trend_vs_goal: "Trend vs goal",
  tdee_vs_formula: "Adaptive vs formula",
  logging_gap: "Logging",
};

const OUTCOME_LABEL: Record<InsightCheck["outcome"], string> = { fired: "finding", quiet: "fine", not_enough_data: "not enough data" };

/** Progress's weekly insights: up to three findings, each with a Why, and every rule checked. */
export function InsightsPanel({ refreshKey = 0, index = 6, className = "col-span-12" }: { refreshKey?: number; index?: number; className?: string }) {
  const r = useApi(api.dietInsights, [refreshKey]);
  const d: DietInsights | null = r.data ?? null;
  const [showChecks, setShowChecks] = useState(false);
  return (
    <Panel id="insights" index={index} className={className} title="This week's diet insights"
      hint={d ? `7 days to ${shortDate(d.week_end)} · fixed rules, every number computed` : undefined}
      action={d && (
        <button type="button" className="text-xs text-accent hover:underline" aria-expanded={showChecks} onClick={() => setShowChecks((s) => !s)}>
          {showChecks ? "Hide rules" : "Rules checked"}
        </button>
      )}
      loading={r.loading && !d} error={!d ? (r.status === 404 ? null : r.error ?? null) : null} onRetry={r.reload} skeletonLines={4}
      empty={!d && r.status === 404 ? { title: "No profile yet.", hint: "Insights need your goal and targets." } : null}>
      {d && (
        <>
          {d.findings.length === 0 ? (
            <p className="rounded-md border border-dashed border-line-2 p-4 text-center text-sm text-muted">Nothing stands out this week. Every rule was checked; open “Rules checked” to see each one.</p>
          ) : (
            <ul className="grid gap-3 md:grid-cols-3">
              {d.findings.map((f) => <FindingCard key={f.code} f={f} />)}
            </ul>
          )}
          {showChecks && (
            <ul className="panel-in mt-4 divide-y divide-line/70 text-xs" aria-label="Rules checked this week">
              {d.checks.map((c) => (
                <li key={c.code} className="flex items-center justify-between gap-3 py-1.5">
                  <span className="text-ink">{CHECK_LABEL[c.code] ?? c.code}</span>
                  <span className="text-right text-muted"><span className={c.outcome === "fired" ? "text-warn" : c.outcome === "quiet" ? "text-good" : ""}>{OUTCOME_LABEL[c.outcome]}</span> · {c.detail}</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Panel>
  );
}
