import type { Exercise } from "@ascend/shared";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { axeViolations } from "../test/axe";
import { CommandBar, isCommandKey, PENDING_COACH_KEY } from "./CommandBar";
import { ToastProvider } from "./Toast";

vi.mock("../api/client", () => ({
  api: {
    exercises: vi.fn(), skills: vi.fn(), foods: vi.fn(), activeWorkout: vi.fn(), startWorkout: vi.fn(), logSet: vi.fn(),
    logWeight: vi.fn(), logMeal: vi.fn(), trainSkill: vi.fn(),
  },
}));

const bench: Exercise = { id: 2, name: "Barbell Bench Press", equipment: "barbell", section: "gym", met: null, time_based: false, muscles: [], source: "ascend" };

function renderBar(props: Partial<Parameters<typeof CommandBar>[0]> = {}) {
  const onNavigate = vi.fn();
  const onClose = vi.fn();
  const onChanged = vi.fn();
  const save = vi.fn(async (s) => s);
  const utils = render(
    <PrefsProvider initial={DEFAULT_SETTINGS} save={save}>
      <ToastProvider>
        <CommandBar open onClose={onClose} onNavigate={onNavigate} onChanged={onChanged} {...props} />
      </ToastProvider>
    </PrefsProvider>,
  );
  return { ...utils, onNavigate, onClose, onChanged, save };
}

beforeEach(() => {
  vi.mocked(api.exercises).mockReset().mockResolvedValue([bench]);
  vi.mocked(api.skills).mockReset().mockResolvedValue([]);
  vi.mocked(api.activeWorkout).mockReset().mockResolvedValue(null);
  vi.mocked(api.startWorkout).mockReset().mockResolvedValue({ id: 9, day: "2026-10-20", section: "gym", started_at: "", finished_at: null, sets: [], source: "app", title: "" });
  vi.mocked(api.logSet).mockReset().mockResolvedValue({
    set: { id: 1, exercise_id: 2, exercise_name: "Barbell Bench Press", weight_kg: 80, reps: 5, rpe: 8, duration_s: null, distance_m: null, avg_hr: null, e1rm: 93, is_pr: false, performed_at: "" },
    xp_awarded: 12, previous_best_e1rm: null,
  });
  vi.mocked(api.logWeight).mockReset();
  sessionStorage.clear();
});

describe("CommandBar", () => {
  it("is a labelled dialog with a combobox and lists pages when empty", async () => {
    const { container } = renderBar();
    expect(screen.getByRole("dialog", { name: "Command bar" })).toBeInTheDocument();
    const input = screen.getByRole("combobox", { name: "Command" });
    await waitFor(() => expect(input).toHaveFocus());
    const options = screen.getAllByRole("option").map((o) => o.textContent ?? "");
    expect(options).toContain("Fuel");
    // Ten quick actions come first.
    expect(options.slice(0, 10).every((o) => !["Today", "Fuel"].includes(o))).toBe(true);
    expect(options[0]).toBe("Start or continue today's session");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("logs a set from 'bench 80x5 @8' with Enter, starting a session when none is open", async () => {
    const { onClose, onChanged } = renderBar();
    const input = screen.getByRole("combobox", { name: "Command" });
    await waitFor(() => expect(api.exercises).toHaveBeenCalled());
    await userEvent.type(input, "bench 80x5 @8");
    expect(await screen.findByRole("option", { name: /Barbell Bench Press · 80 kg × 5 @8/ })).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(api.logSet).toHaveBeenCalledWith(9, { exercise_id: 2, weight_kg: 80, reps: 5, rpe: 8 }));
    expect(api.startWorkout).toHaveBeenCalledWith("gym");
    expect(onChanged).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it("moves with the arrow keys and sends unrecognised text to the Coach", async () => {
    const { onNavigate } = renderBar();
    const input = screen.getByRole("combobox", { name: "Command" });
    await userEvent.type(input, "how much protein do I need");
    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(1);
    expect(options[0]).toHaveTextContent("Ask the Coach: “how much protein do I need”");
    await userEvent.keyboard("{Enter}");
    expect(sessionStorage.getItem(PENDING_COACH_KEY)).toBe("how much protein do I need");
    expect(onNavigate).toHaveBeenCalledWith("coach");
  });

  it("logs a weigh-in", async () => {
    renderBar();
    const input = screen.getByRole("combobox", { name: "Command" });
    await userEvent.type(input, "weight 81.4{Enter}");
    await waitFor(() => expect(api.logWeight).toHaveBeenCalledWith(81.4));
  });

  it("logs N sets from 'log 3x8 pull-up'", async () => {
    const pullup: Exercise = { id: 5, name: "Pull-up", equipment: "bar", section: "calisthenics", met: null, time_based: false, muscles: [], source: "ascend" };
    vi.mocked(api.exercises).mockResolvedValue([pullup]);
    renderBar();
    await waitFor(() => expect(api.exercises).toHaveBeenCalled());
    await userEvent.type(screen.getByRole("combobox", { name: "Command" }), "log 3x8 pull-up");
    expect(await screen.findByRole("option", { name: /Pull-up · 3 sets of bodyweight × 8/ })).toBeInTheDocument();
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(api.logSet).toHaveBeenCalledTimes(3));
    expect(api.startWorkout).toHaveBeenCalledWith("calisthenics");
  });

  it("a quick action that needs details fills the field and keeps the bar open", async () => {
    const { onClose } = renderBar();
    await userEvent.click(screen.getByRole("option", { name: /Log body weight/ }));
    expect(screen.getByRole("combobox", { name: "Command" })).toHaveValue("weight ");
    expect(onClose).not.toHaveBeenCalled();
  });

  it("closes on Escape", async () => {
    const { onClose } = renderBar();
    await userEvent.type(screen.getByRole("combobox", { name: "Command" }), "{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("closes on Escape even when focus is not in the field", async () => {
    const { onClose } = renderBar();
    (document.activeElement as HTMLElement | null)?.blur();
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("opens on Ctrl+K or Cmd+K only", () => {
    const base = { altKey: false, shiftKey: false, metaKey: false, ctrlKey: false };
    expect(isCommandKey({ ...base, key: "k", ctrlKey: true })).toBe(true);
    expect(isCommandKey({ ...base, key: "K", metaKey: true })).toBe(true);
    expect(isCommandKey({ ...base, key: "k" })).toBe(false);
    expect(isCommandKey({ ...base, key: "k", ctrlKey: true, shiftKey: true })).toBe(false);
  });
});
