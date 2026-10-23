/**
 * The weekly boss raid on Today (boss-v1, ADR-0022): the boss, its HP bar and the damage
 * your logged sets did this week, with the reward on view before you earn it. Beaten by
 * Sunday: bonus XP and the boss's title on your Hunter profile. Missed: nothing is lost.
 * The HP bar moves with transform only; with Reduce motion it simply shows the value.
 */
import type { BossRaid } from "@ascend/shared";
import { useEffect, useId, useRef, useState } from "react";

import { bossArt } from "../lib/bosses";
import { play } from "../lib/sound";
import { Confetti } from "./Celebrate";
import { TrainerSays, useTrainerOn } from "./Trainer";

/** The boss's crest: a horned hexagon, coloured by state. Decorative. */
function Crest({ defeated }: { defeated: boolean }) {
  return (
    <svg viewBox="0 0 48 48" width={44} height={44} aria-hidden="true" className={defeated ? "text-good" : "text-bad"}>
      <path d="M10 14 4 4l12 6M38 14l6-10-12 6" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M24 8 38 16v16L24 40 10 32V16Z" fill="currentColor" fillOpacity="0.15" stroke="currentColor" strokeWidth="2" />
      {defeated ? (
        <path d="m17 24 5 5 9-10" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      ) : (
        <>
          <path d="m16 21 5 3M32 21l-5 3" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
          <path d="M19 31h10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
        </>
      )}
    </svg>
  );
}

const SOURCE_WORDS: Record<BossRaid["hp_source"], string> = {
  program: "your program's week",
  history: "your recent weeks",
  starter: "a starter week",
};

export function bossLine(b: BossRaid): string {
  if (b.defeated) return `${b.name} is down, Hunter. +${b.bonus_xp} XP and the title "${b.title}" are yours.`;
  if (b.damage === 0) return `A new boss rises, Hunter: ${b.name}, ${b.hp} HP. Every set you log hits it. Beat it by Sunday.`;
  return `${b.name} has ${b.hp_left} HP left, Hunter. ${b.hp_left} more sets by Sunday and it falls.`;
}

export function BossRaidCard({ boss }: { boss: BossRaid }) {
  const trainer = useTrainerOn();
  const [open, setOpen] = useState(false);
  const id = useId();
  // The defeat moment plays when the boss falls while you watch (not on every visit).
  const was = useRef(boss.defeated);
  const [moment, setMoment] = useState(false);
  useEffect(() => {
    if (boss.defeated && !was.current) {
      setMoment(true);
      play("levelup");
    }
    was.current = boss.defeated;
  }, [boss.defeated]);
  const left = boss.hp > 0 ? boss.hp_left / boss.hp : 0;
  const days = boss.days_left === 0 ? "last day" : `${boss.days_left} day${boss.days_left === 1 ? "" : "s"} left`;
  return (
    <section className={`card boss-card relative overflow-hidden p-5 ${boss.defeated ? "boss-defeated" : ""} ${moment ? "moment-pop" : ""}`} aria-labelledby={`${id}-t`} data-testid="boss-raid">
      {moment && <Confetti pieces={22} spread={120} duration={1100} />}
      {moment && <p className="sr-only" role="status">{boss.name} defeated. Plus {boss.bonus_xp} XP and the title {boss.title}.</p>}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          {bossArt(boss.name) ? (
            <img src={bossArt(boss.name)!} alt={`${boss.name}, this week's boss`} width={72} height={72} data-testid="boss-art"
              className={`h-[72px] w-[72px] rounded-lg border object-cover ${boss.defeated ? "border-good/60 grayscale" : "border-bad/50"}`} />
          ) : (
            <Crest defeated={boss.defeated} />
          )}
          <div>
            <p className="font-display text-[11px] font-bold uppercase tracking-[0.18em] text-bad">Weekly boss raid</p>
            <h2 id={`${id}-t`} className="text-display-l text-ink">{boss.name}</h2>
          </div>
        </div>
        <span className={`chip ${boss.defeated ? "border-good/60 text-good" : "border-bad/50 text-bad"}`}>{boss.defeated ? "Defeated" : days}</span>
      </div>
      <div className="mt-3">
        <div className="mb-1 flex justify-between text-xs text-muted">
          <span>HP</span>
          <span className="tabular-nums text-ink">{boss.hp_left} / {boss.hp}</span>
        </div>
        <div className="relative h-3 overflow-hidden rounded-full bg-line" role="progressbar" aria-label={`${boss.name} HP`} aria-valuemin={0} aria-valuemax={boss.hp} aria-valuenow={boss.hp_left}>
          <span className="boss-hp absolute inset-0 origin-left rounded-full bg-bad transition-transform duration-700 ease-out" style={{ transform: `scaleX(${left})` }} />
        </div>
        <p className="mt-1.5 text-xs text-muted">{boss.damage} damage dealt: every training set you log this week hits for 1.</p>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs" aria-label="Reward">
        <span className="text-muted">Reward:</span>
        <span className="chip border-xp/50 text-xp">+{boss.bonus_xp} XP</span>
        <span className="chip border-accent/50 text-ink">Title: {boss.title}</span>
        <span className="text-faint">No penalty if it survives.</span>
      </div>
      {trainer && (
        <div className="mt-3">
          <TrainerSays mood={boss.defeated ? "proud" : "hyped"} size={40}>
            <p className="text-sm text-ink">{bossLine(boss)}</p>
          </TrainerSays>
        </div>
      )}
      <div className="mt-2 text-right">
        <button type="button" className="text-xs text-accent hover:underline" aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}>Why?</button>
      </div>
      {open && (
        <div id={id} className="panel-in mt-2 rounded-md border border-line bg-panel-2 p-3 text-xs text-muted">
          <p className="text-ink">HP {boss.hp} comes from {SOURCE_WORDS[boss.hp_source]}: {boss.hp_note}.</p>
          <p className="mt-1">{boss.why.formula} ({boss.algo_version}).</p>
          <p className="mt-1">Week {boss.week_start} to {boss.week_end}. Titles earned so far: {boss.titles_earned}.</p>
        </div>
      )}
    </section>
  );
}
