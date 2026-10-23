/**
 * The big trainer on Today (v1.2): your trainer shown large, in the mood of the moment,
 * with what is still pending today (the same reminders as the desktop notifications)
 * and a button to talk. In plain mode (trainer off) the same list shows without the
 * character, and only when something is pending.
 */
import type { GameSummary } from "@ascend/shared";

import { api } from "../api/client";
import { pendingReminders, quietLine, reminderMood, type Reminder } from "../lib/reminders";
import { useApi } from "../lib/useApi";
import type { Page } from "./Layout";
import { TrainerPortrait, useTrainer, useTrainerOn } from "./Trainer";

const SCROLL_TO: Partial<Record<Reminder["key"], string>> = { reason: "reason-title", water: "quest-window", checkin: "checkin-title" };

export function greeting(now: Date, name: string | null | undefined): string {
  const h = now.getHours();
  const part = h < 12 ? "Morning" : h < 17 ? "Afternoon" : "Evening";
  return name ? `${part}, ${name}.` : `${part}, Hunter.`;
}

export function TrainerHero({ game, name, refreshKey = 0, onNavigate, onOpenChat, now = () => new Date() }: {
  game: GameSummary;
  name?: string | null;
  refreshKey?: number;
  onNavigate?: (p: Page) => void;
  onOpenChat?: () => void;
  now?: () => Date;
}) {
  const trainerOn = useTrainerOn();
  const t = useTrainer();
  const plan = useApi(api.currentPlan, [refreshKey], { cacheKey: "plan" });
  const checkin = useApi(api.checkinToday, [refreshKey]);
  const at = now();
  const items = pendingReminders({
    game,
    nextSession: plan.data?.next.name ?? null,
    checkedIn: checkin.loading ? undefined : Boolean(checkin.data),
    now: at,
  });
  if (!trainerOn && items.length === 0) return null;

  const act = (r: Reminder) => {
    const id = SCROLL_TO[r.key];
    const el = id ? document.getElementById(id) ?? document.querySelector(`[data-testid="${id}"]`) : null;
    if (r.page === "dashboard" && el) el.scrollIntoView?.({ behavior: "smooth", block: "center" });
    else onNavigate?.(r.page);
  };

  const list = (
    <ul className="mt-2 space-y-1.5" aria-label="Pending today">
      {items.map((r) => (
        <li key={r.key} className="flex flex-wrap items-center justify-between gap-2 text-sm" data-testid={`reminder-${r.key}`}>
          <span className={r.urgent ? "text-warn" : "text-ink"}>{r.text}</span>
          <button type="button" className="text-xs font-medium text-accent hover:underline" onClick={() => act(r)}>{r.action}</button>
        </li>
      ))}
    </ul>
  );

  if (!trainerOn) {
    return (
      <section className="card p-5" aria-labelledby="pending-title" data-testid="trainer-hero">
        <h2 id="pending-title" className="card-title">Pending today</h2>
        {list}
      </section>
    );
  }
  return (
    <section className="card trainer-hero relative overflow-hidden p-5" aria-label={`${t.name}, your trainer`} data-testid="trainer-hero">
      <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-end">
        <TrainerPortrait mood={reminderMood(items)} size={168} className="trainer-big" />
        <div className="trainer-bubble relative min-w-0 flex-1 rounded-xl border border-line-2 bg-panel-2/80 px-4 py-3">
          <p className="font-display text-[11px] font-bold uppercase tracking-[0.18em] text-accent">{t.name}</p>
          <p className="text-h3 text-ink">{greeting(at, name)}</p>
          {items.length ? list : <p className="mt-1 text-sm text-muted" data-testid="trainer-quiet">{quietLine(game)}</p>}
          {onOpenChat && (
            <button type="button" className="btn-ghost mt-3 text-xs" onClick={onOpenChat}>Ask {t.short} (Ctrl+K)</button>
          )}
        </div>
      </div>
    </section>
  );
}
