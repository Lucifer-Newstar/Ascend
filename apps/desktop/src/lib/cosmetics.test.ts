import { describe, expect, it } from "vitest";

import { CATALOG, isUnlocked, unlockText, type Progress } from "./cosmetics";

const base: Progress = { rank: "E", bestStreak: 0, sessions: 0, prs: 0, bossesBeaten: [] };
const item = (id: string) => CATALOG.find((c) => c.id === id)!;

describe("cosmetic unlocks (v1.3: sessions, not daily streaks)", () => {
  it("has no unlock that needs a daily streak", () => {
    for (const c of CATALOG) expect(c.unlock.kind).not.toBe("streak");
  });

  it("opens the Ronin coat at 10 sessions on any days", () => {
    const ronin = item("outfit_ronin");
    expect(unlockText(ronin.unlock)).toBe("Finish 10 training sessions");
    expect(isUnlocked(ronin, { ...base, sessions: 9 })).toBe(false);
    expect(isUnlocked(ronin, { ...base, sessions: 10 })).toBe(true);
  });

  it("keeps what an old best streak already earned", () => {
    expect(isUnlocked(item("outfit_ronin"), { ...base, bestStreak: 7 })).toBe(true);
    expect(isUnlocked(item("relic_focus_charm"), { ...base, bestStreak: 14 })).toBe(true);
    expect(isUnlocked(item("weapon_spear_of_valor"), { ...base, bestStreak: 29, sessions: 49 })).toBe(false);
    expect(isUnlocked(item("weapon_spear_of_valor"), { ...base, sessions: 50 })).toBe(true);
  });
});
