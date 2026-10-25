/**
 * The boss screen (v1.2): the weekly boss full size over the theme's event art (dark
 * scrim, solid panel for every word). Opened from the boss card on Today. Shows the art,
 * the HP left, the days left, the reward and the trainer's line; Esc or Close leaves.
 */
import type { BossRaid } from "@ascend/shared";
import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";

import { CATEGORY_LABEL, bossArt } from "../lib/bosses";
import { dropName } from "../lib/cosmetics";
import { useAppTheme } from "../lib/prefs";
import { themeArt } from "../lib/themeArt";
import { EventBackdrop } from "./EventBackdrop";
import { SystemWindow } from "./SystemWindow";
import { TrainerSays, useTrainerOn } from "./Trainer";
import { bossEyebrow, bossLine } from "./BossRaid";

export function BossScreen({ boss, onClose }: { boss: BossRaid; onClose: () => void }) {
  const art = themeArt(useAppTheme(), "event");
  const trainer = useTrainerOn();
  const close = useRef<HTMLButtonElement>(null);
  const portrait = bossArt(boss.name);
  const left = boss.hp > 0 ? boss.hp_left / boss.hp : 0;
  // A dialog of its own (not a modal System window, which would centre itself over the
  // portrait): focus moves to Close, Esc closes.
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    close.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
    };
    document.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("keydown", onKey, true);
      previous?.focus?.();
    };
  }, [onClose]);
  return createPortal(
    <div className="fixed inset-0 z-50 flex overflow-y-auto p-6" data-testid="boss-screen" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }} role="dialog" aria-modal="true" aria-label={`${boss.name}, ${boss.seasonal ? "seasonal" : "weekly"} boss`}>
      <EventBackdrop art={art} />
      <div className="relative z-10 m-auto grid w-full max-w-4xl grid-cols-1 items-center gap-6 md:grid-cols-[auto_minmax(0,1fr)]">
        {portrait && (
          <img src={portrait} alt={`${boss.name}, this week's boss`} width={320} height={320} data-testid="boss-screen-art"
            className={`mx-auto h-[300px] w-[300px] shrink-0 rounded-2xl border-2 object-cover shadow-2xl ${boss.defeated ? "border-good/70 grayscale" : "border-bad/70"}`} />
        )}
        <SystemWindow variant="warning" title={boss.seasonal ? "Seasonal boss" : "Weekly boss"} className="min-w-0 bg-panel"
          actions={<button ref={close} type="button" className="btn-primary" onClick={onClose}>Close</button>}>
          <h2 className="text-display-l text-ink">{boss.name}</h2>
          {boss.tier && (
            <p className="mt-1 flex flex-wrap gap-1.5 text-[11px]">
              <span className="chip border-accent/50 text-ink">Tier {boss.tier}</span>
              {boss.category && <span className="chip">{CATEGORY_LABEL[boss.category]}</span>}
              {boss.seasonal && <span className="chip border-warn/60 text-warn">{bossEyebrow(boss).replace("Seasonal boss · ", "")}</span>}
            </p>
          )}
          <p className="mt-1 text-sm text-muted">{boss.defeated ? "Defeated this week" : `${boss.days_left === 0 ? "Last day" : `${boss.days_left} day${boss.days_left === 1 ? "" : "s"} left`} · beat it by Sunday`}</p>
          <div className="mt-4">
            <div className="mb-1 flex justify-between text-xs text-muted">
              <span>HP</span>
              <span className="tabular-nums text-ink">{boss.hp_left} / {boss.hp}</span>
            </div>
            <div className="relative h-4 overflow-hidden rounded-full bg-line" role="progressbar" aria-label={`${boss.name} HP`} aria-valuemin={0} aria-valuemax={boss.hp} aria-valuenow={boss.hp_left}>
              <span className="absolute inset-0 origin-left rounded-full bg-bad" style={{ transform: `scaleX(${left})` }} />
            </div>
            <p className="mt-2 text-xs text-muted">Every training set you log this week hits it for 1. No penalty if it survives.</p>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span className="chip border-xp/50 text-xp">+{boss.bonus_xp} XP</span>
            <span className="chip border-accent/50 text-ink">Title: {boss.title}</span>
            {boss.drop && dropName(boss.drop) && <span className="chip border-warn/60 text-warn">Drop: {dropName(boss.drop)}</span>}
          </div>
          {trainer && (
            <div className="mt-4">
              <TrainerSays mood={boss.defeated ? "proud" : "hyped"} size={56}>
                <p className="text-sm text-ink">{bossLine(boss)}</p>
              </TrainerSays>
            </div>
          )}
        </SystemWindow>
      </div>
    </div>,
    document.body,
  );
}
