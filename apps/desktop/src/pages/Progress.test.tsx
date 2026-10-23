import type { Settings } from "@ascend/shared";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { ProgressPage } from "./Progress";

vi.mock("../api/client", () => ({
  api: {
    recap: vi.fn(),
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
    muscles: vi.fn(),
    muscleActivity: vi.fn().mockResolvedValue([]),
    progression: vi.fn(),
    dietInsights: vi.fn(),
    insightExplanation: vi.fn(),
    weeklyReview: vi.fn().mockRejectedValue(new Error("no review yet")),
    deload: vi.fn().mockRejectedValue(new Error("no deload advice")),
    startDeload: vi.fn(),
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
    vi.mocked(api.recap).mockResolvedValue({
      week_start: "2026-10-19", week_end: "2026-10-25", complete: false, sessions: 1, active_days: 1, sets: 6,
      active_minutes: 40, volume_kg: 900, xp: 120, prs: [], sections: [{ section: "gym", sets: 6 }], best_day: null,
      boss: null, streak: 2, excused_days: 0, meal_days: 1, checkins: 1, level: 3, rank: "E", rank_title: "Initiate",
      last_week_sessions: 0, last_week_sets: 0, headline: "1 session logged. Every one of them counts.", version: "recap-v1",
    });
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
    vi.mocked(api.muscles).mockResolvedValue([
      { key: "chest", label: "Chest", group: "push", map_slug: "chest", status: "recovering", es_7d: 12, weekly_low: 10, weekly_high: 20, readiness: 0.7, ready_at: null },
      { key: "latissimus_dorsi", label: "Lats", group: "pull", map_slug: "upper-back", status: "under", es_7d: 4, weekly_low: 10, weekly_high: 20, readiness: 1, ready_at: null },
    ]);
    vi.mocked(api.dietInsights).mockResolvedValue({
      algo_version: "insights-v1", week_end: "2026-10-20",
      findings: [{
        code: "protein_short", title: "Protein at 57% of target", text: "Protein averaged 62 g a day against 109 g.",
        severity: 0.43, numbers: { mean_protein_g: 62 },
        why: { formula: "ratio = mean(logged protein, last 7 days) / protein target", inputs: { mean_protein_g: 62.4, protein_target_g: 109 } },
      }],
      checks: [
        { code: "protein_short", outcome: "fired", detail: "Protein at 57% of target" },
        { code: "weekend_gap", outcome: "not_enough_data", detail: "1 weekend and 4 weekday logs (needs 2 and 4)" },
      ],
    });
    vi.mocked(api.insightExplanation).mockResolvedValue({
      text: "Protein averaged 62 g a day against 109 g.", template: "Protein averaged 62 g a day against 109 g.", phrasing: "template",
      model: null, fallback: "ai_disabled", checks: null, facts: "", version: "explain-v1",
    } as never);
    vi.mocked(api.progression).mockResolvedValue({
      exercise_id: 1, exercise: "Barbell Bench Press",
      e1rm: { unit: "kg", current: 80, best: 80, last: 80, trend_pct_week: 1.2, series: [{ at: "2026-10-08T08:00:00", value: 77.5 }, { at: "2026-10-15T08:00:00", value: 80 }] },
    } as never);
  });

  it("shows the trend weight, a PR and an empty ETA", async () => {
    renderPage();
    expect((await screen.findAllByText("74.3 kg")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("Barbell Bench Press")).length).toBeGreaterThan(0);
    expect(screen.getByText("No goal weight set.")).toBeInTheDocument();
  });

  it("leads with a KPI strip and charts a key movement's estimated 1RM", async () => {
    renderPage();
    const strip = screen.getByRole("region", { name: "Headline numbers" });
    expect(strip).toHaveTextContent("Trend weight");
    expect(strip).toHaveTextContent("PRs · 30 days");
    const lifts = await screen.findByRole("region", { name: "Key movements" });
    await waitFor(() => expect(lifts).toHaveTextContent("80 kg"));
    expect(api.progression).toHaveBeenCalledWith(1);
  });

  it("draws weekly sets against each muscle's band", async () => {
    renderPage();
    expect(await screen.findByLabelText("Chest: 12 sets, band 10 to 20, in band")).toBeInTheDocument();
    expect(screen.getByLabelText("Lats: 4 sets, band 10 to 20, under")).toBeInTheDocument();
  });

  it("suggests the last weigh-in as the placeholder for today's weight", async () => {
    renderPage();
    await screen.findAllByText("74.3 kg");
    expect(screen.getByLabelText("Today's weight (kg)")).toHaveAttribute("placeholder", "73.8");
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

  it("shows this week's diet insights with a Why and the rules checked", async () => {
    renderPage();
    const card = await screen.findByRole("region", { name: "This week's diet insights" });
    expect(await within(card).findByText("Protein at 57% of target")).toBeInTheDocument();
    await userEvent.click(within(card).getByRole("button", { name: "Why: Protein at 57% of target" }));
    expect(within(card).getByTestId("why-panel")).toHaveTextContent("ratio = mean(logged protein");
    await userEvent.click(within(card).getByRole("button", { name: "Rules checked" }));
    expect(within(card).getByRole("list", { name: "Rules checked this week" })).toHaveTextContent("not enough data");
  });
});
