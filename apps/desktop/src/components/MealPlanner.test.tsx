import type { DietPlan } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { DietPlanner } from "./MealPlanner";
import { ToastProvider } from "./Toast";

vi.mock("../api/client", () => ({
  api: { planDiet: vi.fn(), savedDiets: vi.fn(), saveDiet: vi.fn(), deleteDiet: vi.fn() },
}));

const diet: DietPlan = {
  kcal_target: 2600, protein_target_g: 120, diet: "nonveg", notes: [], phrased_by: "rules", algo_version: "diet-gen-v1",
  flags: [{ code: "under_18_maintenance", severity: "block", message: "Under 18: planned at maintenance, not a deficit." }],
  days: [{ day: 1, kcal: 2600, protein_g: 121, meals: [
    { meal: "breakfast", kcal: 600, protein_g: 30, items: [{ food: "Egg", portions: 3, portion_label: "piece", kcal: 210, protein_g: 18 }] },
  ] }],
};

describe("meal planner (on Fuel)", () => {
  beforeEach(() => {
    vi.mocked(api.savedDiets).mockResolvedValue([]);
  });

  it("plans meals and hides calories when asked", async () => {
    vi.mocked(api.planDiet).mockResolvedValue(diet);
    render(
      <PrefsProvider initial={{ ...DEFAULT_SETTINGS, hide_calories: true }} save={vi.fn()}>
        <ToastProvider><DietPlanner /></ToastProvider>
      </PrefsProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Plan my meals" }));
    const d = await screen.findByTestId("diet-draft");
    expect(d).toHaveTextContent("120 g protein a day");
    expect(d).not.toHaveTextContent("kcal");
    expect(d).toHaveTextContent("Adjusted");
  });
});
