import type { WorkoutPlan } from "@ascend/shared";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { PlannerPage } from "./Planner";

vi.mock("../api/client", () => ({
  api: {
    customPrograms: vi.fn(), planWorkout: vi.fn(), saveProgram: vi.fn(), followProgram: vi.fn(), deleteProgram: vi.fn(),
    goalCheck: vi.fn(), planDiet: vi.fn(), savedDiets: vi.fn(), saveDiet: vi.fn(), deleteDiet: vi.fn(),
  },
}));

const workout: WorkoutPlan = {
  draft: {
    name: "Home strength, 3 days", summary: "Push, pull, legs at home.", level: "beginner", equipment: "bodyweight",
    days: [{ key: "a", name: "Push", weekday: 0, slots: [{ exercise: "Push-up", sets: 3, rep_low: 8, rep_high: 12 }] },
      { key: "b", name: "Pull", weekday: 2, slots: [{ exercise: "Inverted Row", sets: 3, rep_low: 8, rep_high: 12 }] }],
    notes: ["Stop each set with 2 reps in reserve."],
  },
  flags: [{ code: "minutes_tight", severity: "warn", message: "45 minutes is tight for 5 exercises." }],
  phrased_by: "rules", algo_version: "workout-gen-v1",
};


function renderPage(settings = DEFAULT_SETTINGS) {
  return render(
    <PrefsProvider initial={settings} save={async (p) => ({ ...settings, ...p })}>
      <ToastProvider><PlannerPage onChanged={vi.fn()} /></ToastProvider>
    </PrefsProvider>,
  );
}

describe("PlannerPage", () => {
  beforeEach(() => {
    vi.mocked(api.customPrograms).mockResolvedValue([]);
    vi.mocked(api.savedDiets).mockResolvedValue([]);
  });

  it("builds a week, shows the checks and saves and follows it", async () => {
    vi.mocked(api.planWorkout).mockResolvedValue(workout);
    vi.mocked(api.saveProgram).mockResolvedValue({ ...workout.draft, id: 4, key: "custom_4", algo_version: "x", created_at: "", updated_at: "", following: false });
    vi.mocked(api.followProgram).mockResolvedValue({ ...workout.draft, id: 4, key: "custom_4", algo_version: "x", created_at: "", updated_at: "", following: true });
    const { container } = renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Build my week" }));
    const draft = await screen.findByTestId("workout-draft");
    expect(draft).toHaveTextContent("Home strength, 3 days");
    expect(draft).toHaveTextContent("3×8–12 Push-up");
    expect(screen.getByText(/45 minutes is tight/)).toBeInTheDocument();
    expect(api.planWorkout).toHaveBeenCalledWith(expect.objectContaining({ focus: "general", days_per_week: 3, equipment: ["gym"] }));
    await userEvent.click(screen.getByRole("button", { name: "Save and follow" }));
    await waitFor(() => expect(api.followProgram).toHaveBeenCalledWith(4));
    await expectNoAxeViolations(container);
  });

  it("checks a goal", async () => {
    vi.mocked(api.goalCheck).mockResolvedValue({ flags: [{ code: "too_fast", severity: "warn", message: "1.2 kg a week is faster than the 0.5 kg ICMR-NIN calls safe." }], worst: "warn", algo_version: "goalcheck-v2" });
    renderPage();
    await userEvent.type(screen.getByLabelText("Now (kg)"), "80");
    await userEvent.type(screen.getByLabelText("Goal (kg)"), "70");
    await userEvent.type(screen.getByLabelText("In weeks"), "8");
    await userEvent.click(screen.getByRole("button", { name: "Check" }));
    expect(await screen.findByText(/faster than the 0.5 kg/)).toBeInTheDocument();
    expect(api.goalCheck).toHaveBeenCalledWith({ weight_kg: 80, target_weight_kg: 70, weeks: 8 });
  });
});
