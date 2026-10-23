/**
 * The boss screen (v1.2): the weekly boss full size over the theme's event art (dark
 * scrim, solid panel for every word). Opened from the boss card on Today. Shows the art,
 * the HP left, the days left, the reward and the trainer's line; Esc or Close leaves.
 */
import type { BossRaid } from "@ascend/shared";
import { useRef } from "react";
import { createPortal } from "react-dom";

import { bossArt } from "../lib/bosses";
import { useAppTheme } from "../lib/prefs";
import { themeArt } from "../lib/themeArt";
import { SystemWindow } from "./SystemWindow";
import { TrainerSays, useTrainerOn } from "./Trainer";
import { bossLine } from "./BossRaid";

export function BossScreen({ boss, onClose }: { boss: BossRaid; onClose: () => void }) {
  const art = themeArt(useAppTheme(), "event");
  const trainer = useTrainerOn();
  const close = useRef<HTMLButtonElement>(null);
  const portrait = bossArt(boss.name);
  const left = boss.hp > 0 ? boss.hp_left / boss.hp : 0;
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6" data-testid="boss-screen">
      <div className="event-art" style={art ? { ["--event-bg" as string]: `url(${art})` } : { background: "rgba(0,0,0,0.75)" }} aria-hidden="true" />
      <div className="relative z-10 grid w-full max-w-4xl grid-cols-1 items-center gap-6 md:grid-cols-[auto_minmax(0,1fr)]">
        {portrait && (
          <img src={portrait} alt={`${boss.name}, this week's boss`} width={320} height={320} data-testid="boss-screen-art"
            className={`mx-auto h-[320px] w-[320px] rounded-2xl border-2 object-cover shadow-2xl ${boss.defeated ? "border-good/70 grayscale" : "border-bad/70"}`} />
        )}
        <SystemWindow variant="warning" title="Weekly boss" modal onClose={onClose} initialFocus={close} className="bg-panel"
          actions={<button ref={close} type="button" className="btn-primary" onClick={onClose}>Close</button>}>
          <h2 className="event-title text-display-l text-ink">{boss.name}</h2>
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
