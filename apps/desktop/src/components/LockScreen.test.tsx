import type { GameSummary, Settings } from "@ascend/shared";
import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { clearApiCache } from "../lib/useApi";
import { readShort } from "../lib/shortSession";
import { LOCK_LEAVE_MS, LockScreen, todayDoor } from "./LockScreen";

const game = { xp: { level: 72, rank: "S", rank_title: "Monarch" } } as unknown as GameSummary;
const at = () => new Date(2026, 9, 23, 7, 5);

function renderLock(onEnter = vi.fn(), settings: Partial<Settings> = {}, onStart?: () => void, g: GameSummary = game) {
  render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, theme: "shadow", reduce_motion: false, avatar: "female", ...settings } as Settings} save={vi.fn()}>
      <LockScreen game={g} onEnter={onEnter} onStart={onStart} now={at} />
    </PrefsProvider>,
  );
  return onEnter;
}

describe("LockScreen", () => {
  beforeEach(() => {
    clearApiCache();
    window.sessionStorage.clear();
    vi.spyOn(api, "profile").mockResolvedValue({ name: "Navin" } as never);
    vi.spyOn(api, "currentPlan").mockResolvedValue(null);
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("shows the hunter tile with name, level and rank, focused, plus the time", async () => {
    renderLock();
    expect(await screen.findByTestId("lock-name")).toHaveTextContent("Navin");
    expect(screen.getByTestId("lock-rank")).toHaveTextContent("Level 72 · Rank S");
    expect(screen.getByTestId("lock-tile")).toHaveFocus();
    expect(screen.getByTestId("lock-tile")).toHaveAccessibleName("Enter ASCEND as Navin, level 72, rank S");
    expect(screen.getByTestId("lock-clock")).toHaveTextContent("07:05");
    expect(screen.getByTestId("avatar")).toHaveAttribute("data-rank", "S");
  });

  it("goes in on a click after the zoom-and-fade, once", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const onEnter = renderLock();
    fireEvent.click(screen.getByTestId("lock-tile"));
    expect(screen.getByTestId("lock-screen").className).toContain("lock-leaving");
    expect(onEnter).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("lock-tile"));
    act(() => { vi.advanceTimersByTime(LOCK_LEAVE_MS + 10); });
    expect(onEnter).toHaveBeenCalledTimes(1);
  });

  it("goes in with Enter, straight away when motion is reduced", async () => {
    const onEnter = renderLock(vi.fn(), { reduce_motion: true });
    await userEvent.keyboard("{Enter}");
    expect(onEnter).toHaveBeenCalledTimes(1);
  });

  it("has no axe violations", async () => {
    renderLock();
    await screen.findByText("Navin");
    await expectNoAxeViolations(document.body);
  });

  describe("the workout door (v1.4)", () => {
    const plan = (last: string | null = null) => ({
      name: "Starter", last_trained: last,
      next: { key: "a", name: "Push A", items: [{ exercise_id: 1 }, { exercise_id: 2 }, { exercise_id: 3 }] },
    }) as never;

    it("says what today is", () => {
      const rest = { ...game, streak: { rest_today: true } } as unknown as GameSummary;
      expect(todayDoor(rest, plan(), "2026-10-23")).toEqual({ kind: "rest" });
      expect(todayDoor(game, null, "2026-10-23")).toEqual({ kind: "none" });
      expect(todayDoor(game, plan("2026-10-23"), "2026-10-23")).toEqual({ kind: "done", name: "Push A" });
      expect(todayDoor(game, plan("2026-10-22"), "2026-10-23")).toEqual({ kind: "session", name: "Push A", moves: 3 });
    });

    it("starts today's session with Enter on a training day", async () => {
      vi.mocked(api.currentPlan).mockResolvedValue(plan());
      const onEnter = vi.fn();
      const onStart = vi.fn();
      renderLock(onEnter, { reduce_motion: true }, onStart);
      expect(await screen.findByText("Push A")).toBeInTheDocument();
      expect(screen.getByTestId("lock-door")).toHaveTextContent("Today: Push A · 3 moves");
      expect(screen.getByTestId("lock-start")).toHaveFocus();
      await userEvent.keyboard("{Enter}");
      expect(onStart).toHaveBeenCalledTimes(1);
      expect(onEnter).not.toHaveBeenCalled();
    });

    it("opens the 10-minute version", async () => {
      vi.mocked(api.currentPlan).mockResolvedValue(plan());
      vi.spyOn(api, "shortSession").mockResolvedValue({ session: "Push A", minutes: 9, items: [], note: "", algo_version: "schedule-v1" });
      const onStart = vi.fn();
      renderLock(vi.fn(), { reduce_motion: true }, onStart);
      await userEvent.click(await screen.findByTestId("lock-short"));
      expect(onStart).toHaveBeenCalledTimes(1);
      expect(readShort(at())?.minutes).toBe(9);
    });

    it("on a rest day says so and Enter just goes in", async () => {
      const rest = { ...game, streak: { rest_today: true } } as unknown as GameSummary;
      vi.mocked(api.currentPlan).mockResolvedValue(plan());
      const onEnter = vi.fn();
      const onStart = vi.fn();
      renderLock(onEnter, { reduce_motion: true }, onStart, rest);
      expect(await screen.findByText(/Rest day ✓/)).toBeInTheDocument();
      expect(screen.queryByTestId("lock-start")).toBeNull();
      await userEvent.keyboard("{Enter}");
      expect(onEnter).toHaveBeenCalledTimes(1);
      expect(onStart).not.toHaveBeenCalled();
    });

    it("has no axe violations with the door showing", async () => {
      vi.mocked(api.currentPlan).mockResolvedValue(plan());
      renderLock(vi.fn(), {}, vi.fn());
      await screen.findByTestId("lock-start");
      await expectNoAxeViolations(document.body);
    });
  });
});
