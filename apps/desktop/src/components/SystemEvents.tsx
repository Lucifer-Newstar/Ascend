/**
 * System events: the level-up / rank-up and quest-complete notices.
 *
 * Watches the game summary (refreshed whenever something is logged) and, when the level,
 * the rank or the daily quest's completion changes for the better, shows a small,
 * non-modal System window in the top-right corner. Nothing shows on the first load,
 * so opening the app never replays old events. Notices close with their button or Esc
 * and leave by themselves after a few seconds (not while hovered or focused).
 */
import type { GameSummary } from "@ascend/shared";
import { useCallback, useEffect, useRef, useState } from "react";

import { SystemWindow, type SystemVariant } from "./SystemWindow";

export interface SystemEvent {
  id: number;
  variant: SystemVariant;
  title: string;
  text: string;
}

interface Snapshot {
  level: number;
  rank: string;
  questDone: boolean;
}

const snapshot = (g: GameSummary): Snapshot => ({
  level: g.xp.level,
  rank: g.xp.rank,
  questDone: g.quest.length > 0 && g.quest.every((q) => q.completed_at),
});

/** The events between two summaries (pure, so it is unit-tested). */
export function eventsBetween(prev: Snapshot | null, g: GameSummary): Omit<SystemEvent, "id">[] {
  if (!prev) return [];
  const next = snapshot(g);
  const out: Omit<SystemEvent, "id">[] = [];
  if (next.level > prev.level) {
    out.push({
      variant: "levelup",
      title: "Level up",
      text: next.rank !== prev.rank
        ? `Level ${next.level} reached. Rank up: ${prev.rank} → ${next.rank} (${g.xp.rank_title}).`
        : `Level ${next.level} reached. Rank ${next.rank} · ${g.xp.rank_title}.`,
    });
  }
  if (next.questDone && !prev.questDone) {
    const xp = g.quest.reduce((n, q) => n + q.xp, 0);
    out.push({ variant: "quest", title: "Quest complete", text: `Daily quest cleared: ${g.quest.length} of ${g.quest.length} tasks · ${xp} XP.` });
  }
  return out;
}

const LIFETIME_MS = 7000;

export function SystemEvents({ game }: { game: GameSummary | undefined }) {
  const last = useRef<Snapshot | null>(null);
  const seq = useRef(0);
  const [events, setEvents] = useState<SystemEvent[]>([]);

  useEffect(() => {
    if (!game) return;
    const fresh = eventsBetween(last.current, game);
    last.current = snapshot(game);
    if (fresh.length) setEvents((list) => [...list, ...fresh.map((e) => ({ ...e, id: ++seq.current }))].slice(-3));
  }, [game]);

  const dismiss = useCallback((id: number) => setEvents((list) => list.filter((e) => e.id !== id)), []);

  // Esc closes the newest notice.
  useEffect(() => {
    if (events.length === 0) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !document.querySelector('[aria-modal="true"]')) dismiss(events[events.length - 1].id);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [events, dismiss]);

  return (
    <div className="pointer-events-none fixed right-6 top-20 z-40 flex w-[340px] flex-col gap-3" data-testid="system-events">
      <div role="status" className="sr-only">{events.length ? `${events[events.length - 1].title}. ${events[events.length - 1].text}` : ""}</div>
      {events.map((e) => (
        <Notice key={e.id} event={e} rank={game?.xp.rank} onClose={() => dismiss(e.id)} />
      ))}
    </div>
  );
}

function Notice({ event, rank, onClose }: { event: SystemEvent; rank?: string; onClose: () => void }) {
  const [held, setHeld] = useState(false);
  useEffect(() => {
    if (held) return;
    const t = setTimeout(onClose, LIFETIME_MS);
    return () => clearTimeout(t);
  }, [held, onClose]);
  return (
    <div className="pointer-events-auto" onMouseEnter={() => setHeld(true)} onMouseLeave={() => setHeld(false)}
      onFocus={() => setHeld(true)} onBlur={() => setHeld(false)}>
      <SystemWindow variant={event.variant} title={event.title} rank={rank} testId={`system-event-${event.variant}`}
        actions={<button type="button" className="btn-ghost px-3 py-1.5 text-xs" onClick={onClose}>Close</button>}>
        <p className="text-sm text-ink">{event.text}</p>
      </SystemWindow>
    </div>
  );
}
