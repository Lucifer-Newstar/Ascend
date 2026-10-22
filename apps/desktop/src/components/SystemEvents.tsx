/**
 * System events: the level-up / rank-up and quest-complete notices.
 *
 * Watches the game summary (refreshed whenever something is logged) and, when the level,
 * the rank or the daily quest's completion changes for the better, shows a small,
 * non-modal System window in the top-right corner. Nothing shows on the first load,
 * so opening the app never replays old events. Notices close with their button or Esc
 * and leave by themselves after a few seconds (not while hovered or focused).
 *
 * The System's voice from the intelligence layer (deload advised, target raised, muscle
 * recovered) arrives through `notices`: each notice id shows once ever (remembered in
 * localStorage) and at most one per refresh, so the System stays rare.
 */
import type { GameSummary, SystemNotice } from "@ascend/shared";
import { useCallback, useEffect, useRef, useState } from "react";

import { play } from "../lib/sound";
import { Confetti } from "./Celebrate";
import { SystemWindow, type SystemVariant } from "./SystemWindow";
import { TrainerPortrait, useTrainerOn } from "./Trainer";
import { RankBadge } from "./XpBar";

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
      title: next.rank !== prev.rank ? "Rank up" : "Level up",
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
const SEEN_KEY = "ascend.system.notices.seen";
const NOTICE_VARIANT: Record<string, SystemVariant> = { deload: "warning", raised: "notice", recovered: "quest" };

function seenIds(): string[] {
  try {
    const raw = window.localStorage.getItem(SEEN_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

/** The one notice to show now: the first the app has not shown before (pure). */
export function nextNotice(notices: SystemNotice[], seen: string[]): SystemNotice | null {
  return notices.find((n) => !seen.includes(n.id)) ?? null;
}

function markSeen(id: string): void {
  try {
    window.localStorage.setItem(SEEN_KEY, JSON.stringify([...seenIds(), id].slice(-200)));
  } catch {
    // storage unavailable: the notice may show again next launch, which is harmless
  }
}

export function SystemEvents({ game, notices }: { game: GameSummary | undefined; notices?: () => Promise<SystemNotice[]> }) {
  const last = useRef<Snapshot | null>(null);
  const seq = useRef(0);
  const [events, setEvents] = useState<SystemEvent[]>([]);

  useEffect(() => {
    if (!game) return;
    const fresh = eventsBetween(last.current, game);
    last.current = snapshot(game);
    if (fresh.length) {
      setEvents((list) => [...list, ...fresh.map((e) => ({ ...e, id: ++seq.current }))].slice(-3));
      play(fresh.some((e) => e.variant === "levelup") ? "levelup" : "quest");
    }
  }, [game]);

  // System notices from the engines, re-read whenever the game summary refreshes.
  useEffect(() => {
    if (!game || !notices) return;
    let alive = true;
    notices()
      .then((list) => {
        const n = alive ? nextNotice(list, seenIds()) : null;
        if (!n) return;
        markSeen(n.id);
        setEvents((all) => [...all, { id: ++seq.current, variant: NOTICE_VARIANT[n.code] ?? "notice", title: n.title, text: n.text }].slice(-3));
        play("quest");
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [game, notices]);

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
        <Notice key={e.id} event={e} rank={game?.xp.rank} level={game?.xp.level} onClose={() => dismiss(e.id)} />
      ))}
    </div>
  );
}

/**
 * v8 moments: level-up, rank-up and quest-clear notices carry the trainer (or the rank
 * badge in plain mode), a confetti burst and a pop-in (transform/opacity only; Reduce
 * motion shows them still, without confetti).
 */
function MomentBody({ event, rank, level }: { event: SystemEvent; rank?: string; level?: number }) {
  const trainer = useTrainerOn();
  const rankUp = event.title === "Rank up";
  return (
    <div className="moment-pop relative flex items-center gap-3" data-testid={`moment-${rankUp ? "rankup" : event.variant}`}>
      <Confetti pieces={rankUp ? 22 : 14} spread={rankUp ? 110 : 80} />
      {trainer ? (
        <TrainerPortrait mood={event.variant === "levelup" ? "hyped" : "proud"} size={64} />
      ) : (
        rank && <RankBadge rank={rank} size={56} />
      )}
      <div className="min-w-0">
        {event.variant === "levelup" && level !== undefined && (
          <p className="font-display text-2xl font-bold leading-none text-xp">LV {level}{rankUp && rank ? ` · ${rank}` : ""}</p>
        )}
        <p className="mt-1 text-sm text-ink">{event.text}</p>
      </div>
    </div>
  );
}

function Notice({ event, rank, level, onClose }: { event: SystemEvent; rank?: string; level?: number; onClose: () => void }) {
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
        {event.variant === "levelup" || event.variant === "quest" ? (
          <MomentBody event={event} rank={rank} level={level} />
        ) : (
          <p className="text-sm text-ink">{event.text}</p>
        )}
      </SystemWindow>
    </div>
  );
}
