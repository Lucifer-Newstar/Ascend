import type { BossRaid } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { BossRaidCard, bossLine } from "./BossRaid";

const boss: BossRaid = {
  week_start: "2026-10-19", week_end: "2026-10-25", name: "Iron Golem", title: "Golem Breaker", hp: 40, damage: 25, hp_left: 15,
  days_left: 3, defeated: false, defeated_at: null, bonus_xp: 150, hp_source: "history", hp_note: "median of your last 4 weeks (38, 41, 40, 44 sets)",
  titles_earned: 2, algo_version: "boss-v1", why: { formula: "HP = a week of your training", inputs: { hp: 40 } },
};

function renderCard(b: BossRaid, trainer = true) {
  return render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, trainer }} save={vi.fn()}>
      <BossRaidCard boss={b} />
    </PrefsProvider>,
  );
}

describe("BossRaidCard", () => {
  it("shows HP, damage, the reward before it is earned, and Why", async () => {
    const { container } = renderCard(boss);
    expect(screen.getByRole("heading", { name: "Iron Golem" })).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Iron Golem HP" })).toHaveAttribute("aria-valuenow", "15");
    expect(screen.getByText("+150 XP")).toBeInTheDocument();
    expect(screen.getByText("Title: Golem Breaker")).toBeInTheDocument();
    expect(screen.getByText("3 days left")).toBeInTheDocument();
    expect(screen.getByText(/15 more sets by Sunday/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Why?" }));
    expect(screen.getByText(/median of your last 4 weeks/)).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });

  it("celebrates a defeat and has no trainer line in plain mode", () => {
    renderCard({ ...boss, defeated: true, hp_left: 0, damage: 40, defeated_at: "2026-10-23T18:00:00" }, false);
    expect(screen.getByText("Defeated")).toBeInTheDocument();
    expect(screen.queryByTestId("trainer-says")).toBeNull();
    expect(bossLine({ ...boss, defeated: true })).toContain('"Golem Breaker"');
    expect(bossLine({ ...boss, damage: 0, hp_left: 40 })).toContain("A new boss rises");
  });
});
