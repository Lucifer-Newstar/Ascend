import type { Exercise, Workout } from "@ascend/shared";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { WorkoutPage } from "./Workout";

vi.mock("../api/client", () => ({
  api: {
    exercises: vi.fn(),
    activeWorkout: vi.fn(),
    startWorkout: vi.fn(),
    logSet: vi.fn(),
    editSet: vi.fn(),
    deleteSet: vi.fn(),
    finishWorkout: vi.fn(),
    updateSettings: vi.fn(),
    previousSession: vi.fn(),
    exercise: vi.fn(),
  },
}));

const bench: Exercise = {
  id: 1, name: "Barbell Bench Press", equipment: "barbell", section: "gym", met: null, time_based: false,
  muscles: [{ muscle: "lower_chest", weight: 1 }],
};
const run: Exercise = {
  id: 50, name: "Running", equipment: "none", section: "cardio", met: 9.8, time_based: true,
  muscles: [{ muscle: "calves", weight: 1 }],
};
const session = (sets: Workout["sets"]): Workout => ({
  id: 9, day: "2026-10-20", section: "cardio", started_at: "2026-10-20T07:00:00", finished_at: null, sets,
  source: "app", title: "",
});

function renderPage() {
  return render(
    <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()}>
      <ToastProvider>
        <WorkoutPage onChanged={() => {}} />
      </ToastProvider>
    </PrefsProvider>,
  );
}

