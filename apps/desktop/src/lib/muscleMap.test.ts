import type { MuscleState } from "@ascend/shared";
import { describe, expect, it } from "vitest";

import { HEAT, agoLabel, countByStatus, heatColor, isReadyAgain, primaryRegion, regionsForSlug, statusBySlug, summarizeSlugs } from "./muscleMap";

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

describe("summarizeSlugs", () => {
  const activity = [
    { key: "front_delts", sets: 4, volume_kg: 1200, last_trained: "2026-10-18T09:00:00" },
    { key: "side_delts", sets: 2.5, volume_kg: 300, last_trained: "2026-10-19T18:00:00" },
    { key: "rear_delts", sets: 0, volume_kg: 0, last_trained: null },
  ];

  it("sums sets and volume per figure region and keeps the latest training", () => {
    const d = summarizeSlugs(states, activity).get("deltoids");
    expect(d).toMatchObject({ label: "Shoulders", status: "recovering", sets: 6.5, volumeKg: 1500, lastTrained: "2026-10-19T18:00:00" });
    expect(d?.regions).toHaveLength(3);
    expect(d?.fatigued).toBe(true);
    expect(d?.readyAgain).toBe(false);
  });

  it("opens the most urgent region of a figure region", () => {
    const d = summarizeSlugs(states).get("deltoids");
    expect(d && primaryRegion(d).key).toBe("side_delts");
  });

  it("marks recovered, recently trained regions as ready again", () => {
    const fresh = { ...m("biceps", "biceps", "optimal"), es_7d: 8, readiness: 0.97 };
    expect(isReadyAgain(fresh)).toBe(true);
    expect(isReadyAgain({ ...fresh, readiness: 0.6 })).toBe(false);
    expect(isReadyAgain({ ...fresh, es_7d: 0 })).toBe(false);
    expect(isReadyAgain({ ...fresh, status: "over" })).toBe(false);
    expect(summarizeSlugs([fresh]).get("biceps")?.readyAgain).toBe(true);
  });
});

describe("heatColor", () => {
  it("maps a share of the busiest region onto the theme ramp", () => {
    expect(heatColor(0, "dark")).toBeNull();
    expect(heatColor(0.05, "dark")).toBe(HEAT.dark[0]);
    expect(heatColor(1, "dark")).toBe(HEAT.dark[4]);
    expect(heatColor(0.5, "light")).toBe(HEAT.light[2]);
  });
});

describe("agoLabel", () => {
  const now = new Date(2026, 9, 20, 12, 0);
  it("speaks in days", () => {
    expect(agoLabel(new Date(2026, 9, 20, 7, 0).toISOString(), now)).toBe("today");
    expect(agoLabel(new Date(2026, 9, 19, 23, 0).toISOString(), now)).toBe("yesterday");
    expect(agoLabel(new Date(2026, 9, 15, 8, 0).toISOString(), now)).toBe("5 days ago");
    expect(agoLabel(null, now)).toBe("not in the last 4 weeks");
  });
});
