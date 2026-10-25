/**
 * The trainer's reminders: what is still pending today, in priority order. Pure, so
 * Today's trainer bubble and the desktop notifications say the same thing.
 *
 * v1.3 (review 1.4, design rules D2/D3 in docs/RULES_AND_BASELINE.md): kind, never about
 * losing something, nothing on a planned rest day, no water nagging, at most two a day.
 *
 * - a missed day's reason (yesterday was missed; a reason keeps it as a rest day)
 * - today's workout (a program is followed and nothing is logged yet today)
 * - evening check, opt-in (Settings > Trainer), from 6 pm on a training day
 * - check-in (before noon, no morning check-in yet)
 */
import type { GameSummary } from "@ascend/shared";

import type { Page } from "../components/Layout";

export type ReminderKey = "reason" | "workout" | "evening" | "checkin";

/** Never more than this many reminders in a day, on Today or as notifications. */
export const MAX_PER_DAY = 2;

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
  /** Settings > Trainer > Evening check (off by default). */
  evening?: boolean;
}

const dayName = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { weekday: "long" });

export function pendingReminders({ game, nextSession, checkedIn, now, evening = false }: ReminderInput): Reminder[] {
  if (!game) return [];
  const s = game.streak;
  // A planned rest day is part of the plan: nothing to remind about.
  if (s.rest_today) return [];
  const out: Reminder[] = [];
  const hour = now.getHours();
  if (s.reason_due) {
    out.push({ key: "reason", text: `How did ${dayName(s.reason_due)} go? If something came up, tell me and I'll count it as rest.`, page: "dashboard", action: "Add a note", urgent: false });
  }
  if (nextSession && !s.active_today) {
    out.push({ key: "workout", text: `Today's workout is ready when you are: ${nextSession}.`, page: "workout", action: "Start workout", urgent: false });
  }
  if (evening && !s.active_today && hour >= 18) {
    out.push({ key: "evening", text: "Still time for a short session if you feel like it. Ten minutes counts.", page: "workout", action: "Start something short", urgent: false });
  }
  if (checkedIn === false && hour < 12) {
    out.push({ key: "checkin", text: "Morning check-in: 20 seconds, and I tune today's plan to how you feel.", page: "dashboard", action: "Check in", urgent: false });
  }
  return out.slice(0, MAX_PER_DAY);
}

/**
 * What the trainer says when nothing is pending. "Everything is done" only when today's
 * quest really is done (QA: it said so beside a 0/3 training quest).
 */
export function quietLine(game: GameSummary | null | undefined): string {
  const left = game ? game.quest.filter((q) => !q.completed_at).length : 0;
  if (left === 0) return "Everything for today is done. Rest well; I'll have tomorrow ready.";
  const items = `${left} quest item${left === 1 ? "" : "s"}`;
  // active_today means anything was logged (a weigh-in counts), not that you trained.
  if (game?.streak.active_today) return `Today already counts for your streak. ${items} still open for extra XP.`;
  return `Nothing urgent. ${items} ${left === 1 ? "is" : "are"} open for when you're ready.`;
}

/** The trainer's mood for the bubble: hyped when something is waiting, else proud (no warning faces for reminders). */
export function reminderMood(items: Reminder[]): "warning" | "hyped" | "proud" {
  if (items.some((r) => r.urgent)) return "warning";
  return items.length ? "hyped" : "proud";
}

const SENT_KEY = "ascend.reminders.sent";

/**
 * Which reminders still need a desktop notification today: each kind at most once a day,
 * and never more than MAX_PER_DAY in total. `store` is localStorage in the app (injected
 * for tests).
 */
export function toNotify(items: Reminder[], today: string, store: Pick<Storage, "getItem" | "setItem">): Reminder[] {
  let sent: Record<string, string> = {};
  try {
    sent = JSON.parse(store.getItem(SENT_KEY) ?? "{}") as Record<string, string>;
  } catch {
    sent = {};
  }
  const already = Object.values(sent).filter((d) => d === today).length;
  const fresh = items.filter((r) => sent[r.key] !== today).slice(0, Math.max(0, MAX_PER_DAY - already));
  if (fresh.length) {
    for (const r of fresh) sent[r.key] = today;
    store.setItem(SENT_KEY, JSON.stringify(sent));
  }
  return fresh;
}
