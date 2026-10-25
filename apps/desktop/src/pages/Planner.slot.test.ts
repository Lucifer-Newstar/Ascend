import { describe, expect, it } from "vitest";

import { slotTarget } from "./Planner";

describe("plan draft targets (v1.3)", () => {
  it("shows reps for a lift and seconds for a hold", () => {
    expect(slotTarget({ exercise: "Push-up", sets: 3, rep_low: 9, rep_high: 12 })).toBe("3×9–12");
    expect(slotTarget({ exercise: "Plank", sets: 3, rep_low: 35, rep_high: 50, measure: "hold" })).toBe("3×35–50 s");
    expect(slotTarget({ exercise: "Dead Hang", sets: 2, rep_low: 30, rep_high: 30, measure: "hold" })).toBe("2×30 s");
  });
});
