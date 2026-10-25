import type { Food, FoodPhotoResult, MlStatus } from "@ascend/shared";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { expectNoAxeViolations } from "../test/axe";
import { ScanMeal } from "./ScanMeal";

vi.mock("../api/client", () => ({ api: { mlStatus: vi.fn(), foodPhoto: vi.fn() } }));

const food = (id: number, name: string): Food =>
  ({ id, name, portion_label: "1 piece", portion_g: 40, kcal: 58, protein_g: 2, carbs_g: 12, fat_g: 0.2 }) as unknown as Food;
const FOODS = [food(1, "Idli"), food(2, "Plain dosa"), food(3, "Sambar")];

const status = (available: boolean): MlStatus => ({
  intent: { available: true, version: "1.0.0", threshold: 0.55, labels: [], reason: null },
  knowledge: { available: true, passages: 1473, sources: [] },
  food_photo: { available, reason: available ? null : "missing", version: available ? "0.1.0" : null, classes: available ? 4 : 0 },
});

const result = (over: Partial<FoodPhotoResult> = {}): FoodPhotoResult => ({
  suggestions: [
    { label: "idli", food_id: 1, name: "Idli", confidence: 0.81 },
    { label: "plain_dosa", food_id: 2, name: "Plain dosa", confidence: 0.12 },
    { label: "sambar", food_id: 3, name: "Sambar", confidence: 0.04 },
  ],
  result: "food",
  model_version: "0.1.0",
  must_confirm: true,
  ...over,
});

async function choosePhoto() {
  const file = new File([new Uint8Array([255, 216, 255, 217])], "plate.jpg", { type: "image/jpeg" });
  await userEvent.upload(screen.getByLabelText("Meal photo"), file);
}

describe("ScanMeal", () => {
  beforeEach(() => {
    vi.mocked(api.mlStatus).mockReset();
    vi.mocked(api.foodPhoto).mockReset();
  });

  it("is hidden when there is no food model", async () => {
    vi.mocked(api.mlStatus).mockResolvedValue(status(false));
    const { container } = render(<ScanMeal foods={FOODS} onPick={vi.fn()} />);
    await waitFor(() => expect(api.mlStatus).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("is hidden when the sidecar has no ml endpoints", async () => {
    vi.mocked(api.mlStatus).mockRejectedValue(new Error("404"));
    const { container } = render(<ScanMeal foods={FOODS} onPick={vi.fn()} />);
    await waitFor(() => expect(api.mlStatus).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("suggests three foods and only adds the one the user picks", async () => {
    vi.mocked(api.mlStatus).mockResolvedValue(status(true));
    vi.mocked(api.foodPhoto).mockResolvedValue(result());
    const onPick = vi.fn();
    render(<ScanMeal foods={FOODS} onPick={onPick} />);
    expect(await screen.findByRole("button", { name: /Scan meal/ })).toBeInTheDocument();
    await choosePhoto();
    expect(await screen.findByText(/Is it one of these\?/)).toBeInTheDocument();
    expect(api.foodPhoto).toHaveBeenCalledWith(expect.stringMatching(/^data:image\/jpeg;base64,/));
    expect(screen.getAllByRole("button", { name: /%$/ })).toHaveLength(3);
    expect(onPick).not.toHaveBeenCalled();
    await expectNoAxeViolations(document.body);
    await userEvent.click(screen.getByRole("button", { name: /Plain dosa/ }));
    expect(onPick).toHaveBeenCalledTimes(1);
    expect(onPick).toHaveBeenCalledWith(FOODS[1]);
  });

  it("says when it sees no food and lets the user dismiss unsure guesses", async () => {
    vi.mocked(api.mlStatus).mockResolvedValue(status(true));
    vi.mocked(api.foodPhoto).mockResolvedValueOnce(result({ result: "not_food", suggestions: [] }));
    const onPick = vi.fn();
    render(<ScanMeal foods={FOODS} onPick={onPick} />);
    await screen.findByRole("button", { name: /Scan meal/ });
    await choosePhoto();
    expect(await screen.findByText(/don't see food/)).toBeInTheDocument();
    vi.mocked(api.foodPhoto).mockResolvedValueOnce(result({ result: "unsure" }));
    await choosePhoto();
    expect(await screen.findByText(/Not sure/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "None of these" }));
    expect(screen.queryByText(/Not sure/)).not.toBeInTheDocument();
    expect(onPick).not.toHaveBeenCalled();
  });

  it("shows the sidecar's error", async () => {
    vi.mocked(api.mlStatus).mockResolvedValue(status(true));
    vi.mocked(api.foodPhoto).mockRejectedValue(new Error("that file is not a photo ASCEND can read"));
    render(<ScanMeal foods={FOODS} onPick={vi.fn()} />);
    await screen.findByRole("button", { name: /Scan meal/ });
    await choosePhoto();
    expect(await screen.findByRole("alert")).toHaveTextContent("not a photo");
  });
});
