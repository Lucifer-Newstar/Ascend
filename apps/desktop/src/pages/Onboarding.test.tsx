import type { Profile } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { FirstSteps } from "../components/FirstSteps";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { Onboarding } from "./Onboarding";

vi.mock("../api/client", () => ({ api: { saveProfile: vi.fn(), updateSettings: vi.fn() } }));

const profile: Profile = {
  name: "Navin", age: 21, sex: "male", height_cm: 172, weight_kg: 68, goal: "maintain", activity: "moderate", target_weight_kg: null,
  energy: { bmr: 1650, tdee: 2560, kcal_target: 2560, protein_target_g: 109, formula_version: "tdee-v1", is_estimate: true },
} as Profile;

function renderOnboarding(onDone = vi.fn()) {
  return render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, reduce_motion: true }} save={vi.fn()}>
      <Onboarding onDone={onDone} />
    </PrefsProvider>,
  );
}

describe("Onboarding", () => {
  it("shows the step, marks the chosen goal as pressed and moves to the targets", async () => {
    vi.mocked(api.saveProfile).mockResolvedValue(profile);
    const done = vi.fn();
    renderOnboarding(done);
    expect(screen.getByRole("img", { name: "Step 1 of 2" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "maintain" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: "bulk" }));
    expect(screen.getByRole("button", { name: "bulk" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "maintain" })).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(screen.getByRole("button", { name: "Calculate my targets" }));
    expect(await screen.findByRole("img", { name: "Step 2 of 2" })).toBeInTheDocument();
    expect(api.saveProfile).toHaveBeenCalledWith(expect.objectContaining({ goal: "bulk" }));
    expect(screen.getAllByTestId("count-up").map((n) => n.textContent)).toEqual(["1,650", "2,560", "2,560", "109"]);
    await userEvent.click(screen.getByRole("button", { name: "Enter ASCEND" }));
    expect(done).toHaveBeenCalled();
  });

  it("has no axe violations", async () => {
    const { container } = renderOnboarding();
    await expectNoAxeViolations(container);
  });
});

describe("FirstSteps", () => {
  it("sends a new user to Training or Diet", async () => {
    const nav = vi.fn();
    render(<FirstSteps onNavigate={nav} />);
    expect(screen.getByRole("heading", { name: /welcome to ascend/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /log a set/i }));
    await userEvent.click(screen.getByRole("button", { name: /log a meal/i }));
    expect(nav.mock.calls).toEqual([["workout"], ["diet"]]);
  });
});
