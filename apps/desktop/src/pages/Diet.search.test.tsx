import type { Food } from "@ascend/shared";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { DietPage, addFoodFromHash } from "./Diet";

vi.mock("../api/client", () => ({
  api: { foods: vi.fn(), addFood: vi.fn(), dayLog: vi.fn(), logMeal: vi.fn(), deleteMeal: vi.fn(), updateSettings: vi.fn(), tdee: vi.fn(), tdeeExplanation: vi.fn(), planDiet: vi.fn(), savedDiets: vi.fn(), saveDiet: vi.fn(), deleteDiet: vi.fn(), foodGuide: vi.fn() },
}));

const food = (id: number, name: string): Food => ({ id, name, portion_label: "1 katori", portion_g: 150, kcal: 200, protein_g: 6, carbs_g: 30, fat_g: 5, source: "approx" });
const TABLE = [food(1, "Idli"), food(2, "Sakkarai pongal"), food(3, "Ven pongal")];

function renderPage() {
  return render(
    <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()}>
      <ToastProvider>
        <DietPage onChanged={() => {}} />
      </ToastProvider>
    </PrefsProvider>,
  );
}

describe("Diet food search (v1.3)", () => {
  beforeEach(() => {
    vi.mocked(api.foods).mockImplementation(async (q = "") =>
      q ? TABLE.filter((f) => f.name.toLowerCase().includes(q.toLowerCase())).sort((a) => (a.name === "Ven pongal" ? -1 : 1)) : TABLE);
    vi.mocked(api.dayLog).mockRejectedValue(new Error("not needed here"));
    vi.mocked(api.savedDiets).mockResolvedValue([]);
    vi.mocked(api.foodGuide).mockRejectedValue(new Error("not needed here"));
    vi.mocked(api.tdee).mockRejectedValue(new Error("not needed here"));
  });
  afterEach(() => {
    window.location.hash = "";
  });

  it("asks the sidecar once typing pauses and shows its ranking", async () => {
    renderPage();
    expect(await screen.findByRole("button", { name: /Sakkarai pongal/ })).toBeInTheDocument();
    expect(api.foods).toHaveBeenLastCalledWith("");
    await userEvent.type(screen.getByLabelText("Search foods"), "pongal");
    await act(() => new Promise((r) => setTimeout(r, 300)));
    expect(api.foods).toHaveBeenLastCalledWith("pongal");
    expect(vi.mocked(api.foods).mock.calls.filter(([q]) => q && q !== "pongal")).toHaveLength(0);
    const rows = screen.getAllByRole("button", { name: /pongal/ });
    expect(rows[0]).toHaveTextContent("Ven pongal");
  });

  it("offers to add a food the table does not have", async () => {
    renderPage();
    await userEvent.type(await screen.findByLabelText("Search foods"), "kozhukattai");
    await userEvent.click(await screen.findByRole("button", { name: "Add “kozhukattai” as your own food" }, { timeout: 2000 }));
    expect(screen.getByTestId("add-food-form")).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveValue("kozhukattai");
  });

  it("opens the form from the trainer chat link", async () => {
    expect(addFoodFromHash("#diet/add-food/ragi%20dosa")).toBe("ragi dosa");
    expect(addFoodFromHash("#diet/add-food")).toBe("");
    expect(addFoodFromHash("#diet")).toBeNull();
    window.location.hash = "diet/add-food/ragi%20dosa";
    renderPage();
    expect(await screen.findByLabelText("Name")).toHaveValue("ragi dosa");
  });
});
