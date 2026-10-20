import type { DayLog, Food } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { DietPage } from "./Diet";

vi.mock("../api/client", () => ({
  api: { foods: vi.fn(), dayLog: vi.fn(), logMeal: vi.fn(), deleteMeal: vi.fn(), updateSettings: vi.fn() },
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
