/**
 * The "Why?" disclosure used by the intelligence layer: the formula in words and every
 * input with the exact value the engine used, so no suggested number is unexplained.
 */
import type { Explanation, Why } from "@ascend/shared";
import { useEffect, useId, useState } from "react";

export const WHY_LABEL: Record<string, string> = {
  // prog-v1
  last_sets: "Last session (reps)",
  last_holds: "Last session (holds)",
  last_load_kg: "Last load (kg)",
  added_load_kg: "Added load (kg)",
  last_rpe: "Last RPE (average)",
  rep_low: "Rep range, bottom",
  rep_high: "Rep range, top",
  range_from: "Range from",
  range_s: "Hold range (s)",
  goal_s: "Hold goal (s)",
  increment_kg: "Smallest step (kg)",
  target_rpe: "Target RPE",
  e1rm_kg: "e1RM, last session (kg)",
  stalled: "Stalled",
  sessions: "Sessions logged",
  // recovery-v2
  fatigue_F: "Fatigue now, F (effective sets)",
  capacity_C: "Capacity, C (effective sets)",
  prior_half_life_h: "Population half-life (h)",
  personal_k: "Your recovery factor, k",
  half_life_h: "Your half-life, h × k (h)",
  checkin_M: "Check-in modifier, M",
  readiness: "Readiness (you)",
  readiness_population: "Readiness (population)",
  // tdee-v1
  tdee_kcal: "Expenditure now, T (kcal/day)",
  sd_kcal: "Uncertainty, 1 SD (kcal)",
  formula_tdee_kcal: "Formula estimate (kcal/day)",
  trend_kg: "Trend weight (kg)",
  weigh_ins: "Weigh-ins used",
  days_of_data: "Days of data",
  intake_days_7: "Days with meals, last 7",
  gate_days: "Days needed to move the target",
  weekly_target_kcal: "This week's target (kcal)",
  target_source: "Target comes from",
  status: "Status",
};

export function WhyButton({ why, label, title, explain }: {
  why: Why;
  label: string;
  title?: string;
  /** Optional plain-language sentence (local model, number-checked; else the template). */
  explain?: () => Promise<Explanation>;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div>
      <button type="button" className="text-xs text-accent hover:underline" aria-expanded={open} aria-controls={id}
        aria-label={label} onClick={() => setOpen((o) => !o)}>
        Why?
      </button>
      {open && <WhyPanel id={id} why={why} title={title} explain={explain} />}
    </div>
  );
}

export function WhyPanel({ why, id, title, explain }: { why: Why; id?: string; title?: string; explain?: () => Promise<Explanation> }) {
  const [plain, setPlain] = useState<Explanation | null>(null);
  useEffect(() => {
    if (!explain) return;
    let alive = true;
    explain().then((e) => alive && setPlain(e)).catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [explain]);
  return (
    <div id={id} className="panel-in mt-2 rounded-md border border-line bg-panel-2 p-3 text-xs" data-testid="why-panel">
      {title && <p className="font-medium text-ink">{title}</p>}
      {plain && (
        <p className="mb-2 text-ink" data-testid="why-plain">
          {plain.text}{" "}
          <span className="text-faint">({plain.phrasing === "model" ? "phrased by the local model, numbers checked" : "template"})</span>
        </p>
      )}
      <p className="text-ink">{why.formula}</p>
      <dl className="mt-2 grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 text-muted">
        {Object.entries(why.inputs).map(([k, v]) => (
          <div key={k} className="contents">
            <dt>{WHY_LABEL[k] ?? k.replace(/_/g, " ")}</dt>
            <dd className="text-right text-ink">{v === null ? "no data" : String(v)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
