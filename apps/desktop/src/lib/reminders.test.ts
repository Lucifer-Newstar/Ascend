import type { GameSummary } from "@ascend/shared";
import { describe, expect, it } from "vitest";

import { MAX_PER_DAY, pendingReminders, quietLine, reminderMood, toNotify } from "./reminders";

const game = (over: Partial<GameSummary["streak"]> = {}, quest: Partial<GameSummary["quest"][number]>[] = []) =>
  ({
    xp: { rank: "D" },
    streak: { current: 5, best: 9, excused: 0, active_today: false, reason_due: null, ...over },
    quest,
  }) as unknown as GameSummary;

const at = (h: number) => new Date(2026, 9, 23, h, 0, 0);

const memStore = () => {
  const mem = new Map<string, string>();
  return { getItem: (k: string) => mem.get(k) ?? null, setItem: (k: string, v: string) => void mem.set(k, v) };
};

describe("trainer reminders", () => {
  it("lists what is pending in order and never more than two", () => {
    const items = pendingReminders({
      game: game({ reason_due: "2026-10-22" }), nextSession: "Push A", checkedIn: false, now: at(9), evening: true,
    });
    expect(items.map((r) => r.key)).toEqual(["reason", "workout"]);
    expect(items[0].text).toContain("Thursday");
    expect(reminderMood(items)).toBe("hyped");
  });

  it("asks for the check-in only in the morning and says nothing once the day is done", () => {
    expect(pendingReminders({ game: game(), nextSession: null, checkedIn: false, now: at(8) }).map((r) => r.key)).toEqual(["checkin"]);
    const done = pendingReminders({ game: game({ active_today: true }), nextSession: "Push A", checkedIn: true, now: at(20), evening: true });
    expect(done).toEqual([]);
    expect(reminderMood(done)).toBe("proud");
  });

  it("adds the evening check only when it is turned on", () => {
    const off = pendingReminders({ game: game(), nextSession: null, checkedIn: true, now: at(19) });
    expect(off).toEqual([]);
    const on = pendingReminders({ game: game(), nextSession: null, checkedIn: true, now: at(19), evening: true });
    expect(on.map((r) => r.key)).toEqual(["evening"]);
    expect(pendingReminders({ game: game(), nextSession: null, checkedIn: true, now: at(15), evening: true })).toEqual([]);
  });

  it("notifies each kind at most once a day", () => {
    const store = memStore();
    const items = pendingReminders({ game: game(), nextSession: "Push A", checkedIn: true, now: at(19), evening: true });
    expect(toNotify(items, "2026-10-23", store).map((r) => r.key)).toEqual(["workout", "evening"]);
    expect(toNotify(items, "2026-10-23", store)).toEqual([]);
    expect(toNotify(items, "2026-10-24", store)).toHaveLength(2);
  });

  it("says the day is done only when today's quest is done", () => {
    const open = [{ code: "train_3", completed_at: null }, { code: "protein", completed_at: "2026-10-23T10:00:00" }];
    expect(quietLine(game({ active_today: true }, open))).toBe("Today already counts for your streak. 1 quest item still open for extra XP.");
    expect(quietLine(game({}, [...open, { code: "steps", completed_at: null }]))).toBe("Nothing urgent. 2 quest items are open for when you're ready.");
    expect(quietLine(game({ active_today: true }, [{ code: "train_3", completed_at: "2026-10-23T10:00:00" }]))).toMatch(/^Everything for today is done/);
  });
});

/** R6 in docs/RULES_AND_BASELINE.md: reminders are kind, rare and quiet on rest days. */
describe("rules: reminders (R6)", () => {
  const every = () => {
    const out = [];
    for (const h of [7, 9, 13, 18, 21, 23]) {
      for (const over of [{}, { reason_due: "2026-10-22" }, { current: 30 }, { current: 0 }]) {
        out.push(...pendingReminders({ game: game(over, [{ code: "water_8", progress: 1, target: 8, completed_at: null }]), nextSession: "Push A", checkedIn: false, now: at(h), evening: true }));
      }
    }
    return out;
  };

  it("never frames a reminder as losing something", () => {
    const loss = /\b(lose|lost|losing|ends|end at|break|broken|reset|gone|miss out|at risk|midnight|keep it)\b/i;
    for (const r of every()) expect(r.text).not.toMatch(loss);
  });

  it("has no water reminder and nothing urgent", () => {
    for (const r of every()) {
      expect(r.key).not.toBe("water");
      expect(r.urgent).toBe(false);
    }
  });

  it("says nothing on a planned rest day", () => {
    for (const h of [8, 19, 22]) {
      expect(pendingReminders({ game: game({ rest_today: true, reason_due: "2026-10-22" }), nextSession: "Push A", checkedIn: false, now: at(h), evening: true })).toEqual([]);
    }
  });

  it("caps the day at two, on Today and as notifications", () => {
    expect(MAX_PER_DAY).toBe(2);
    const store = memStore();
    let sent = 0;
    for (const h of [7, 9, 13, 18, 21]) {
      const items = pendingReminders({ game: game({ reason_due: "2026-10-22" }), nextSession: "Push A", checkedIn: false, now: at(h), evening: true });
      expect(items.length).toBeLessThanOrEqual(MAX_PER_DAY);
      sent += toNotify(items, "2026-10-23", store).length;
    }
    expect(sent).toBe(MAX_PER_DAY);
  });
});
