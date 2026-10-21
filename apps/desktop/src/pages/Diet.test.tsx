import type { DayLog, Food } from "@ascend/shared";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { DietPage } from "./Diet";

vi.mock("../api/client", () => ({
  api: { foods: vi.fn(), dayLog: vi.fn(), logMeal: vi.fn(), deleteMeal: vi.fn(), updateSettings: vi.fn(), tdee: vi.fn(), tdeeExplanation: vi.fn() },
}));

const idli: Food = { id: 1, name: "Idli", portion_label: "1 piece", portion_g: 40, kcal: 58, protein_g: 2, carbs_g: 12, fat_g: 0.2, source: "approx" };
const day: DayLog = {
  day: "2026-10-20",
  meals: [{
    id: 5, day: "2026-10-20", meal_type: "breakfast", logged_at: "2026-10-20T08:15:00", kcal: 174,
    items: [{ id: 9, food_id: 1, food_name: "Idli", portions: 3, kcal: 174, protein_g: 6, carbs_g: 36, fat_g: 0.6 }],
  }],
  totals: { kcal: 174, protein_g: 6, carbs_g: 36, fat_g: 0.6 },
  kcal_target: 2500, protein_target_g: 110, values_are_approximate: true,
};

function renderPage() {
  return render(
    <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()}>
      <ToastProvider>
        <DietPage onChanged={() => {}} />
      </ToastProvider>
    </PrefsProvider>,
  );
}

describe("Diet page", () => {
  beforeEach(() => {
    vi.mocked(api.foods).mockResolvedValue([idli]);
    vi.mocked(api.dayLog).mockResolvedValue(day);
    vi.mocked(api.tdee).mockResolvedValue({
      algo_version: "tdee-v1", status: "adaptive", tdee_kcal: 2480, sd_kcal: 120, low_kcal: 2360, high_kcal: 2600,
      formula_tdee_kcal: 2635, formula_target_kcal: 2135, target_kcal: 1980, target_source: "adaptive", target_week_start: "2026-10-19",
      trend_kg: 73.9, days_of_data: 60, weigh_ins: 48, intake_days_7: 5, weigh_ins_7: 6, gate_days: 6, paused: true,
      reason: "intake logged on 5 of the last 7 days (needs 6); the target holds", series: [], weeks: [],
      why: { formula: "Kalman filter on [trend weight W, expenditure T]", inputs: { tdee_kcal: 2480, sd_kcal: 120 } },
    });
    vi.mocked(api.tdeeExplanation).mockResolvedValue({
      text: "You burn about 2480 kcal a day.", template: "You burn about 2480 kcal a day.", phrasing: "template",
      model: null, fallback: "ai_disabled", checks: null, facts: "", version: "explain-v1",
    } as never);
  });

  it("leads with a KPI strip and shows the adaptive expenditure as a range with its Why", async () => {
    renderPage();
    const strip = await screen.findByRole("region", { name: "Headline numbers" });
    expect(strip).toHaveTextContent("Calories today");
    expect(strip).toHaveTextContent("2,326 kcal");
    const card = await screen.findByRole("region", { name: "Energy & expenditure" });
    expect(card).toHaveTextContent("2,480");
    expect(card).toHaveTextContent("likely 2,360–2,600");
    expect(card).toHaveTextContent("5/7");
    expect(within(card).getByRole("status")).toHaveTextContent("the target holds");
    await userEvent.click(within(card).getByRole("button", { name: "Why this expenditure?" }));
    expect(screen.getByTestId("why-panel")).toHaveTextContent("Kalman filter");
    expect(await screen.findByTestId("why-plain")).toHaveTextContent("You burn about 2480 kcal a day.");
  });

  it("names the food on each plate control and shows targets with units", async () => {
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Idli/ }));
    expect(screen.getByRole("button", { name: "More Idli" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Less Idli" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remove Idli" })).toBeInTheDocument();
    expect(screen.getByText("of 2,500 kcal")).toBeInTheDocument();
    expect(screen.getByText("of 110 g")).toBeInTheDocument();
    const types = ["breakfast", "lunch", "dinner", "snack"].map((t) => screen.getByRole("button", { name: t }));
    expect(types.filter((b) => b.getAttribute("aria-pressed") === "true")).toHaveLength(1);
    await userEvent.click(types[3]);
    expect(types[3]).toHaveAttribute("aria-pressed", "true");
  });

  it("reports a failed meal delete instead of failing silently", async () => {
    vi.mocked(api.deleteMeal).mockRejectedValue(new Error("engine offline"));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Delete breakfast at/ }));
    expect(await screen.findByText("engine offline")).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = renderPage();
    await screen.findByText("Today");
    await expectNoAxeViolations(container);
  });
});
