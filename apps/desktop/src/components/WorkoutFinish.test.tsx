import type { BossRaid, FinishedWorkout, GameSummary, WorkoutSet } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { clock, RunThrough, timerCue } from "./RunThrough";
import { finishLine, sessionCounted, WorkoutFinish } from "./WorkoutFinish";

const set = (id: number, name = "Push-up"): WorkoutSet => ({ id, exercise_id: 1, exercise_name: name, weight_kg: 0, reps: 8, rpe: 8 }) as unknown as WorkoutSet;
const result = (sets: number, xp: number, minutes = 12): FinishedWorkout =>
  ({ workout: { id: 1, sets: Array.from({ length: sets }, (_, i) => set(i + 1, i % 2 ? "Squat" : "Push-up")) }, xp_awarded: xp, active_minutes: minutes, hard_sets: sets }) as unknown as FinishedWorkout;
const game = { xp: { level: 4, rank: "E", xp_into_level: 60, xp_for_next: 120, total: 400, today: 40, rank_title: "", daily_cap: 600, formula_version: "x" }, streak: { current: 5, best: 7, freezes_held: 0, freezes_used: 0, active_today: true }, calm: { current: 0, best: 0 }, quest: [] } as unknown as GameSummary;
const boss = { name: "Iron Golem", hp_left: 120, days_left: 3, defeated: false } as unknown as BossRaid;

function wrap(ui: React.ReactNode) {
  return render(<PrefsProvider initial={{ ...DEFAULT_SETTINGS, reduce_motion: true }} save={vi.fn()}>{ui}</PrefsProvider>);
}

describe("workout finish moment", () => {
  it("counts a session from 3 sets or 10 timed minutes", () => {
    expect(sessionCounted(result(2, 0, 4))).toBe(false);
    expect(sessionCounted(result(3, 30, 4))).toBe(true);
    expect(sessionCounted(result(1, 10, 15))).toBe(true);
  });

  it("explains a short session kindly and celebrates a level-up", () => {
    expect(finishLine({ result: result(2, 0, 4) }).text).toMatch(/One more set/);
    expect(finishLine({ result: result(5, 40), game, levelBefore: 3 }).mood).toBe("hyped");
    expect(finishLine({ result: result(5, 40), game, levelBefore: 4 }).mood).toBe("proud");
  });

  it("shows XP, level progress, streak, boss and the 3-set rule", async () => {
    const onClose = vi.fn();
    wrap(<WorkoutFinish summary={{ result: result(2, 0, 4), game, boss }} onClose={onClose} />);
    expect(screen.getByTestId("finish-xp")).toHaveTextContent("+0 XP");
    expect(screen.getByText(/Level 4 · Rank E/)).toBeInTheDocument();
    expect(screen.getByText("5 days")).toBeInTheDocument();
    expect(screen.getByText("Iron Golem")).toBeInTheDocument();
    expect(screen.getByText(/counts once it has 3 sets/)).toBeVisible();
    expect(screen.getByText(/earned no XP, but every set is saved/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(onClose).toHaveBeenCalled();
  });
});

describe("full-screen timer", () => {
  it("formats the clock and picks a cue", () => {
    expect(clock(90)).toBe("1:30");
    expect(clock(5)).toBe("0:05");
    expect(timerCue(40, 1).mood).toBe("neutral");
    expect(timerCue(5, 1).text).toMatch(/Almost/);
    expect(timerCue(0, 2).mood).toBe("proud");
  });

  it("keeps the screen awake while open and lets it sleep on exit", async () => {
    const keepAwake = vi.fn(async (on: boolean) => on);
    (window as unknown as { ascend: unknown }).ascend = { keepAwake };
    const onExit = vi.fn();
    const props = { exercise: { name: "Push-up", image: null, section: "calisthenics" as const, muscles: [] }, target: "BW × 8", setsDone: 1, restTotal: 90, paused: false, onTogglePause: vi.fn(), onSkipRest: vi.fn(), onSetDone: vi.fn(), onExit };
    const view = wrap(<RunThrough {...props} restLeft={75} />);
    expect(screen.getByTestId("run-clock")).toHaveTextContent("1:15");
    await vi.waitFor(() => expect(keepAwake).toHaveBeenCalledWith(true));
    await userEvent.keyboard("{Escape}");
    expect(onExit).toHaveBeenCalled();
    view.unmount();
    expect(keepAwake).toHaveBeenLastCalledWith(false);
    delete (window as unknown as { ascend?: unknown }).ascend;
  });

  it("shows Set done when the rest is over", async () => {
    const onSetDone = vi.fn();
    wrap(<RunThrough exercise={{ name: "Squat", image: null, section: "gym", muscles: [] }} target={null} setsDone={0} restLeft={0} restTotal={90} paused={false} onTogglePause={vi.fn()} onSkipRest={vi.fn()} onSetDone={onSetDone} onExit={vi.fn()} />);
    expect(screen.getByTestId("run-clock")).toHaveTextContent("GO");
    await userEvent.click(screen.getByRole("button", { name: "Set done" }));
    expect(onSetDone).toHaveBeenCalled();
  });
});
