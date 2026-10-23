import type { BaselineOut, GameSummary, Profile } from "@ascend/shared";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { FirstSteps } from "../components/FirstSteps";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { Onboarding, ProfileForm } from "./Onboarding";

vi.mock("../api/client", () => ({
  api: { saveProfile: vi.fn(), updateSettings: vi.fn(), baseline: vi.fn(), game: vi.fn(), logWeight: vi.fn(), backups: vi.fn().mockResolvedValue([]) },
}));

const profile: Profile = {
  name: "Navin", age: 21, sex: "male", height_cm: 172, weight_kg: 68, goal: "maintain", activity: "moderate", target_weight_kg: null,
  focus: "skills", equipment: ["pullup_bar"],
  energy: { bmr: 1650, tdee: 2560, kcal_target: 2560, protein_target_g: 109, formula_version: "tdee-v1", is_estimate: true },
};

const game = {
  xp: { total: 120, today: 120, level: 2, xp_into_level: 20, xp_for_next: 150, rank: "E", rank_title: "Awakened", daily_cap: 600, formula_version: "x" },
  streak: { current: 1, best: 1, excused: 0, reason_due: null, active_today: true },
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

async function fillBody(weight = "68") {
  await userEvent.type(screen.getByRole("spinbutton", { name: /^Age/ }), "21");
  await userEvent.type(screen.getByRole("spinbutton", { name: /^Height/ }), "172");
  await userEvent.type(screen.getByRole("spinbutton", { name: /^Weight/ }), weight);
  await userEvent.click(screen.getByRole("button", { name: "Male" }));
}

beforeEach(() => {
  vi.mocked(api.saveProfile).mockReset().mockResolvedValue(profile);
  vi.mocked(api.baseline).mockReset();
  vi.mocked(api.logWeight).mockReset().mockResolvedValue({} as never);
  vi.mocked(api.game).mockReset().mockResolvedValue(game);
  save.mockClear();
});

describe("Onboarding (v1.2)", () => {
  it("opens on the System intro with Begin and Restore my data", async () => {
    renderOnboarding();
    expect(screen.getByTestId("landing")).toHaveTextContent("A new Hunter has awakened.");
    await userEvent.click(screen.getByRole("button", { name: "Restore my data" }));
    expect(await screen.findByRole("heading", { name: "Restore my data" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("button", { name: "Begin" })).toBeInTheDocument();
  });

  it("walks three steps with empty fields, saves the profile and the first weigh-in, and offers the baseline test", async () => {
    const result: BaselineOut = {
      baseline: { pushups: 22, plank_s: 60, taken_at: "2026-10-20T08:00:00" }, workout_id: 3, sets_logged: 2, xp_awarded: 54, level: 2, rank: "E", steps_unlocked: [],
    };
    vi.mocked(api.baseline).mockResolvedValue(result);
    const done = vi.fn();
    renderOnboarding(done);
    await userEvent.click(screen.getByRole("button", { name: "Begin" }));
    expect(screen.getByRole("img", { name: "Step 1 of 3" })).toBeInTheDocument();
    // No made-up numbers: every body field starts empty.
    for (const name of [/^Age/, /^Height/, /^Weight/, /^Goal weight/]) expect(screen.getByRole("spinbutton", { name })).toHaveValue(null);
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter your age");
    await userEvent.type(screen.getByRole("textbox", { name: "Name (optional)" }), "Navin");
    await fillBody();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(await screen.findByRole("img", { name: "Step 2 of 3" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cut" })).toBeNull(); // the goal decides it
    await userEvent.click(screen.getByRole("button", { name: /Learn bodyweight skills/ }));
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Days a week you can train" }), "4");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(await screen.findByRole("img", { name: "Step 3 of 3" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: /Pull-up bar/ }));
    await userEvent.click(screen.getByRole("button", { name: "Finish" }));
    await waitFor(() => expect(api.saveProfile).toHaveBeenCalledWith(expect.objectContaining({
      name: "Navin", age: 21, height_cm: 172, weight_kg: 68, focus: "skills", goal: "maintain", equipment: ["pullup_bar"], target_weight_kg: null,
    })));
    expect(save).toHaveBeenCalledWith(expect.objectContaining({ sessions_per_week: 4, units: "metric" }));
    expect(api.logWeight).toHaveBeenCalledWith(68);

    const win = await screen.findByTestId("awakened");
    expect(win).toHaveTextContent("You have been selected.");
    expect(await screen.findByText("3 hard sets for lats")).toBeInTheDocument();
    expect(screen.getAllByTestId("count-up").map((n) => n.textContent)).toEqual(["2,560", "109"]);
    await userEvent.click(within(win).getByRole("button", { name: "Take the test" }));
    expect(screen.getByRole("spinbutton", { name: /Max pull-ups/ })).toBeInTheDocument(); // has a bar
    await userEvent.type(screen.getByRole("spinbutton", { name: /Max strict push-ups/ }), "22");
    await userEvent.type(screen.getByRole("spinbutton", { name: /Plank hold/ }), "60");
    await userEvent.click(screen.getByRole("button", { name: "Log my baseline" }));
    await waitFor(() => expect(api.baseline).toHaveBeenCalledWith({ pushups: 22, pullups: null, dead_hang_s: null, plank_s: 60, squats_60s: null }));
    expect(await screen.findByTestId("awakened")).toHaveTextContent("+54 XP");
    const picker = within(screen.getByTestId("awakened")).getByTestId("trainer-picker");
    await userEvent.click(within(picker).getAllByRole("radio")[1]);
    await waitFor(() => expect(save).toHaveBeenCalledWith(expect.objectContaining({ trainer_id: expect.any(String) })));
    await userEvent.click(screen.getByRole("button", { name: "Enter ASCEND" }));
    expect(done).toHaveBeenCalled();
  });

  it("enters height and weight in the chosen units, and the goal weight is optional", async () => {
    vi.mocked(api.saveProfile).mockResolvedValue({ ...profile, equipment: ["dumbbells"] });
    renderOnboarding();
    await userEvent.click(screen.getByRole("button", { name: "Begin" }));
    await userEvent.click(screen.getByRole("button", { name: "Imperial (lb, in)" }));
    await fillBody("176");
    await userEvent.type(screen.getByRole("spinbutton", { name: /^Goal weight/ }), "165");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await userEvent.click(await screen.findByRole("button", { name: /Just get fit/ }));
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await userEvent.click(await screen.findByRole("checkbox", { name: /Dumbbells/ }));
    await userEvent.click(screen.getByRole("button", { name: "Finish" }));
    await waitFor(() => expect(api.saveProfile).toHaveBeenCalledWith(expect.objectContaining({ weight_kg: 79.8, target_weight_kg: 74.8, focus: null, goal: "maintain" })));
    const win = await screen.findByTestId("awakened");
    await userEvent.click(within(win).getByRole("button", { name: "Take the test" }));
    expect(screen.queryByRole("spinbutton", { name: /Max pull-ups/ })).not.toBeInTheDocument(); // no bar
    await userEvent.click(screen.getByRole("button", { name: "Not now" }));
    expect(api.baseline).not.toHaveBeenCalled();
  });

  it("has no axe violations", async () => {
    const { container } = renderOnboarding();
    await expectNoAxeViolations(container);
    await userEvent.click(screen.getByRole("button", { name: "Begin" }));
    await expectNoAxeViolations(container);
  });
});

describe("ProfileForm (Settings)", () => {
  it("keeps the equipment checklist and the goal editable", async () => {
    const onSaved = vi.fn();
    render(<ProfileForm initial={profile} onSaved={onSaved} submitLabel="Save profile" />);
    expect(screen.getByRole("checkbox", { name: /Pull-up bar/ })).toBeChecked();
    expect(screen.getByRole("button", { name: /Learn bodyweight skills/ })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("checkbox", { name: /Rings/ }));
    await userEvent.click(screen.getByRole("button", { name: /Lose fat/ }));
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await waitFor(() => expect(api.saveProfile).toHaveBeenCalledWith(expect.objectContaining({ equipment: ["pullup_bar", "rings"], focus: "fat_loss", goal: "cut" })));
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
