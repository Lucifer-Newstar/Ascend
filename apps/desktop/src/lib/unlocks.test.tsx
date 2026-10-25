import type { GameSummary } from "@ascend/shared";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { currentUnlocks, useUnlockWatcher } from "./unlocks";

vi.mock("../api/client", () => ({
  api: { game: vi.fn(), prs: vi.fn(), titles: vi.fn(), skillUnlocks: vi.fn(), syncUnlocks: vi.fn() },
}));

const game = { xp: { level: 9, rank: "D", rank_title: "Hunter" }, streak: { current: 2, best: 5, lifetime_sessions: 12 } } as unknown as GameSummary;
const titles = [
  { title: "Golem Breaker", boss: "Iron Golem", week_start: "2026-10-12", earned_at: "2026-10-16T19:00:00" },
  { title: "Golem Breaker", boss: "Iron Golem", week_start: "2026-10-19", earned_at: "2026-10-23T19:00:00" },
];
const skill = { id: 1, skill_key: "muscle_up", skill_name: "Muscle-up", step_key: "c2b", step_name: "Chest-to-bar pull-up",
  unlocked_at: "2026-10-20T18:00:00", xp: 80, final: false, next_step_name: null, source: "log" };

describe("unlock watcher (v1.4)", () => {
  it("lists ranks reached, bosses beaten once each, skill steps and earned cosmetics", () => {
    const keys = currentUnlocks({ game, prs: 0, titles, skills: [skill as never] }).map((u) => u.key);
    expect(keys).toContain("rank:D");
    expect(keys).not.toContain("rank:E"); // the starting rank is not an unlock
    expect(keys.filter((k) => k === "boss:Iron Golem")).toHaveLength(1);
    expect(keys).toContain("skill:muscle_up.c2b");
    expect(keys).toContain("cosmetic:outfit_ronin"); // 10 sessions
    expect(keys).toContain("cosmetic:weapon_shadow_dagger"); // a boss win
    expect(keys).not.toContain("cosmetic:outfit_cyber_hunter"); // starter items are not unlocks
    for (const k of keys) expect(k).toMatch(/^[a-z]+:[A-Za-z0-9_\- .']+$/); // the sidecar's key rule
  });

  it("reports unlocks and plays only the new non-skill ones", async () => {
    vi.mocked(api.game).mockResolvedValue(game);
    vi.mocked(api.prs).mockResolvedValue([]);
    vi.mocked(api.titles).mockResolvedValue(titles);
    vi.mocked(api.skillUnlocks).mockResolvedValue([skill as never]);
    vi.mocked(api.syncUnlocks).mockResolvedValue({
      new: [
        { key: "rank:D", kind: "rank", title: "Rank D", detail: "", at: "2026-10-25T18:00:00", seeded: false },
        { key: "skill:muscle_up.c2b", kind: "skill", title: "Chest-to-bar pull-up", detail: "", at: "2026-10-25T18:00:00", seeded: false },
      ],
      total: 6,
    });
    const { result } = renderHook(() => useUnlockWatcher(0));
    await waitFor(() => expect(result.current.playing.map((u) => u.key)).toEqual(["rank:D"]));
    expect(api.syncUnlocks).toHaveBeenCalledTimes(1);
  });
});
