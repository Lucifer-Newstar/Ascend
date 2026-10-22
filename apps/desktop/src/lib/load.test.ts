import type { Exercise, Workout } from "@ascend/shared";
import { describe, expect, it } from "vitest";

import { effort, sessionLoad } from "./load";

const bench: Exercise = { id: 1, name: "Bench", equipment: "barbell", section: "gym", met: null, time_based: false, muscles: [{ muscle: "pec_major_sternal", weight: 1 }, { muscle: "triceps_lateral", weight: 0.5 }] };
const set = (rpe: number | null) => ({ id: Math.random(), exercise_id: 1, exercise_name: "Bench", weight_kg: 60, reps: 8, rpe, duration_s: null, distance_m: null, avg_hr: null, e1rm: null, is_pr: false, performed_at: "" });

describe("effort", () => {
  it("matches the sidecar bands", () => {
    expect([effort(null), effort(8), effort(6), effort(4)]).toEqual([1, 1, 0.5, 0.25]);
  });
});

describe("sessionLoad", () => {
  it("sums weight x effort per muscle", () => {
    const w: Workout = { id: 1, day: "", section: "gym", started_at: "", finished_at: null, sets: [set(8), set(6)], source: "app", title: "" };
    expect(sessionLoad(w, [bench])).toEqual([["pec_major_sternal", 1.5], ["triceps_lateral", 0.75]]);
  });
  it("is empty without a workout", () => {
    expect(sessionLoad(null, [bench])).toEqual([]);
  });
});
