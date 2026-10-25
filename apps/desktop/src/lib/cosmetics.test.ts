import { describe, expect, it } from "vitest";

import { CATALOG, bestPeriod, cosmeticArt, cosmeticFilter, isUnlocked, unlockProgress, unlockText, type Progress } from "./cosmetics";

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

describe("clears and catch-up paths (v1.4)", () => {
  const wins = (weeks: string[], bosses?: string[]): Progress => ({ ...base, bossesBeaten: bosses ?? weeks.map(() => "Iron Golem"), bossWeeks: weeks });

  it("gives every time-bound unlock a catch-up total (no item is locked for good)", () => {
    for (const c of CATALOG) {
      const u = c.unlock;
      if (u.kind === "boss" || u.kind === "period" || u.kind === "seasonals") expect(u.orWins, c.id).toBeGreaterThan(0);
    }
  });

  it("opens a seasonal drop by beating its boss or by enough wins in total", () => {
    const wolf = CATALOG.find((c) => c.id === "pet_spirit_wolf")!;
    expect(isUnlocked(wolf, wins([], ["Winter Wraith"]))).toBe(true);
    expect(isUnlocked(wolf, wins(Array(9).fill("2026-03-02")))).toBe(false);
    expect(isUnlocked(wolf, wins(Array(10).fill("2026-03-02")))).toBe(true);
    expect(unlockText(wolf.unlock)).toBe("Beat the seasonal boss of winter (Dec to Feb), or win 10 bosses in total");
  });

  it("counts a monthly clear by calendar month, with a total to catch up", () => {
    const dagger = CATALOG.find((c) => c.id === "weapon_storm_dagger")!;
    const spread = ["2026-09-07", "2026-09-21", "2026-10-05", "2026-10-19"];
    expect(bestPeriod(spread, "month")).toBe(2);
    expect(isUnlocked(dagger, wins(spread))).toBe(false);
    expect(isUnlocked(dagger, wins([...spread, "2026-10-26"]))).toBe(true); // 3 in October
    expect(isUnlocked(dagger, wins(["2026-01-05", "2026-02-02", "2026-03-02", "2026-04-06", "2026-05-04", "2026-06-01", "2026-07-06", "2026-08-03"]))).toBe(true); // 8 in total
    expect(unlockProgress(dagger.unlock, wins(spread))).toBe("best month: 2 of 3 · total 4 of 8");
  });

  it("counts different seasonal bosses for the seasonal clears", () => {
    const ring = CATALOG.find((c) => c.id === "relic_season_ring")!;
    expect(isUnlocked(ring, wins([], ["Harvest Colossus", "Harvest Colossus"]))).toBe(false);
    expect(isUnlocked(ring, wins([], ["Harvest Colossus", "Winter Wraith"]))).toBe(true);
  });

  it("draws the new items as recolours of existing art", () => {
    for (const c of CATALOG.filter((x) => x.base)) {
      expect(cosmeticArt(c.id, "female"), c.id).toBe(cosmeticArt(c.base!, "female"));
      expect(cosmeticFilter(c.id)).toMatch(/^hue-rotate\(\d+deg\)/);
    }
    expect(cosmeticFilter("pet_tiger_cub")).toBe("");
  });
});

describe("no spoilers (design rule D6)", () => {
  it("never names a seasonal boss in an unlock rule", () => {
    for (const c of CATALOG) for (const b of ["Winter Wraith", "Shadow Sovereign", "Monsoon Serpent", "Harvest Colossus"]) expect(unlockText(c.unlock)).not.toContain(b);
  });
});
