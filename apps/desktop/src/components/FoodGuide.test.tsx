import { render, screen } from "@testing-library/react";
import type { FoodGuide } from "@ascend/shared";
import { describe, expect, it } from "vitest";

import { FoodGuideBody } from "./FoodGuide";

const guide: FoodGuide = {
  day: "2026-10-23",
  source: "Dietary Guidelines for Indians, ICMR-NIN 2024",
  version: "foodrules-v1",
  guidelines: [
    { title: "Keep salt to about 5 g a day", detail: "About one teaspoon in all." },
    { title: "Get protein from food", detail: "Dal, curd, eggs." },
  ],
  foods_logged: 3,
  groups: [
    { key: "cereals_millets", label: "Cereals and millets", count: 1, core: true },
    { key: "vegetables", label: "Vegetables", count: 0, core: true },
    { key: "eggs_fish_meat", label: "Eggs, fish or meat", count: 0, core: false },
  ],
  missing: ["Vegetables"],
  hfss: ["Samosa"],
  tips: ["Add a vegetable or a piece of fruit: half the plate is the target."],
};

const BODY = /weight|body ?fat|bmi|slim|thin/i;

describe("FoodGuideBody", () => {
  it("marks the groups on today's plate and lists the tips", () => {
    render(<FoodGuideBody guide={guide} />);
    expect(screen.getByTestId("group-cereals_millets")).toHaveAttribute("data-on", "true");
    expect(screen.getByTestId("group-vegetables")).toHaveAttribute("data-on", "false");
    expect(screen.getByTestId("group-eggs_fish_meat")).toHaveTextContent("(optional)");
    expect(screen.getByTestId("food-guide-hfss")).toHaveTextContent("Samosa");
    expect(screen.getByText(/half the plate/)).toBeInTheDocument();
    expect(screen.getByText("The 2 guidelines")).toBeInTheDocument();
    expect(screen.getByText(/ICMR-NIN 2024/)).toBeInTheDocument();
  });

  it("never talks about the body", () => {
    render(<FoodGuideBody guide={guide} />);
    expect(screen.getByTestId("food-guide").textContent ?? "").not.toMatch(BODY);
  });
});