describe("Training page", () => {
  beforeEach(() => {
    vi.mocked(api.exercises).mockImplementation(async (...args) => (args[1] === "cardio" ? [run] : [bench]));
    vi.mocked(api.activeWorkout).mockResolvedValue(null);
    vi.mocked(api.previousSession).mockResolvedValue(null);
    vi.mocked(api.exercise).mockRejectedValue(new Error("not needed"));
  });

  it("switches section tabs and loads that library", async () => {
    renderPage();
    expect(await screen.findByText("Barbell Bench Press")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Cardio" }));
    expect(await screen.findByText("Running")).toBeInTheDocument();
    expect(api.exercises).toHaveBeenLastCalledWith("", "cardio");
    expect(screen.getByRole("tab", { name: "Cardio" })).toHaveAttribute("aria-selected", "true");
  });

  it("logs a timed run into a cardio session", async () => {
    vi.mocked(api.startWorkout).mockResolvedValue(session([]));
    const loggedSet = {
      id: 3, exercise_id: 50, exercise_name: "Running", weight_kg: 0, reps: 1, rpe: 7, duration_s: 1800,
      distance_m: null, avg_hr: null, e1rm: null, is_pr: false, performed_at: "2026-10-20T07:30:00",
    };
    vi.mocked(api.logSet).mockResolvedValue({ set: loggedSet, xp_awarded: 15, previous_best_e1rm: null });
    renderPage();
    await userEvent.click(await screen.findByRole("tab", { name: "Cardio" }));
    await userEvent.click(await screen.findByText("Running"));
    vi.mocked(api.activeWorkout).mockResolvedValue(session([loggedSet]));
    await userEvent.click(screen.getByRole("button", { name: "Log" }));
    await waitFor(() => expect(api.logSet).toHaveBeenCalled());
    expect(api.startWorkout).toHaveBeenCalledWith("cardio");
    expect(vi.mocked(api.logSet).mock.calls[0][1]).toMatchObject({ exercise_id: 50, duration_s: 1800, rpe: 7 });
    expect(await screen.findByText("30:00")).toBeInTheDocument();
    // The toast says it, and "+15 XP" floats off the form.
    expect((await screen.findAllByText(/\+15 XP/)).length).toBeGreaterThan(0);
  });

  it("animates a freshly logged lift: the row slides in with a check and +XP floats up", async () => {
    vi.mocked(api.startWorkout).mockResolvedValue({ ...session([]), section: "gym" });
    const lift = {
      id: 7, exercise_id: 1, exercise_name: "Barbell Bench Press", weight_kg: 60, reps: 8, rpe: 8, duration_s: null,
      distance_m: null, avg_hr: null, e1rm: 76, is_pr: false, performed_at: "2026-10-20T07:30:00",
    };
    vi.mocked(api.logSet).mockResolvedValue({ set: lift, xp_awarded: 12, previous_best_e1rm: null });
    renderPage();
    await userEvent.click(await screen.findByText("Barbell Bench Press"));
    vi.mocked(api.activeWorkout).mockResolvedValue({ ...session([lift]), section: "gym" });
    await userEvent.click(screen.getByRole("button", { name: "Log set" }));
    expect(await screen.findByTestId("set-xp-gain")).toHaveTextContent("+12 XP");
    const row = document.querySelector("tr[data-just-logged]");
    expect(row).toHaveClass("set-row-in");
    expect(within(row as HTMLElement).getByText("1")).toBeInTheDocument();
  });

  it("skips the +XP float with Reduce motion on (the toast still confirms)", async () => {
    vi.mocked(api.startWorkout).mockResolvedValue({ ...session([]), section: "gym" });
    const lift = {
      id: 8, exercise_id: 1, exercise_name: "Barbell Bench Press", weight_kg: 60, reps: 8, rpe: 8, duration_s: null,
      distance_m: null, avg_hr: null, e1rm: 76, is_pr: false, performed_at: "2026-10-20T07:30:00",
    };
    vi.mocked(api.logSet).mockResolvedValue({ set: lift, xp_awarded: 12, previous_best_e1rm: null });
    render(
      <PrefsProvider initial={{ ...DEFAULT_SETTINGS, reduce_motion: true }} save={vi.fn()}>
        <ToastProvider>
          <WorkoutPage onChanged={() => {}} />
        </ToastProvider>
      </PrefsProvider>,
    );
    await userEvent.click(await screen.findByText("Barbell Bench Press"));
    vi.mocked(api.activeWorkout).mockResolvedValue({ ...session([lift]), section: "gym" });
    await userEvent.click(screen.getByRole("button", { name: "Log set" }));
    expect(await screen.findByText(/Set logged · \+12 XP/)).toBeInTheDocument();
    expect(screen.queryByTestId("set-xp-gain")).toBeNull();
  });

  it("has no axe violations with a logged lift and a logged run", async () => {
    const lift = {
      id: 4, exercise_id: 1, exercise_name: "Barbell Bench Press", weight_kg: 60, reps: 8, rpe: 8, duration_s: null,
      distance_m: null, avg_hr: null, e1rm: 76, is_pr: true, performed_at: "2026-10-20T07:10:00",
    };
    const runSet = {
      id: 5, exercise_id: 50, exercise_name: "Running", weight_kg: 0, reps: 1, rpe: 6, duration_s: 1500,
      distance_m: 4000, avg_hr: 150, e1rm: null, is_pr: false, performed_at: "2026-10-20T07:40:00",
    };
    vi.mocked(api.activeWorkout).mockResolvedValue({ ...session([lift, runSet]), section: "gym" });
    const { container } = renderPage();
    await screen.findAllByRole("button", { name: "Edit set 1" });
    for (const table of container.querySelectorAll("table")) {
      const header = table.querySelectorAll("thead th").length;
      for (const row of table.querySelectorAll("tbody tr")) {
        const cells = [...row.children].reduce((n, c) => n + Number(c.getAttribute("colspan") ?? 1), 0);
        expect(cells).toBe(header);
      }
    }
    await expectNoAxeViolations(container);
  });

  it("deletes a set after confirming", async () => {
    const s = {
      id: 4, exercise_id: 1, exercise_name: "Barbell Bench Press", weight_kg: 60, reps: 8, rpe: 8, duration_s: null,
      distance_m: null, avg_hr: null, e1rm: 76, is_pr: false, performed_at: "2026-10-20T07:10:00",
    };
    vi.mocked(api.activeWorkout).mockResolvedValue({ ...session([s]), section: "gym" });
    vi.mocked(api.deleteSet).mockResolvedValue(null);
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Delete set 1" }));
    vi.mocked(api.activeWorkout).mockResolvedValue({ ...session([]), section: "gym" });
    await userEvent.click(screen.getByRole("button", { name: "Delete set 1?" }));
    await waitFor(() => expect(api.deleteSet).toHaveBeenCalledWith(9, 4));
    expect(await screen.findByText("No sets yet today.")).toBeInTheDocument();
  });

  it("logs a lift by pressing Enter in the reps field", async () => {
    vi.mocked(api.activeWorkout).mockResolvedValue({ ...session([]), section: "gym" });
    const loggedSet = {
      id: 5, exercise_id: 1, exercise_name: "Barbell Bench Press", weight_kg: 60, reps: 8, rpe: 8, duration_s: null,
      distance_m: null, avg_hr: null, e1rm: 76, is_pr: false, performed_at: "2026-10-20T07:12:00",
    };
    vi.mocked(api.logSet).mockResolvedValue({ set: loggedSet, xp_awarded: 10, previous_best_e1rm: null });
    renderPage();
    await userEvent.click(await screen.findByText("Barbell Bench Press"));
    const form = screen.getByRole("form", { name: "Log a set of Barbell Bench Press" });
    const reps = within(form).getByRole("spinbutton", { name: "Reps" });
    expect(form).toContainElement(reps);
    await userEvent.type(reps, "{Enter}");
    await waitFor(() => expect(api.logSet).toHaveBeenCalled());
    expect(vi.mocked(api.logSet).mock.calls.at(-1)?.[1]).toMatchObject({ exercise_id: 1 });
  });
  it("logs a plank as a hold and shows seconds in the session, opened from the gallery", async () => {
    const plank: Exercise = {
      id: 39, name: "Plank", equipment: "bodyweight", section: "calisthenics", met: null, time_based: false,
      muscles: [{ muscle: "abs", weight: 1 }], measure: "hold",
    };
    vi.mocked(api.exercises).mockResolvedValue([plank]);
    sessionStorage.setItem("ascend.pendingExercise", JSON.stringify({ id: 39, section: "calisthenics" }));
    vi.mocked(api.startWorkout).mockResolvedValue({ ...session([]), section: "calisthenics" });
    const held = {
      id: 4, exercise_id: 39, exercise_name: "Plank", weight_kg: 0, reps: 1, rpe: 8, duration_s: 45,
      distance_m: null, avg_hr: null, e1rm: null, is_pr: true, performed_at: "2026-10-20T07:30:00", measure: "hold" as const,
    };
    vi.mocked(api.logSet).mockResolvedValue({ set: held, xp_awarded: 3, previous_best_e1rm: null });
    renderPage();
    // The pending exercise opens straight into the hold form.
    expect(await screen.findByRole("button", { name: "Log hold" })).toBeInTheDocument();
    expect(api.exercises).toHaveBeenLastCalledWith("", "calisthenics");
    await userEvent.click(screen.getByRole("button", { name: "45 s" }));
    vi.mocked(api.activeWorkout).mockResolvedValue({ ...session([held]), section: "calisthenics" });
    await userEvent.click(screen.getByRole("button", { name: "Log hold" }));
    expect(api.logSet).toHaveBeenCalledWith(9, { exercise_id: 39, duration_s: 45, weight_kg: 0, reps: 1, rpe: 8 });
    const table = await screen.findByRole("table", { name: "Plank: logged sets" });
    expect(within(table).getByRole("columnheader", { name: "Hold" })).toBeInTheDocument();
    expect(within(table).getByText("45 s")).toBeInTheDocument();
    expect(await screen.findByText(/New best hold! Plank 45 s/)).toBeInTheDocument();
  });

  it("bodyweight moves start at no added load, and an unlocking set shows the Skill acquired moment", async () => {
    const pullup: Exercise = {
      id: 3, name: "Pull-up", equipment: "bodyweight", section: "calisthenics", met: null, time_based: false,
      muscles: [{ muscle: "lats", weight: 1 }], measure: "reps",
    };
    vi.mocked(api.exercises).mockResolvedValue([pullup]);
    sessionStorage.setItem("ascend.pendingExercise", JSON.stringify({ id: 3, section: "calisthenics" }));
    vi.mocked(api.startWorkout).mockResolvedValue({ ...session([]), section: "calisthenics" });
    const set = {
      id: 5, exercise_id: 3, exercise_name: "Pull-up", weight_kg: 0, reps: 8, rpe: 8, duration_s: null,
      distance_m: null, avg_hr: null, e1rm: null, is_pr: false, performed_at: "2026-10-20T07:30:00", measure: "reps" as const,
    };
    vi.mocked(api.logSet).mockResolvedValue({
      set, xp_awarded: 3, previous_best_e1rm: null,
      unlocks: [{ id: 1, skill_key: "muscle_up", skill_name: "Muscle-up", step_key: "c2b", step_name: "Chest-to-bar pull-up",
        unlocked_at: "2026-10-20T07:30:00", xp: 80, final: false, next_step_name: "Muscle-up negative", source: "log" }],
    });
    vi.mocked(api.activeWorkout).mockResolvedValue(null);
    renderPage();
    const load = await screen.findByRole("spinbutton", { name: "Added load (kg)" });
    expect(load).toHaveValue(0);
    await userEvent.click(screen.getByRole("button", { name: "Log set" }));
    expect(vi.mocked(api.logSet).mock.calls.at(-1)?.[1]).toMatchObject({ exercise_id: 3, weight_kg: 0 });
    const dialog = await screen.findByRole("dialog", { name: "Chest-to-bar pull-up" });
    expect(dialog).toHaveTextContent("Skill acquired");
    await userEvent.click(within(dialog).getByRole("button", { name: "Continue" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows last session in grey and logs 5 sets keyboard-only with 5 Enters (≤15 keystrokes)", async () => {
    const mk = (id: number, reps: number, extra: Partial<Workout["sets"][number]> = {}) => ({
      id, exercise_id: 1, exercise_name: "Barbell Bench Press", weight_kg: 60, reps, rpe: 8, duration_s: null,
      distance_m: null, avg_hr: null, e1rm: 76, is_pr: false, performed_at: "2026-10-18T07:00:00", measure: "reps" as const, ...extra,
    });
    vi.mocked(api.logSet).mockReset();
    const last = [mk(101, 8), mk(102, 8), mk(103, 7), mk(104, 6), mk(105, 6)];
    vi.mocked(api.previousSession).mockResolvedValue({ workout_id: 3, day: "2026-10-18", source: "app", sets: last });
    const today: Workout["sets"] = [];
    vi.mocked(api.activeWorkout).mockImplementation(async () => ({ ...session([...today]), section: "gym" }));
    vi.mocked(api.startWorkout).mockResolvedValue({ ...session([]), section: "gym" });
    vi.mocked(api.logSet).mockImplementation(async (_w, body) => {
      const s = mk(200 + today.length, body.reps ?? 0, { weight_kg: body.weight_kg ?? 0, rpe: body.rpe ?? null, performed_at: "2026-10-20T07:00:00" });
      today.push(s);
      return { set: s, xp_awarded: 10, previous_best_e1rm: null };
    });
    renderPage();
    await userEvent.click(await screen.findByText("Barbell Bench Press"));
    // Ghost values: every set of last time, in grey, next to today's column.
    const grid = await screen.findByRole("table", { name: "Sets: last time and today" });
    await waitFor(() => expect(within(grid).getAllByTestId("ghost").map((c) => c.textContent)).toEqual(
      ["60 kg × 8 @8", "60 kg × 8 @8", "60 kg × 7 @8", "60 kg × 6 @8", "60 kg × 6 @8"],
    ));
    expect(screen.getByText(/Target:/)).toHaveTextContent("Target: 60 kg × 8 @8 (last time");
    const reps = screen.getByRole("spinbutton", { name: "Reps" });
    await waitFor(() => expect(reps).toHaveValue(8));
    reps.focus();
    let keystrokes = 0;
    for (let i = 0; i < 5; i += 1) {
      await userEvent.keyboard("{Enter}");
      keystrokes += 1;
      await waitFor(() => expect(api.logSet).toHaveBeenCalledTimes(i + 1));
      await waitFor(() => expect(screen.getAllByText(/^60 kg × \d @8$/).length).toBeGreaterThan(5 + i));
    }
    expect(keystrokes).toBeLessThanOrEqual(15);
    // Each set repeated last time's set n, in order.
    expect(vi.mocked(api.logSet).mock.calls.map(([, b]) => [b.weight_kg, b.reps])).toEqual([[60, 8], [60, 8], [60, 7], [60, 6], [60, 6]]);
    expect(reps).toHaveFocus();
  });

  it("pre-fills a hold with last time's seconds", async () => {
    const plank = { id: 30, name: "Plank", equipment: "body only", section: "calisthenics", met: null, time_based: false, measure: "hold", muscles: [{ muscle: "abs", weight: 1 }] } as Exercise;
    vi.mocked(api.exercises).mockResolvedValue([plank]);
    vi.mocked(api.previousSession).mockResolvedValue({
      workout_id: 3, day: "2026-10-18", source: "app",
      sets: [{ id: 1, exercise_id: 30, exercise_name: "Plank", weight_kg: 0, reps: 1, rpe: null, duration_s: 50, distance_m: null, avg_hr: null, e1rm: null, is_pr: false, performed_at: "2026-10-18T07:00:00", measure: "hold" }],
    });
    renderPage();
    await userEvent.click(await screen.findByText("Plank"));
    await waitFor(() => expect(screen.getByRole("spinbutton", { name: "Hold (seconds)" })).toHaveValue(50));
    expect(screen.getByTestId("ghost")).toHaveTextContent("50 s");
  });
});
