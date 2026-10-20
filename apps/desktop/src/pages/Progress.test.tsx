import type { Settings } from "@ascend/shared";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { ProgressPage } from "./Progress";

vi.mock("../api/client", () => ({
  api: {
    bodyMetrics: vi.fn(),
    eta: vi.fn(),
    profile: vi.fn(),
    saveProfile: vi.fn(),
    logWeight: vi.fn(),
    weekly: vi.fn(),
    prs: vi.fn(),
    measurements: vi.fn(),
    logMeasurement: vi.fn(),
    updateSettings: vi.fn(),
  },
}));

const profile = {
  name: "Navin", age: 21, sex: "male" as const, height_cm: 175, weight_kg: 74, goal: "cut" as const, activity: "moderate" as const,
  target_weight_kg: null,
  energy: { bmr: 1700, tdee: 2600, kcal_target: 2100, protein_target_g: 140, formula_version: "tdee-v1", is_estimate: true },
};
const noGoal = {
  goal_kg: null, current_trend_kg: 74, rate_kg_per_week: null, eta_from: null, eta_to: null, confidence: "low" as const,
  on_track: false, reason: "no goal weight set", formula_version: "trend-v1", note: "Estimate, not a promise",
};

function renderPage(settings: Settings = DEFAULT_SETTINGS) {
  return render(
    <PrefsProvider initial={settings} save={vi.fn()}>
      <ToastProvider>
        <ProgressPage refreshKey={0} onChanged={() => {}} />
      </ToastProvider>
    </PrefsProvider>,
  );
}

describe("ProgressPage", () => {
  beforeEach(() => {
    vi.mocked(api.bodyMetrics).mockResolvedValue([
      { id: 1, measured_at: "2026-10-18T07:00:00", weight_kg: 74.4, trend_kg: 74.4, waist_cm: null, resting_hr: null },
      { id: 2, measured_at: "2026-10-19T07:00:00", weight_kg: 73.8, trend_kg: 74.3, waist_cm: null, resting_hr: null },
    ]);
    vi.mocked(api.eta).mockResolvedValue(noGoal);
    vi.mocked(api.profile).mockResolvedValue(profile);
    vi.mocked(api.weekly).mockResolvedValue([]);
    vi.mocked(api.prs).mockResolvedValue([
      { exercise_id: 1, exercise: "Barbell Bench Press", type: "e1rm", value: 80, weight_kg: 70, reps: 5, formula: "epley",
        algo_version: "pr-v1", achieved_at: "2026-10-15T08:00:00", set_id: 3 },
    ]);
    vi.mocked(api.measurements).mockResolvedValue([]);
  });

  it("shows the trend weight, a PR and an empty ETA", async () => {
    renderPage();
    expect(await screen.findByText("74.3 kg")).toBeInTheDocument();
    expect(await screen.findByText("Barbell Bench Press")).toBeInTheDocument();
    expect(screen.getByText("No goal weight set.")).toBeInTheDocument();
  });

  it("sets a goal weight on the profile", async () => {
    vi.mocked(api.saveProfile).mockResolvedValue({ ...profile, target_weight_kg: 70 });
    renderPage();
    await userEvent.type(await screen.findByLabelText(/Set a goal weight/), "70");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.saveProfile).toHaveBeenCalled());
    expect(vi.mocked(api.saveProfile).mock.calls[0][0]).toMatchObject({ name: "Navin", target_weight_kg: 70 });
    expect(vi.mocked(api.saveProfile).mock.calls[0][0]).not.toHaveProperty("energy");
  });

  it("logs a weigh-in typed in pounds as kilograms", async () => {
    vi.mocked(api.logWeight).mockResolvedValue({ id: 3, measured_at: "", weight_kg: 74.843, trend_kg: 74.4, waist_cm: null, resting_hr: null });
    renderPage({ ...DEFAULT_SETTINGS, units: "imperial" });
    await userEvent.type(await screen.findByLabelText("Today's weight (lb)"), "165");
    await userEvent.click(screen.getByRole("button", { name: "Log weigh-in" }));
    await waitFor(() => expect(api.logWeight).toHaveBeenCalledWith(74.843));
  });
});
