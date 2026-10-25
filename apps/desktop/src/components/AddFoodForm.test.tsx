import type { Food } from "@ascend/shared";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { expectNoAxeViolations } from "../test/axe";
import { AddFoodForm } from "./AddFoodForm";
import { ToastProvider } from "./Toast";

vi.mock("../api/client", () => ({ api: { addFood: vi.fn() } }));

const sundal: Food = { id: 300, name: "Amma's sundal", portion_label: "1 katori", portion_g: 100, kcal: 160, protein_g: 8, carbs_g: 22, fat_g: 4, source: "custom" };

function renderForm(initialName = "") {
  const onAdded = vi.fn();
  const onCancel = vi.fn();
  const view = render(
    <ToastProvider>
      <AddFoodForm initialName={initialName} onAdded={onAdded} onCancel={onCancel} />
    </ToastProvider>,
  );
  return { onAdded, onCancel, ...view };
}

describe("AddFoodForm", () => {
  beforeEach(() => vi.mocked(api.addFood).mockReset());

  it("saves a food of your own with its numbers per portion", async () => {
    vi.mocked(api.addFood).mockResolvedValue(sundal);
    const { onAdded, container } = renderForm("Amma's sundal");
    expect(screen.getByLabelText("Name")).toHaveValue("Amma's sundal");
    await userEvent.clear(screen.getByLabelText("Portion"));
    await userEvent.type(screen.getByLabelText("Portion"), "1 katori");
    await userEvent.type(screen.getByLabelText("kcal"), "160");
    await userEvent.type(screen.getByLabelText("Protein g"), "8");
    await userEvent.click(screen.getByRole("button", { name: "Save food" }));
    expect(api.addFood).toHaveBeenCalledWith({
      name: "Amma's sundal", portion_label: "1 katori", portion_g: 100, kcal: 160, protein_g: 8, carbs_g: 0, fat_g: 0,
    });
    expect(onAdded).toHaveBeenCalledWith(sundal);
    await expectNoAxeViolations(container);
  });

  it("asks for a name and the calories before saving", async () => {
    renderForm();
    await userEvent.click(screen.getByRole("button", { name: "Save food" }));
    expect(within(screen.getByTestId("add-food-form")).getByRole("alert")).toHaveTextContent("Give the food a name.");
    await userEvent.type(screen.getByLabelText("Name"), "Kozhukattai");
    await userEvent.click(screen.getByRole("button", { name: "Save food" }));
    expect(within(screen.getByTestId("add-food-form")).getByRole("alert")).toHaveTextContent("Calories per portion are needed.");
    expect(api.addFood).not.toHaveBeenCalled();
  });

  it("shows the sidecar's answer when the name is taken", async () => {
    vi.mocked(api.addFood).mockRejectedValueOnce(new Error("A food called “Milk (toned)” already exists."));
    renderForm("milk (toned)");
    await userEvent.type(screen.getByLabelText("kcal"), "60");
    await userEvent.click(screen.getByRole("button", { name: "Save food" }));
    expect(await within(screen.getByTestId("add-food-form")).findByRole("alert")).toHaveTextContent("already exists");
  });
});
