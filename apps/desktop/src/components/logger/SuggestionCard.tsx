/**
 * The logger's suggestion card (prog-v1): the next target, what changed and a one-line
 * reason, with "Use it", "Keep mine" and a "Why?" that lists the formula and every input.
 * Every number on it comes from the progression engine; the text never invents one.
 */
import type { ProgressionTarget } from "@ascend/shared";

import type { Units } from "../../lib/units";
import { toDisplayWeight, weightUnit } from "../../lib/units";
import { WhyButton } from "../WhyPanel";

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/0+$/, "").replace(/\.$/, ""));

export function describeTarget(t: ProgressionTarget, units: Units): string {
  const load = t.weight_kg > 0 ? ` @ ${fmt(toDisplayWeight(t.weight_kg, units))} ${weightUnit(units)}` : "";
  const amount = t.kind === "hold" ? `${t.seconds ?? 0} s` : String(t.reps ?? 0);
  return `${t.sets} × ${amount}${t.kind === "hold" && t.weight_kg > 0 ? load.replace(" @ ", " + ") : load}`;
}

export function changeLabel(t: ProgressionTarget, units: Units): string {
  const last = t.explanation.inputs.last_load_kg ?? t.explanation.inputs.added_load_kg;
  const lastLoad = typeof last === "number" ? last : null;
  switch (t.reason) {
    case "deload_week":
      return "Deload";
    case "kept":
      return "Your numbers";
    case "hold_recovering":
      return "Hold · recovering";
    case "stall_reset":
      return "Reset −10%";
    case "criterion_confirm":
      return "Confirm step";
  }
  switch (t.change) {
    case "up_load":
      return lastLoad !== null ? `+${fmt(toDisplayWeight(t.weight_kg - lastLoad, units))} ${weightUnit(units)}` : "Heavier";
    case "up_reps":
      return "+1 rep";
    case "up_time":
      return "More time";
    case "down":
      return "Lighter";
    case "advance":
      return "Next step";
    case "first":
      return "Baseline";
    default:
      return "Hold";
  }
}

export function SuggestionCard({ target, units, decided, busy, onUse, onKeep }: {
  target: ProgressionTarget;
  units: Units;
  decided: "accepted" | "kept" | null;
  busy?: boolean;
  onUse: () => void;
  onKeep: () => void;
}) {
  const t = target;
  if (t.kind === "none") return null;
  const first = t.change === "first";
  const kept = t.reason === "kept" || decided === "kept";
  const e = t.e1rm;
  const unit = e?.unit === "kg" ? weightUnit(units) : e?.unit === "s" ? "s" : "reps";
  const show = (v: number) => (e?.unit === "kg" ? fmt(toDisplayWeight(v, units)) : fmt(v));
  return (
    <section className="mt-4 rounded-md border border-line bg-panel-2 p-3" aria-label="Suggested next target" data-testid="suggestion-card">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[11px] uppercase tracking-wide text-muted">Suggested next</p>
        <span className="chip text-[11px]" data-testid="suggestion-change">{changeLabel(t, units)}</span>
      </div>
      {!first && (
        <p className="mt-1 text-lg font-semibold text-ink" data-testid="suggestion-target">
          {describeTarget(t, units)}
          {t.rpe !== null && <>{" "}<span className="ml-1 text-sm font-normal text-muted">RPE {fmt(t.rpe)}</span></>}
        </p>
      )}
      <p className="mt-1 text-sm text-muted">{t.why}</p>
      {t.skill && (
        <p className="mt-1 text-xs text-muted">
          Feeds <span className="text-ink">{t.skill.skill_name}</span>: {t.skill.step_name} needs {t.skill.criterion}
          {" "}({t.skill.sessions_met}/{t.skill.confirm_sessions} sessions met)
        </p>
      )}
      {e && e.current !== null && (
        <p className="mt-1 text-xs text-muted" data-testid="suggestion-e1rm">
          {e.unit === "kg" ? "e1RM" : e.unit === "s" ? "Best hold" : "Best set"} {show(e.current)} {unit} · best {show(e.best ?? e.current)} {unit}
          {e.trend_pct_week !== null && ` · ${e.trend_pct_week >= 0 ? "+" : ""}${e.trend_pct_week}% a week`}
          {t.stalled && <span className="ml-1 text-warn">· stalled {t.stall_sessions} sessions</span>}
        </p>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {!first && !kept && (
          <>
            <button type="button" className="btn-primary h-8 px-3 text-xs" disabled={busy || decided === "accepted"} onClick={onUse}>
              {decided === "accepted" ? "Using it" : "Use it"}
            </button>
            <button type="button" className="btn-ghost h-8 px-3 text-xs" disabled={busy} onClick={onKeep}>Keep mine</button>
          </>
        )}
        {kept && t.kept_until && (
          <p className="text-xs text-muted">Keeping your numbers until {new Date(t.kept_until).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}.</p>
        )}
        <WhyButton why={t.explanation} label={`Why ${first ? "no target yet" : describeTarget(t, units)}?`} />
      </div>
    </section>
  );
}
