/**
 * The trainer's reminders (v1.2): what is still pending today, in priority order. Pure,
 * so Today's trainer bubble and the desktop notifications say the same thing.
 *
 * - a missed day's reason (yesterday was missed and the streak waits for it)
 * - streak at risk (a running streak, nothing logged today, from 6 pm)
 * - today's workout (a program is followed and nothing is logged yet today)
 * - water (today's quest has a water item that is not done)
 * - check-in (before noon, no morning check-in yet)
 */
import type { GameSummary } from "@ascend/shared";

import type { Page } from "../components/Layout";

export type ReminderKey = "reason" | "streak" | "workout" | "water" | "checkin";

export interface Reminder {
  key: ReminderKey;
  text: string;
  /** Where the action is. */
  page: Page;
  action: string;
  urgent: boolean;
}

export interface ReminderInput {
  game: GameSummary | null | undefined;
  /** The program's next session name, or null with no program. */
  nextSession: string | null | undefined;
  /** Whether this morning's check-in is done (undefined while unknown). */
  checkedIn: boolean | undefined;
  now: Date;
}

const dayName = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { weekday: "long" });

export function pendingReminders({ game, nextSession, checkedIn, now }: ReminderInput): Reminder[] {
  if (!game) return [];
  const out: Reminder[] = [];
  const s = game.streak;
  const hour = now.getHours();
  if (s.reason_due) {
    out.push({ key: "reason", text: `You missed ${dayName(s.reason_due)}. Tell me why today and your streak stays.`, page: "dashboard", action: "Give a reason", urgent: true });
  }
  if (s.current > 0 && !s.active_today && hour >= 18) {
    out.push({ key: "streak", text: `Your ${s.current}-day streak ends at midnight. Log anything to keep it.`, page: "workout", action: "Log something", urgent: true });
  }
  if (nextSession && !s.active_today) {
    out.push({ key: "workout", text: `Today's workout is waiting: ${nextSession}.`, page: "workout", action: "Start workout", urgent: false });
  }
  const water = game.quest.find((q) => q.code.startsWith("water") && !q.completed_at);
  if (water) {
    out.push({ key: "water", text: `Water: ${water.progress} of ${water.target} glasses so far.`, page: "dashboard", action: "Open quests", urgent: false });
  }
  if (checkedIn === false && hour < 12) {
    out.push({ key: "checkin", text: "Morning check-in: 20 seconds, and I tune today's plan to how you feel.", page: "dashboard", action: "Check in", urgent: false });
  }
  return out;
}

/** The trainer's mood for the bubble: a warning when something is at stake, else hyped, else proud. */
export function reminderMood(items: Reminder[]): "warning" | "hyped" | "proud" {
  if (items.some((r) => r.urgent)) return "warning";
  return items.length ? "hyped" : "proud";
}

const SENT_KEY = "ascend.reminders.sent";

/**
 * Which reminders still need a desktop notification today: each kind at most once a day.
 * `store` is localStorage in the app (injected for tests).
 */
export function toNotify(items: Reminder[], today: string, store: Pick<Storage, "getItem" | "setItem">): Reminder[] {
  let sent: Record<string, string> = {};
  try {
    sent = JSON.parse(store.getItem(SENT_KEY) ?? "{}") as Record<string, string>;
  } catch {
    sent = {};
  }
  const fresh = items.filter((r) => sent[r.key] !== today);
  if (fresh.length) {
    for (const r of fresh) sent[r.key] = today;
    store.setItem(SENT_KEY, JSON.stringify(sent));
  }
  return fresh;
}
