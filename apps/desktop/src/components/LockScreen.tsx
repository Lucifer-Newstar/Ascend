/**
 * The lock screen (v1.2): every launch opens on the landing art with your hunter tile, like
 * a desktop sign-in screen. Click the tile or press Enter to go in; it zooms and fades into
 * Today (instant with reduced motion). ASCEND has no PIN or password, so none is asked here.
 * The words sit on solid panels, so every theme stays readable.
 */
import type { GameSummary } from "@ascend/shared";
import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import { useReducedMotion } from "../lib/motion";
import { usePrefs } from "../lib/prefs";
import { useApi } from "../lib/useApi";
import { Avatar } from "./Avatar";
import { LandingArt } from "./LandingArt";
import { RankBadge } from "./XpBar";

/** How long the zoom-and-fade into the app takes (ms). */
export const LOCK_LEAVE_MS = 380;

export function LockScreen({ game, onEnter, now = () => new Date() }: {
  game: GameSummary | null | undefined;
  onEnter: () => void;
  now?: () => Date;
}) {
  const { settings } = usePrefs();
  const reduce = useReducedMotion();
  const profile = useApi(api.profile, []);
  const [leaving, setLeaving] = useState(false);
  const tile = useRef<HTMLButtonElement>(null);
  const left = useRef(false);

  const enter = () => {
    if (left.current) return;
    left.current = true;
    if (reduce) {
      onEnter();
      return;
    }
    setLeaving(true);
    window.setTimeout(onEnter, LOCK_LEAVE_MS);
  };

  useEffect(() => tile.current?.focus(), []);
  // Enter goes in even when focus wandered off the tile (a click on the background).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Enter" && document.activeElement !== tile.current) {
        e.preventDefault();
        enter();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // enter only reads refs and stable props
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const name = profile.data?.name?.trim() || "Hunter";
  const rank = game?.xp.rank ?? "E";
  const level = game?.xp.level ?? 1;
  const at = now();
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
        <Avatar look={settings.avatar ?? "male"} rank={rank} outfit={settings.outfit} weapon={settings.weapon} relic={settings.relic} pet={settings.pet} height={200} />
        <span className="mt-1 text-h2 text-ink" data-testid="lock-name">{name}</span>
        <span className="flex items-center gap-2 text-sm text-muted" data-testid="lock-rank">
          <RankBadge rank={rank} size={26} /> Level {level} · Rank {rank}
        </span>
      </button>
      <p className="relative z-[1] rounded-md bg-panel px-3 py-1.5 text-sm text-muted">Click your hunter or press Enter</p>
    </main>
  );
}
