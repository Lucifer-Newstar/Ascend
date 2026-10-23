import type { GameSummary, Settings } from "@ascend/shared";
import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { LOCK_LEAVE_MS, LockScreen } from "./LockScreen";

const game = { xp: { level: 72, rank: "S", rank_title: "Monarch" } } as unknown as GameSummary;
const at = () => new Date(2026, 9, 23, 7, 5);

function renderLock(onEnter = vi.fn(), settings: Partial<Settings> = {}) {
  render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, theme: "shadow", reduce_motion: false, avatar: "female", ...settings } as Settings} save={vi.fn()}>
      <LockScreen game={game} onEnter={onEnter} now={at} />
    </PrefsProvider>,
  );
  return onEnter;
}

describe("LockScreen", () => {
  beforeEach(() => {
    vi.spyOn(api, "profile").mockResolvedValue({ name: "Navin" } as never);
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
});
