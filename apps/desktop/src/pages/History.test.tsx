import type { WorkoutSet } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { HistoryPage, summarise } from "./History";

vi.mock("../api/client", () => ({ api: { history: vi.fn(), updateSettings: vi.fn() } }));

const set = (over: Partial<WorkoutSet>): WorkoutSet => ({
  id: 1, exercise_id: 1, exercise_name: "Bench", weight_kg: 60, reps: 8, rpe: 8, duration_s: null, distance_m: null,
  avg_hr: null, e1rm: 76, is_pr: false, performed_at: "2026-10-20T08:00:00", ...over,
});

describe("summarise", () => {
  it("shows the best lift in the chosen unit", () => {
    const rows = summarise([set({}), set({ id: 2, weight_kg: 70, reps: 5, is_pr: true })], "imperial");
    expect(rows).toEqual([{ name: "Bench", sets: 2, best: "154.3 lb × 5", top: 70, pr: true }]);
  });

  it("shows duration and distance for timed sets instead of reps", () => {
    const run = set({ exercise_name: "Running", weight_kg: 0, reps: 1, duration_s: 1500, distance_m: 4800 });
    expect(summarise([run], "metric")[0].best).toBe("25:00 · 4.8 km");
  });

  it("falls back to reps for bodyweight work", () => {
    expect(summarise([set({ exercise_name: "Push-up", weight_kg: 0, reps: 20 })], "metric")[0].best).toBe("20 reps");
  });
});

describe("HistoryPage", () => {
  it("offers to log something when history is empty", async () => {
    vi.mocked(api.history).mockResolvedValue([]);
    const nav = vi.fn();
    render(
      <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()}>
        <HistoryPage refreshKey={0} onNavigate={nav} />
      </PrefsProvider>,
    );
    await userEvent.click(await screen.findByRole("button", { name: "Log a meal" }));
    expect(nav).toHaveBeenCalledWith("diet");
  });

  it("explains an unreachable engine", async () => {
    vi.mocked(api.history).mockRejectedValue(Object.assign(new Error("Can't reach the local engine."), { status: 0 }));
    render(
      <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()}>
        <HistoryPage refreshKey={0} onNavigate={vi.fn()} />
      </PrefsProvider>,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("The local engine isn't responding");
  });

  it("marks imported sessions with where they came from", async () => {
    vi.mocked(api.history).mockResolvedValue([
      {
        day: "2026-10-18", kcal_in: 0, sets: 1, xp: 0, meals: [],
        workouts: [
          { id: 7, day: "2026-10-18", section: "gym", started_at: "2026-10-18T18:00:00", finished_at: null,
            sets: [set({ exercise_name: "Barbell Bench Press" })], source: "hevy", title: "Upper A" },
        ],
      },
    ]);
    render(
      <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()}>
        <HistoryPage refreshKey={0} onNavigate={vi.fn()} />
      </PrefsProvider>,
    );
    expect(await screen.findByText("Imported from Hevy")).toBeInTheDocument();
    expect(screen.getByText("Upper A")).toBeInTheDocument();
  });
});
