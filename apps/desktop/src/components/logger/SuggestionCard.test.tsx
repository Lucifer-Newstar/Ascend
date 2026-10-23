import type { ProgressionTarget } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { expectNoAxeViolations } from "../../test/axe";
import { changeLabel, describeTarget, SuggestionCard } from "./SuggestionCard";

const base: ProgressionTarget = {
  exercise_id: 1, exercise: "Barbell Bench Press", kind: "reps", sets: 3, reps: 6, seconds: null, weight_kg: 62.5, rpe: 8,
  change: "up_load", reason: "top_of_range", why: "Every set hit 10 reps: +2.5 kg and back to 6.",
  explanation: { formula: "Double progression in 6-10 reps at RPE 8", inputs: { last_sets: "10, 10, 10", last_load_kg: 60, increment_kg: 2.5 } },
  rep_range: [6, 10], increment_kg: 2.5, e1rm: { unit: "kg", current: 81.2, best: 84, last: 84, trend_pct_week: 1.4, series: [] },
  stalled: false, stall_sessions: 0, skill: null, readiness: null, kept_until: null, deload_week: false, phrasing: "template", algo_version: "prog-v1",
};

describe("SuggestionCard", () => {
  it("shows the target, the change, the reason and the strength trend", async () => {
    const onUse = vi.fn();
    const { container } = render(<SuggestionCard target={base} units="metric" decided={null} onUse={onUse} onKeep={vi.fn()} />);
    expect(screen.getByTestId("suggestion-target")).toHaveTextContent("3 × 6 @ 62.5 kg effort 8");
    expect(screen.getByTestId("suggestion-change")).toHaveTextContent("+2.5 kg");
    expect(screen.getByTestId("suggestion-e1rm")).toHaveTextContent("Strength estimate 81.2 kg · best 84 kg · +1.4% a week");
    await userEvent.click(screen.getByRole("button", { name: "Use it" }));
    expect(onUse).toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Why 3 × 6 @ 62.5 kg?" }));
    expect(screen.getByTestId("why-panel")).toHaveTextContent("Last session (reps)10, 10, 10");
    await expectNoAxeViolations(container);
  });

  it("shows the plain-language sentence and says who wrote it", async () => {
    const explain = vi.fn(async () => ({
      text: "All three sets reached 10 reps, so add 2.5 kg and start again at 6.", template: base.why, phrasing: "model" as const,
      model: "qwen3:4b", fallback: null, checks: { numbers: "pass", banned: "pass" }, facts: "", version: "explain-v1",
    }));
    render(<SuggestionCard target={base} units="metric" decided={null} onUse={vi.fn()} onKeep={vi.fn()} explain={explain} />);
    await userEvent.click(screen.getByRole("button", { name: "Why 3 × 6 @ 62.5 kg?" }));
    expect(await screen.findByTestId("why-plain")).toHaveTextContent("add 2.5 kg and start again at 6. (phrased by the local model, numbers checked)");
    expect(explain).toHaveBeenCalledTimes(1);
  });

  it("labels holds, resets, deloads and the first time", () => {
    const hold: ProgressionTarget = { ...base, kind: "hold", reps: null, seconds: 24, weight_kg: 0, change: "up_time", reason: "add_time" };
    expect(describeTarget(hold, "metric")).toBe("3 × 24 s");
    expect(changeLabel(hold, "metric")).toBe("More time");
    expect(changeLabel({ ...base, change: "reset", reason: "stall_reset" }, "metric")).toBe("Reset −10%");
    expect(changeLabel({ ...base, change: "hold", reason: "deload_week" }, "metric")).toBe("Deload");
    expect(changeLabel({ ...base, weight_kg: 65 }, "imperial")).toBe("+11 lb");
    render(<SuggestionCard target={{ ...base, change: "first", reason: "first", why: "First time: log a set that feels like RPE 8." }} units="metric" decided={null} onUse={vi.fn()} onKeep={vi.fn()} />);
    expect(screen.queryByTestId("suggestion-target")).toBeNull();
    expect(screen.queryByRole("button", { name: "Use it" })).toBeNull();
  });

  it("names the skill step a calisthenics target feeds", () => {
    const skill = { skill_name: "Muscle-up", step_name: "Negative pull-up", criterion: "3×10", sessions_met: 0, confirm_sessions: 2 };
    render(<SuggestionCard target={{ ...base, weight_kg: 0, reps: 8, skill }} units="metric" decided={null} onUse={vi.fn()} onKeep={vi.fn()} />);
    expect(screen.getByText(/needs 3×10/)).toHaveTextContent("Feeds Muscle-up: Negative pull-up needs 3×10 (0/2 sessions met)");
  });
});
