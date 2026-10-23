import type { GameSummary } from "@ascend/shared";
import { describe, expect, it } from "vitest";

import { pendingReminders, reminderMood, toNotify } from "./reminders";

const game = (over: Partial<GameSummary["streak"]> = {}, quest: Partial<GameSummary["quest"][number]>[] = []) =>
  ({
    xp: { rank: "D" },
    streak: { current: 5, best: 9, excused: 0, active_today: false, reason_due: null, ...over },
    quest,
  }) as unknown as GameSummary;

const at = (h: number) => new Date(2026, 9, 23, h, 0, 0);

describe("trainer reminders", () => {
  it("lists what is pending, most urgent first", () => {
    const items = pendingReminders({
      game: game({ reason_due: "2026-10-22" }, [{ code: "water_8", progress: 3, target: 8, completed_at: null }]),
      nextSession: "Push A", checkedIn: false, now: at(19),
    });
    expect(items.map((r) => r.key)).toEqual(["reason", "streak", "workout", "water"]);
    expect(items[0].text).toContain("Thursday");
    expect(items[1].text).toBe("Your 5-day streak ends at midnight. Log anything to keep it.");
    expect(reminderMood(items)).toBe("warning");
  });

  it("asks for the check-in only in the morning and says nothing once the day is done", () => {
    expect(pendingReminders({ game: game(), nextSession: null, checkedIn: false, now: at(8) }).map((r) => r.key)).toEqual(["checkin"]);
    const done = pendingReminders({ game: game({ active_today: true }), nextSession: "Push A", checkedIn: true, now: at(20) });
    expect(done).toEqual([]);
    expect(reminderMood(done)).toBe("proud");
  });

  it("notifies each kind at most once a day", () => {
    const mem = new Map<string, string>();
    const store = { getItem: (k: string) => mem.get(k) ?? null, setItem: (k: string, v: string) => void mem.set(k, v) };
    const items = pendingReminders({ game: game(), nextSession: "Push A", checkedIn: true, now: at(19) });
    expect(toNotify(items, "2026-10-23", store).map((r) => r.key)).toEqual(["streak", "workout"]);
    expect(toNotify(items, "2026-10-23", store)).toEqual([]);
    expect(toNotify(items, "2026-10-24", store)).toHaveLength(2);
  });
});
