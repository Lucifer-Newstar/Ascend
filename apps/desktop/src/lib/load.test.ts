import type { Exercise, Workout } from "@ascend/shared";
import { describe, expect, it } from "vitest";

import { effort, sessionLoad } from "./load";

const bench: Exercise = { id: 1, name: "Bench", equipment: "barbell", muscles: [{ muscle: "lower_chest", weight: 1 }, { muscle: "triceps", weight: 0.5 }] };
const set = (rpe: number | null) => ({ id: Math.random(), exercise_id: 1, exercise_name: "Bench", weight_kg: 60, reps: 8, rpe, e1rm: null, is_pr: false, performed_at: "" });

describe("effort", () => {
  it("matches the sidecar bands", () => {
    expect([effort(null), effort(8), effort(6), effort(4)]).toEqual([1, 1, 0.5, 0.25]);
  });
});

describe("sessionLoad", () => {
  it("sums weight x effort per muscle", () => {
    const w: Workout = { id: 1, day: "", started_at: "", finished_at: null, sets: [set(8), set(6)] };
    expect(sessionLoad(w, [bench])).toEqual([["lower_chest", 1.5], ["triceps", 0.75]]);
  });
  it("is empty without a workout", () => {
    expect(sessionLoad(null, [bench])).toEqual([]);
  });
});
