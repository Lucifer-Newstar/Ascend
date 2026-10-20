import type { GameSummary } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { XpChip } from "./XpChip";

vi.mock("../api/client", () => ({ api: { game: vi.fn(), updateSettings: vi.fn() } }));

const summary = (total: number, level: number, into: number): GameSummary => ({
  xp: { total, today: 0, level, xp_into_level: into, xp_for_next: 500, rank: "E", rank_title: "Novice", daily_cap: 600, formula_version: "xp-v1" },
  streak: { current: 2, best: 2, freezes_held: 0, freezes_used: 0, active_today: true },
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
    expect(screen.getByTestId("confetti")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("You reached level 2");
  });

  it("keeps the announcement but drops the confetti with reduced motion", async () => {
    vi.mocked(api.game).mockResolvedValueOnce(summary(490, 1, 490)).mockResolvedValueOnce(summary(530, 2, 30));
    const { rerender } = render(renderChip(0, true));
    await screen.findByText("LV 1");
    rerender(renderChip(1, true));
    await screen.findByText("LV 2");
    expect(screen.queryByTestId("confetti")).toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent("You reached level 2");
  });
});
