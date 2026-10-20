import type { MuscleState } from "@ascend/shared";
import { describe, expect, it } from "vitest";

import { countByStatus, regionsForSlug, statusBySlug } from "./muscleMap";

function m(key: string, map_slug: string, status: MuscleState["status"]): MuscleState {
  return { key, label: key, group: "", map_slug, status, es_7d: 0, weekly_low: 1, weekly_high: 2, readiness: 1, ready_at: null };
}

const states = [
  m("front_delts", "deltoids", "optimal"),
  m("side_delts", "deltoids", "recovering"),
  m("rear_delts", "deltoids", "under"),
  m("quads", "quadriceps", "over"),
  m("calves", "calves", "no_data"),
];

describe("statusBySlug", () => {
  it("shows the most urgent status when regions share a figure slug", () => {
    expect(statusBySlug(states).get("deltoids")).toBe("recovering");
    expect(statusBySlug(states).get("quadriceps")).toBe("over");
  });
});

describe("helpers", () => {
  it("lists regions for a slug", () => {
    expect(regionsForSlug(states, "deltoids").map((s) => s.key)).toEqual(["front_delts", "side_delts", "rear_delts"]);
  });
  it("counts statuses", () => {
    expect(countByStatus(states)).toEqual({ over: 1, recovering: 1, under: 1, optimal: 1, no_data: 1 });
  });
});
