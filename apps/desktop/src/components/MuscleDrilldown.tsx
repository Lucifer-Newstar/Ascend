/**
 * Drill-down for one muscle region: daily effective sets and readiness over 1, 7 or
 * 30 days, the sets that loaded it, and the rule-based suggestion from the sidecar.
 * The recovery block compares your readiness with the population's (recovery-v2) and has a
 * "Why?" with the formula and every input.
 */
import type { Explanation, MuscleRecovery, RecoveryGroup } from "@ascend/shared";
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import { readyAtLabel } from "../lib/format";
import { useReducedMotion } from "../lib/motion";
import { STATUS_LABELS } from "../lib/muscleMap";
import { useApi } from "../lib/useApi";
import { BarChart } from "./charts";
import { Segmented } from "./Segmented";
import { ErrorState, Loading } from "./States";
import { WhyButton } from "./WhyPanel";

type Range = "1" | "7" | "30";

const dayLabel = (iso: string) => new Date(iso + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" });
const timeLabel = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" });

/** How long the closing animation (panel-out in index.css) plays before unmounting. */
export const CLOSE_MS = 160;

export function MuscleDrilldown({ code, onClose: onClosed }: { code: string; onClose: () => void }) {
  const [range, setRange] = useState<Range>("7");
  const h = useApi(() => api.muscleHistory(code, Number(range)), [code, range]);
  const rec = useApi(() => api.recovery(), [code]);
  const mine = rec.data?.muscles.find((m) => m.key === code) ?? null;
  const group = mine ? rec.data?.groups.find((g) => g.group === mine.group) ?? null : null;
  const explainMuscle = useCallback(() => api.recoveryExplanation(code), [code]);
  const panel = useRef<HTMLElement>(null);
  const reduce = useReducedMotion();
  const [closing, setClosing] = useState(false);
  // Opens with a short rise/fade (panel-in) and closes with the reverse before unmounting.
  const onClose = () => {
    if (closing) return;
    if (reduce) return onClosed();
    setClosing(true);
    setTimeout(onClosed, CLOSE_MS);
  };
  const close = useRef(onClose);
  close.current = onClose;

  // Opening moves focus into the panel (once); Esc closes it from anywhere on the page.
  useEffect(() => {
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close.current();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <section ref={panel} tabIndex={-1} className={`origin-top rounded-xl border border-accent/30 bg-panel-2 p-4 outline-none ${closing ? "panel-out" : "panel-in"}`} aria-label="Muscle details" aria-live="polite" data-state={closing ? "closing" : "open"}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-ink">{h.data?.label ?? code}</h3>
        <div className="flex items-center gap-3">
          <Segmented
            label="Days shown"
            value={range}
            onChange={setRange}
            options={[{ value: "1", label: "1 day" }, { value: "7", label: "7 days" }, { value: "30", label: "30 days" }]}
          />
          <button type="button" className="text-xs text-faint hover:text-ink" onClick={onClose} aria-label="Close muscle details">close</button>
        </div>
      </div>
      {h.loading && !h.data ? <Loading /> : h.error ? <ErrorState message={h.error} onRetry={h.reload} /> : h.data && (
        <div className="space-y-4">
          <dl className="grid grid-cols-4 gap-3 text-xs">
            <div><dt className="text-muted">Status</dt><dd className="mt-0.5 text-sm text-ink">{STATUS_LABELS[h.data.status]}</dd></div>
            <div><dt className="text-muted">Last 7 days</dt><dd className="mt-0.5 text-sm text-ink">{Math.round(h.data.es_7d * 10) / 10} sets</dd></div>
            <div><dt className="text-muted">Weekly target</dt><dd className="mt-0.5 text-sm text-ink">{h.data.target_low}–{h.data.target_high} sets</dd></div>
            <div><dt className="text-muted">Readiness</dt><dd className="mt-0.5 text-sm text-ink">{Math.round(h.data.readiness * 100)}%{h.data.ready_at ? ` · ${readyAtLabel(h.data.ready_at)}` : ""}</dd></div>
          </dl>
          {mine && group && <RecoveryYou m={mine} g={group} explain={explainMuscle} />}
          {h.data.suggestion && <p className="rounded-lg border border-line bg-panel px-3 py-2 text-xs text-ink">{h.data.suggestion}</p>}
          {h.data.daily.length > 1 && (
            <div>
              <div className="mb-1 text-[11px] uppercase tracking-wider text-faint">Effective sets per day</div>
              <BarChart
                height={150}
                width={900}
                labels={h.data.daily.map((d) => dayLabel(d.day))}
                values={h.data.daily.map((d) => Math.round(d.eff_sets * 10) / 10)}
                summary={`Effective sets per day for ${h.data.label} over ${h.data.days} days`}
                valueLabel="Effective sets"
              />
            </div>
          )}
          <div>
            <div className="mb-1 text-[11px] uppercase tracking-wider text-faint">Sets that loaded it</div>
            {h.data.contributing_sets.length === 0 ? (
              <p className="text-xs text-faint">No sets for this muscle in the last {h.data.days} day{h.data.days > 1 ? "s" : ""}.</p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-faint"><th className="py-1 font-medium">When</th><th className="font-medium">Exercise</th><th className="font-medium">Share</th><th className="font-medium">Effort</th><th className="text-right font-medium">Eff. sets</th></tr>
                </thead>
                <tbody>
                  {h.data.contributing_sets.slice(0, 12).map((s) => (
                    <tr key={s.set_id} className="border-t border-line/60">
                      <td className="py-1 text-muted">{timeLabel(s.at)}</td>
                      <td className="text-ink">{s.exercise}</td>
                      <td className="text-muted">×{s.weight}</td>
                      <td className="text-muted">{s.effort}</td>
                      <td className="text-right text-ink">{s.es}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <p className="text-[10px] text-faint">Effective sets = muscle share × effort from RPE · {h.data.formula_version} · estimates</p>
        </div>
      )}
    </section>
  );
}

const pct = (x: number) => `${Math.round(x * 100)}%`;

/** "Population vs you": the same doses decayed with the population half-life and with yours. */
export function RecoveryYou({ m, g, explain }: { m: MuscleRecovery; g: RecoveryGroup; explain?: () => Promise<Explanation> }) {
  const slower = g.k > 1;
  // Only call it slower or faster when the 90% interval excludes the population value.
  const clear = g.k_low > 1 || g.k_high < 1;
  return (
    <div className="rounded-lg border border-line bg-panel px-3 py-2 text-xs" data-testid="recovery-you">
      <p className="text-ink">
        Readiness: <span className="font-semibold">you {pct(m.readiness)}</span>
        <span className="text-muted"> · population {pct(m.readiness_population)}</span>
        {m.modifier > 1 && <span className="text-muted"> · today&apos;s check-in ×{m.modifier}</span>}
      </p>
      <p className="mt-1 text-muted">
        {g.personal
          ? clear
            ? `Your ${g.group} muscles recover ${slower ? "slower" : "faster"} than the population: half-life ${m.half_life_h} h instead of ${m.prior_half_life_h} h (factor ${g.k}, 90% interval ${g.k_low}–${g.k_high}, from ${g.n} sessions).`
            : `Your ${g.group} muscles recover about like the population so far: half-life ${m.half_life_h} h against ${m.prior_half_life_h} h (factor ${g.k}, but the 90% interval ${g.k_low}–${g.k_high} still includes 1, from ${g.n} sessions).`
          : `Population recovery for ${g.group} until your sessions show a clear difference (${g.n} usable so far).`}
      </p>
      <div className="mt-1">
        <WhyButton why={m.why} label={`Why is ${m.label} readiness ${pct(m.readiness)}?`} explain={explain} />
      </div>
    </div>
  );
}
