import type { GameSummary } from "@ascend/shared";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { segmentFills, XpChip } from "./XpChip";

vi.mock("../api/client", () => ({ api: { game: vi.fn(), updateSettings: vi.fn() } }));

const summary = (total: number, level: number, into: number): GameSummary => ({
  xp: { total, today: 0, level, xp_into_level: into, xp_for_next: 500, rank: "E", rank_title: "Novice", daily_cap: 600, formula_version: "xp-v1" },
  streak: { current: 2, best: 2, excused: 0, reason_due: null, active_today: true },
  calm: { current: 0, best: 0, active_today: false },
  quest: [],
});

function renderChip(key: number, reduce = false) {
  return (
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, reduce_motion: reduce }} save={vi.fn()}>
      <XpChip refreshKey={key} />
    </PrefsProvider>
  );
}

describe("XpChip", () => {
  beforeEach(() => vi.mocked(api.game).mockReset());

  it("floats the XP gained after a refresh, without a celebration inside a level", async () => {
    vi.mocked(api.game).mockResolvedValueOnce(summary(100, 1, 100)).mockResolvedValueOnce(summary(112, 1, 112));
    const { rerender } = render(renderChip(0));
    expect(await screen.findByText("LV 1")).toBeInTheDocument();
    expect(screen.queryByTestId("xp-gain")).toBeNull();
    rerender(renderChip(1));
    expect(await screen.findByTestId("xp-gain")).toHaveTextContent("+12 XP");
    expect(screen.queryByTestId("confetti")).toBeNull();
  });

  it("bursts confetti and announces a level-up", async () => {
    vi.mocked(api.game).mockResolvedValueOnce(summary(490, 1, 490)).mockResolvedValueOnce(summary(530, 2, 30));
    const { rerender } = render(renderChip(0));
    await screen.findByText("LV 1");
    rerender(renderChip(1));
    expect(await screen.findByText("LV 2")).toBeInTheDocument();
    expect(await screen.findByTestId("confetti")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("You reached level 2");
  });

  it("starts a new level's count from zero instead of counting down from the old level", async () => {
    vi.mocked(api.game).mockResolvedValueOnce(summary(490, 1, 490)).mockResolvedValueOnce(summary(530, 2, 30));
    vi.useFakeTimers({ toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance"] });
    // Only animation frames and the clock are fake; React runs effects on its own real
    // schedule. Each waitFor poll advances one frame and checks again, so the test does
    // not depend on whether the count-up effect has started by the time it advances (it
    // failed under load when it advanced 1000 ms once, before the effect existed).
    const frame = () => act(() => { vi.advanceTimersByTime(16); });
    const shown = () => Number(screen.getByTestId("count-up").textContent);
    try {
      const { rerender } = render(renderChip(0));
      await screen.findByText("LV 1");
      await waitFor(() => { frame(); expect(shown()).toBe(490); });
      rerender(renderChip(1));
      await screen.findByText("LV 2");
      // Mid-animation the number is on its way up from 0, not down from 490 (which would
      // only ever show values above 30).
      await waitFor(() => { frame(); expect(shown()).toBeGreaterThan(0); expect(shown()).toBeLessThan(30); });
      await waitFor(() => { frame(); expect(shown()).toBe(30); });
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps the announcement but drops the confetti with reduced motion", async () => {
    vi.mocked(api.game).mockResolvedValueOnce(summary(490, 1, 490)).mockResolvedValueOnce(summary(530, 2, 30));
    const { rerender } = render(renderChip(0, true));
    await screen.findByText("LV 1");
    rerender(renderChip(1, true));
    await screen.findByText("LV 2");
    expect(screen.queryByTestId("confetti")).toBeNull();
    // The announcement is rendered together with "LV 2" (useRise derives it while
    // rendering), so no timer or extra wait is involved here.
    expect(screen.getByRole("status")).toHaveTextContent("You reached level 2");
  });

  it("shows the rank badge, a 10-segment XP bar and the streak in the top bar", async () => {
    vi.mocked(api.game).mockResolvedValueOnce(summary(250, 3, 250));
    render(renderChip(0, true));
    expect(await screen.findByRole("img", { name: "Rank E, Novice" })).toHaveTextContent("E");
    const segments = screen.getByTestId("xp-segments").querySelectorAll("[data-fill]");
    expect(segments).toHaveLength(10);
    // 250 of 500 XP: five full segments, five empty.
    expect([...segments].map((s) => s.getAttribute("data-fill"))).toEqual(["1.00", "1.00", "1.00", "1.00", "1.00", "0.00", "0.00", "0.00", "0.00", "0.00"]);
    expect(screen.getByTestId("top-streak")).toHaveAccessibleName("2-day streak, details");
  });

  it("explains the streak rules on click: reasons, and progress is never lost", async () => {
    vi.mocked(api.game).mockResolvedValueOnce({ ...summary(250, 3, 250), streak: { current: 9, best: 12, excused: 1, reason_due: null, active_today: false } });
    render(renderChip(0, true));
    const button = await screen.findByRole("button", { name: /9-day streak, details/ });
    expect(button).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(button);
    const pop = screen.getByRole("dialog", { name: "Streak" });
    expect(pop).toHaveTextContent("Best 12 · today not counted yet");
    expect(pop).toHaveTextContent("1 missed day kept with a reason");
    expect(pop).toHaveTextContent("Two missed days in a row, or no reason, reset it.");
    expect(pop).toHaveTextContent("never removes XP, levels, ranks or unlocked skills");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Streak" })).toBeNull();
  });
});

describe("segmentFills", () => {
  it("splits a fill across 10 segments with a partial last one", () => {
    expect(segmentFills(0.37).map((k) => Math.round(k * 100) / 100)).toEqual([1, 1, 1, 0.7, 0, 0, 0, 0, 0, 0]);
    expect(segmentFills(1.4)).toEqual(Array(10).fill(1));
    expect(segmentFills(-1)).toEqual(Array(10).fill(0));
  });
});
