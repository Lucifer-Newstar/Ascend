import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Dashboard, Stats, TdeeReport } from "@ascend/shared";
import { todaysRows } from "./TodaysNumbers";

const ring = (value: number, target: number) => ({ value, target, label: "", is_estimate: true });
const dash = {
  date: "2026-10-22", has_profile: true,
  rings: { tasks: { ...ring(1, 3), is_estimate: false }, kcal_in: ring(1200, 2800), kcal_out: ring(150, 350) },
  nutrition: { kcal: 1200, protein_g: 80, carbs_g: 100, fat_g: 40 },
  game: {
    xp: { total: 5400, today: 120, level: 9, xp_into_level: 300, xp_for_next: 900, rank: "D", rank_title: "Initiate", daily_cap: 800, formula_version: "xp-v2" },
    streak: { current: 4, best: 9, freezes_held: 1, freezes_used: 0, active_today: true },
    calm: { current: 0, best: 0 },
    quest: [{ id: 1, day: "2026-10-22", kind: "training", code: "train_lats", title: "3 hard sets for lats", detail: "", metric: "sets:latissimus_dorsi", target: 3, progress: 1, xp: 60, completed_at: null }],
  },
  muscles: [
    { key: "latissimus_dorsi", label: "Lats", group: "Pull", map_slug: "latissimus_dorsi", status: "under", es_7d: 3, weekly_low: 10, weekly_high: 20, readiness: 1, ready_at: null },
    { key: "infraspinatus", label: "Infraspinatus", group: "Pull", map_slug: "infraspinatus", status: "optimal", es_7d: 1, weekly_low: 0, weekly_high: 0, readiness: 1, ready_at: null, readiness_only: true },
  ],
} as unknown as Dashboard;
const stats = { version: "stats-v1", window_days: 28, stats: [{ key: "str", label: "STR", value: 42, formula: "e1RM vs bodyweight", inputs: { squat_ratio: 1.2 } }] } as Stats;
const tdee = { algo_version: "tdee-v1", status: "learning", tdee_kcal: 2650, low_kcal: 2400, high_kcal: 2900, days_of_data: 9, weigh_ins: 4 } as unknown as TdeeReport;

describe("Today's numbers", () => {
  it("lists every number on Today with its source, and marks thin data as rough", () => {
    const rows = todaysRows(dash, stats, tdee);
    const names = rows.map((r) => r.name);
    expect(names).toEqual(expect.arrayContaining(["Level and rank", "XP today", "Streak", "Quest: 3 hard sets for lats", "Ring: kcal eaten", "Stat STR", "Muscle map", "Energy burned per day"]));
    expect(rows.find((r) => r.key === "level")?.how).toContain("xp-v2");
    expect(rows.find((r) => r.key === "muscles")?.how).toContain("1 small muscles show readiness only");
    const t = rows.find((r) => r.key === "tdee");
    render(<>{t?.data}</>);
    expect(screen.getByTestId("rough-badge")).toHaveTextContent("rough · based on 9 days");
  });
});
