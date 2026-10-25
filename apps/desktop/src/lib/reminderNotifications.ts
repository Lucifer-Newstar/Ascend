/**
 * Desktop notifications for the trainer's reminders (v1.2). While the app is open it looks
 * again every 30 minutes; each kind of reminder notifies at most once a day, and only when
 * Reminders are on (Settings). Clicking a notification brings the app forward on the page
 * where the action is.
 *
 * v1.4: with the tray on, this keeps running while the window is closed, and the workout
 * reminder waits for the usual training time.
 */
import type { GameSummary } from "@ascend/shared";
import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { Page } from "../components/Layout";
import { pendingReminders, toNotify } from "./reminders";
import { useApi } from "./useApi";

const EVERY_MS = 30 * 60 * 1000;

export function localDay(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function useReminderNotifications({ game, enabled, evening = false, trainerName, refreshKey, onNavigate }: {
  game: GameSummary | null | undefined;
  enabled: boolean;
  /** Settings > Trainer > Evening check (off by default). */
  evening?: boolean;
  trainerName: string;
  refreshKey: number;
  onNavigate: (p: Page) => void;
}) {
  const [tick, setTick] = useState(0);
  const plan = useApi(api.currentPlan, [refreshKey, tick], { cacheKey: "plan" });
  const checkin = useApi(api.checkinToday, [refreshKey, tick]);
  // v1.4: the usual training time decides when today's workout reminder arrives.
  const schedule = useApi(api.schedule, [refreshKey]);
  useEffect(() => {
    const id = window.setInterval(() => setTick((n) => n + 1), EVERY_MS);
    return () => window.clearInterval(id);
  }, []);
  useEffect(() => {
    if (!enabled || !game || plan.loading || checkin.loading || typeof window === "undefined" || !("Notification" in window)) return;
    const now = new Date();
    const items = pendingReminders({ game, nextSession: plan.data?.next.name ?? null, checkedIn: Boolean(checkin.data), now, evening, plannedTime: schedule.data?.time ?? null });
    if (items.length === 0) return;
    const send = () => {
      for (const r of toNotify(items, localDay(now), window.localStorage)) {
        const n = new Notification(trainerName, { body: r.text, tag: `ascend-${r.key}` });
        n.onclick = () => {
          window.focus();
          onNavigate(r.page);
        };
      }
    };
    if (Notification.permission === "granted") send();
    else if (Notification.permission === "default") void Notification.requestPermission().then((p) => { if (p === "granted") send(); });
  }, [enabled, evening, game, plan.loading, plan.data, checkin.loading, checkin.data, schedule.data, trainerName, onNavigate, tick]);
}
