import type { Exercise, Workout } from "@ascend/shared";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { WorkoutPage } from "./Workout";

vi.mock("../api/client", () => ({
  api: {
    exercises: vi.fn(),
    activeWorkout: vi.fn(),
    startWorkout: vi.fn(),
    logSet: vi.fn(),
    editSet: vi.fn(),
    deleteSet: vi.fn(),
    finishWorkout: vi.fn(),
    updateSettings: vi.fn(),
  },
}));

const bench: Exercise = {
  id: 1, name: "Barbell Bench Press", equipment: "barbell", section: "gym", met: null, time_based: false,
  muscles: [{ muscle: "lower_chest", weight: 1 }],
};
const run: Exercise = {
  id: 50, name: "Running", equipment: "none", section: "cardio", met: 9.8, time_based: true,
  muscles: [{ muscle: "calves", weight: 1 }],
};
const session = (sets: Workout["sets"]): Workout => ({
  id: 9, day: "2026-10-20", section: "cardio", started_at: "2026-10-20T07:00:00", finished_at: null, sets,
  source: "app", title: "",
});

function renderPage() {
  return render(
    <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()}>
      <ToastProvider>
        <WorkoutPage onChanged={() => {}} />
      </ToastProvider>
    </PrefsProvider>,
  );
}

describe("Training page", () => {
  beforeEach(() => {
    vi.mocked(api.exercises).mockImplementation(async (...args) => (args[1] === "cardio" ? [run] : [bench]));
    vi.mocked(api.activeWorkout).mockResolvedValue(null);
  });

  it("switches section tabs and loads that library", async () => {
    renderPage();
    expect(await screen.findByText("Barbell Bench Press")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Cardio" }));
    expect(await screen.findByText("Running")).toBeInTheDocument();
    expect(api.exercises).toHaveBeenLastCalledWith("", "cardio");
    expect(screen.getByRole("tab", { name: "Cardio" })).toHaveAttribute("aria-selected", "true");
  });

  it("logs a timed run into a cardio session", async () => {
    vi.mocked(api.startWorkout).mockResolvedValue(session([]));
    const loggedSet = {
      id: 3, exercise_id: 50, exercise_name: "Running", weight_kg: 0, reps: 1, rpe: 7, duration_s: 1800,
      distance_m: null, avg_hr: null, e1rm: null, is_pr: false, performed_at: "2026-10-20T07:30:00",
    };
    vi.mocked(api.logSet).mockResolvedValue({ set: loggedSet, xp_awarded: 15, previous_best_e1rm: null });
    renderPage();
    await userEvent.click(await screen.findByRole("tab", { name: "Cardio" }));
    await userEvent.click(await screen.findByText("Running"));
    vi.mocked(api.activeWorkout).mockResolvedValue(session([loggedSet]));
    await userEvent.click(screen.getByRole("button", { name: "Log" }));
    await waitFor(() => expect(api.logSet).toHaveBeenCalled());
    expect(api.startWorkout).toHaveBeenCalledWith("cardio");
    expect(vi.mocked(api.logSet).mock.calls[0][1]).toMatchObject({ exercise_id: 50, duration_s: 1800, rpe: 7 });
    expect(await screen.findByText("30:00")).toBeInTheDocument();
    expect(await screen.findByText(/\+15 XP/)).toBeInTheDocument();
  });

  it("deletes a set after confirming", async () => {
    const s = {
      id: 4, exercise_id: 1, exercise_name: "Barbell Bench Press", weight_kg: 60, reps: 8, rpe: 8, duration_s: null,
      distance_m: null, avg_hr: null, e1rm: 76, is_pr: false, performed_at: "2026-10-20T07:10:00",
    };
    vi.mocked(api.activeWorkout).mockResolvedValue({ ...session([s]), section: "gym" });
    vi.mocked(api.deleteSet).mockResolvedValue(null);
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Delete set 1" }));
    vi.mocked(api.activeWorkout).mockResolvedValue({ ...session([]), section: "gym" });
    await userEvent.click(screen.getByRole("button", { name: "Delete set 1?" }));
    await waitFor(() => expect(api.deleteSet).toHaveBeenCalledWith(9, 4));
    expect(await screen.findByText("No sets yet today.")).toBeInTheDocument();
  });

  it("logs a lift by pressing Enter in the reps field", async () => {
    vi.mocked(api.activeWorkout).mockResolvedValue({ ...session([]), section: "gym" });
    const loggedSet = {
      id: 5, exercise_id: 1, exercise_name: "Barbell Bench Press", weight_kg: 60, reps: 8, rpe: 8, duration_s: null,
      distance_m: null, avg_hr: null, e1rm: 76, is_pr: false, performed_at: "2026-10-20T07:12:00",
    };
    vi.mocked(api.logSet).mockResolvedValue({ set: loggedSet, xp_awarded: 10, previous_best_e1rm: null });
    renderPage();
    await userEvent.click(await screen.findByText("Barbell Bench Press"));
    const form = screen.getByRole("form", { name: "Log a set of Barbell Bench Press" });
    const reps = within(form).getByRole("spinbutton", { name: "Reps" });
    expect(form).toContainElement(reps);
    await userEvent.type(reps, "{Enter}");
    await waitFor(() => expect(api.logSet).toHaveBeenCalled());
    expect(vi.mocked(api.logSet).mock.calls.at(-1)?.[1]).toMatchObject({ exercise_id: 1 });
  });
});
