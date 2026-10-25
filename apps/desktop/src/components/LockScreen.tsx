/**
 * The lock screen (v1.2): every launch opens on the landing art with your hunter tile, like
 * a desktop sign-in screen. Click the tile or press Enter to go in; it zooms and fades into
 * Today (instant with reduced motion). ASCEND has no PIN or password, so none is asked here.
 * The words sit on solid panels, so every theme stays readable.
 *
 * v1.4 (review 2.4, M14): the lock screen is the workout door. It says what today is
 * ("Today: Push A · 4 moves" or "Rest day ✓"), and on a training day Enter starts today's
 * session on Train; the tile still goes to Today. A short day gets the 10-minute version.
 * Settings > Trainer can switch the lock screen off.
 */
import type { GameSummary, Plan } from "@ascend/shared";
import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import { equippedGear } from "../lib/cosmetics";
import { useReducedMotion } from "../lib/motion";
import { localDay, rememberShort } from "../lib/shortSession";
import { usePrefs } from "../lib/prefs";
import { useApi } from "../lib/useApi";
import { Avatar } from "./Avatar";
import { LandingArt } from "./LandingArt";
import { RankBadge } from "./XpBar";

/** How long the zoom-and-fade into the app takes (ms). */
export const LOCK_LEAVE_MS = 380;

export type TodayDoor =
  | { kind: "session"; name: string; moves: number }
  | { kind: "done"; name: string }
  | { kind: "rest" }
  | { kind: "none" };

/** What the door says about today: rest day, today's session, or already trained. */
export function todayDoor(game: GameSummary | null | undefined, plan: Plan | null | undefined, today: string): TodayDoor {
  if (game?.streak?.rest_today) return { kind: "rest" };
  if (!plan) return { kind: "none" };
  if (plan.last_trained === today) return { kind: "done", name: plan.next.name };
  return { kind: "session", name: plan.next.name, moves: plan.next.items.length };
}

export function LockScreen({ game, onEnter, onStart, now = () => new Date() }: {
  game: GameSummary | null | undefined;
  onEnter: () => void;
  /** v1.4: start today's session on Train (Enter on a training day). */
  onStart?: () => void;
  now?: () => Date;
}) {
  const { settings } = usePrefs();
  const reduce = useReducedMotion();
  const profile = useApi(api.profile, []);
  const plan = useApi(api.currentPlan, [], { cacheKey: "plan" });
  const [leaving, setLeaving] = useState(false);
  const tile = useRef<HTMLButtonElement>(null);
  const left = useRef(false);
  const at = now();
  const door = todayDoor(game, plan.data, localDay(at));
  const canStart = door.kind === "session" && onStart !== undefined;

  const go = (then: () => void) => {
    if (left.current) return;
    left.current = true;
    if (reduce) {
      then();
      return;
    }
    setLeaving(true);
    window.setTimeout(then, LOCK_LEAVE_MS);
  };
  const enter = () => go(onEnter);
  const start = () => go(onStart ?? onEnter);
  const startShort = async () => {
    try {
      const s = await api.shortSession(10);
      if (s) rememberShort(s, at);
    } catch {
      // the full session opens instead; Train still works
    }
    start();
  };
  // Enter on a training day starts today's session (one key from launch to the first set).
  const enterKey = useRef(enter);
  useEffect(() => {
    enterKey.current = canStart ? start : enter;
  });

  // Focus the tile, or "Start today's session" on a training day, so Enter does the right thing.
  const startBtn = useRef<HTMLButtonElement>(null);
  useEffect(() => (canStart ? startBtn.current : tile.current)?.focus(), [canStart]);
  // Enter goes in even when focus wandered off the tile (a click on the background).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = document.activeElement;
      if (e.key === "Enter" && el !== tile.current && !(el instanceof HTMLButtonElement)) {
        e.preventDefault();
        enterKey.current();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const name = profile.data?.name?.trim() || "Hunter";
  const rank = game?.xp.rank ?? "E";
  const level = game?.xp.level ?? 1;
  const time = at.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  const date = at.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });

  return (
    <main className={`lock-screen relative flex min-h-full flex-col items-center justify-center gap-6 overflow-hidden bg-bg p-8 ${leaving ? "lock-leaving" : ""}`}
      data-testid="lock-screen">
      <LandingArt dim />
      <div className="relative z-[1] rounded-xl bg-panel/95 px-5 py-2 text-center shadow-lg" data-testid="lock-clock">
        <div className="font-display text-3xl font-bold tabular-nums text-ink">{time}</div>
        <div className="text-xs text-muted">{date}</div>
      </div>
      <button ref={tile} type="button" onClick={enter} data-testid="lock-tile"
        aria-label={`Enter ASCEND as ${name}, level ${level}, rank ${rank}`}
        className="lock-tile relative z-[1] flex flex-col items-center gap-2 rounded-2xl border border-line-2 bg-panel px-10 pb-6 pt-5 shadow-2xl outline-none hover:border-accent focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent">
        <Avatar look={settings.avatar ?? "male"} rank={rank} height={200}
          {...equippedGear({ outfit: settings.outfit, weapon: settings.weapon, relic: settings.relic, pet: settings.pet }, { themed: settings.themed_cosmetics ?? true })} />
        <span className="mt-1 text-h2 text-ink" data-testid="lock-name">{name}</span>
        <span className="flex items-center gap-2 text-sm text-muted" data-testid="lock-rank">
          <RankBadge rank={rank} size={26} /> Level {level} · Rank {rank}
        </span>
      </button>
      <section className="relative z-[1] flex flex-col items-center gap-2 rounded-xl bg-panel/95 px-5 py-3 text-center shadow-lg" data-testid="lock-door" aria-label="Today">
        {door.kind === "rest" && <p className="text-sm text-ink">Rest day ✓ Recovery is part of the plan.</p>}
        {door.kind === "done" && <p className="text-sm text-ink">Today&apos;s session is done ✓ Next: {door.name}</p>}
        {door.kind === "session" && (
          <p className="text-sm text-ink">Today: <span className="font-semibold">{door.name}</span> · {door.moves} {door.moves === 1 ? "move" : "moves"}</p>
        )}
        {canStart ? (
          <div className="flex flex-wrap justify-center gap-2">
            <button ref={startBtn} type="button" className="btn-primary" onClick={start} data-testid="lock-start">Start today&apos;s session</button>
            <button type="button" className="btn-ghost" onClick={() => void startShort()} data-testid="lock-short">Short on time? 10-minute version</button>
          </div>
        ) : null}
        <p className="text-xs text-muted">{canStart ? "Press Enter to start, or click your hunter for Today" : "Click your hunter or press Enter"}</p>
      </section>
    </main>
  );
}
