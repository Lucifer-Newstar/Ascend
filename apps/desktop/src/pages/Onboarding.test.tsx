import type { BaselineOut, GameSummary, Profile } from "@ascend/shared";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { FirstSteps } from "../components/FirstSteps";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { Onboarding, ProfileForm } from "./Onboarding";

vi.mock("../api/client", () => ({ api: { saveProfile: vi.fn(), updateSettings: vi.fn(), baseline: vi.fn(), game: vi.fn() } }));

const profile: Profile = {
  name: "Navin", age: 21, sex: "male", height_cm: 172, weight_kg: 68, goal: "maintain", activity: "moderate", target_weight_kg: null,
  focus: "skills", equipment: ["pullup_bar"],
  energy: { bmr: 1650, tdee: 2560, kcal_target: 2560, protein_target_g: 109, formula_version: "tdee-v1", is_estimate: true },
};

const game = {
  xp: { total: 120, today: 120, level: 2, xp_into_level: 20, xp_for_next: 150, rank: "E", rank_title: "Awakened", daily_cap: 600, formula_version: "x" },
  streak: { current: 1, best: 1, freezes_held: 0, freezes_used: 0, active_today: true },
  calm: { current: 0, best: 0, active_today: false },
  quest: [{ id: 1, day: "2026-10-20", kind: "training", code: "train_lats", title: "3 hard sets for lats", detail: "", metric: "sets:lats", target: 3, progress: 0, xp: 40, completed_at: null }],
} as unknown as GameSummary;

const save = vi.fn(async (patch) => ({ ...DEFAULT_SETTINGS, reduce_motion: true, ...patch }));

function renderOnboarding(onDone = vi.fn()) {
  return render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, reduce_motion: true }} save={save}>
      <Onboarding onDone={onDone} />
    </PrefsProvider>,
  );
}

beforeEach(() => {
  vi.mocked(api.saveProfile).mockReset().mockResolvedValue(profile);
  vi.mocked(api.baseline).mockReset();
  vi.mocked(api.game).mockReset().mockResolvedValue(game);
  save.mockClear();
});

describe("Onboarding (Awakening)", () => {
  it("walks five steps, saves focus, goal and equipment, logs the baseline and shows the first quest", async () => {
    const result: BaselineOut = {
      baseline: { pushups: 22, plank_s: 60, taken_at: "2026-10-20T08:00:00" }, workout_id: 3, sets_logged: 2, xp_awarded: 54, level: 2, rank: "E", steps_unlocked: [],
    };
    vi.mocked(api.baseline).mockResolvedValue(result);
    const done = vi.fn();
    renderOnboarding(done);
    expect(screen.getByRole("img", { name: "Step 1 of 5" })).toBeInTheDocument();
    await userEvent.type(screen.getByRole("textbox", { name: "Name (optional)" }), "Navin");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("img", { name: "Step 2 of 5" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Fat loss/ }));
    // The calorie goal follows the focus until it is set by hand.
    expect(screen.getByRole("button", { name: "Cut" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: /Skills/ }));
    expect(screen.getByRole("button", { name: "Maintain" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Training days per week" }), "4");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("img", { name: "Step 3 of 5" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: /Pull-up bar/ }));
    await userEvent.click(screen.getByRole("button", { name: "Save and continue" }));
    await waitFor(() => expect(api.saveProfile).toHaveBeenCalledWith(expect.objectContaining({ name: "Navin", focus: "skills", goal: "maintain", equipment: ["pullup_bar"] })));
    expect(save).toHaveBeenCalledWith(expect.objectContaining({ sessions_per_week: 4, units: "metric" }));

    expect(await screen.findByRole("img", { name: "Step 4 of 5" })).toBeInTheDocument();
    expect(screen.getByRole("spinbutton", { name: /Max pull-ups/ })).toBeInTheDocument(); // has a bar
    await userEvent.type(screen.getByRole("spinbutton", { name: /Max strict push-ups/ }), "22");
    await userEvent.type(screen.getByRole("spinbutton", { name: /Plank hold/ }), "60");
    await userEvent.click(screen.getByRole("button", { name: "Log my baseline" }));
    await waitFor(() => expect(api.baseline).toHaveBeenCalledWith({ pushups: 22, pullups: null, dead_hang_s: null, plank_s: 60, squats_60s: null, bodyweight_kg: null }));

    const win = await screen.findByTestId("awakened");
    expect(win).toHaveTextContent("You have been selected.");
    expect(await screen.findByText("3 hard sets for lats")).toBeInTheDocument();
    expect(win).toHaveTextContent("+54 XP");
    expect(screen.getAllByTestId("count-up").map((n) => n.textContent)).toEqual(["1,650", "2,560", "2,560", "109"]);
    // The trainer is picked here, in the one first-run flow (Settings can change it later).
    const picker = within(win).getByTestId("trainer-picker");
    await userEvent.click(within(picker).getAllByRole("radio")[1]);
    await waitFor(() => expect(save).toHaveBeenCalledWith(expect.objectContaining({ trainer_id: expect.any(String) })));
    await userEvent.click(screen.getByRole("button", { name: "Enter ASCEND" }));
    expect(done).toHaveBeenCalled();
  });

  it("can skip the optional steps and the test, and hides bar tests without a bar", async () => {
    vi.mocked(api.saveProfile).mockResolvedValue({ ...profile, equipment: ["dumbbells"] });
    renderOnboarding();
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await userEvent.click(await screen.findByRole("button", { name: "Skip" }));
    await userEvent.click(await screen.findByRole("checkbox", { name: /Dumbbells/ }));
    await userEvent.click(screen.getByRole("button", { name: "Save and continue" }));
    expect(await screen.findByRole("img", { name: "Step 4 of 5" })).toBeInTheDocument();
    expect(screen.queryByRole("spinbutton", { name: /Max pull-ups/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Skip the test" }));
    expect(api.baseline).not.toHaveBeenCalled();
    expect(await screen.findByTestId("awakened")).toHaveTextContent("No baseline yet");
  });

  it("enters height and weight in the chosen units", async () => {
    renderOnboarding();
    await userEvent.click(screen.getByRole("button", { name: "Imperial (lb, in)" }));
    const weight = screen.getByRole("spinbutton", { name: /Weight/ });
    expect(weight).toHaveValue(149.9); // 68 kg
    await userEvent.clear(weight);
    await userEvent.type(weight, "176");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await userEvent.click(await screen.findByRole("button", { name: "Skip" }));
    await userEvent.click(await screen.findByRole("button", { name: "Skip" }));
    await waitFor(() => expect(api.saveProfile).toHaveBeenCalledWith(expect.objectContaining({ weight_kg: 79.8 })));
  });

  it("has no axe violations", async () => {
    const { container } = renderOnboarding();
    await expectNoAxeViolations(container);
  });
});

describe("ProfileForm (Settings)", () => {
  it("keeps the equipment checklist editable", async () => {
    const onSaved = vi.fn();
    render(<ProfileForm initial={profile} onSaved={onSaved} submitLabel="Save profile" />);
    expect(screen.getByRole("checkbox", { name: /Pull-up bar/ })).toBeChecked();
    await userEvent.click(screen.getByRole("checkbox", { name: /Rings/ }));
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await waitFor(() => expect(api.saveProfile).toHaveBeenCalledWith(expect.objectContaining({ equipment: ["pullup_bar", "rings"], focus: "skills" })));
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
