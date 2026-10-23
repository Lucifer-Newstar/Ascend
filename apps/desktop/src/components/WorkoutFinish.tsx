/**
 * The workout finish moment (v1.2): finishing a session is an event, not a toast. A full
 * screen over the theme's event art (behind a dark scrim, so every word sits on a solid
 * panel) shows what the session was worth: sets, XP, level and rank progress, the streak,
 * the weekly boss and the trainer's reaction. It also explains the 3-set rule, so a short
 * session that earns +0 XP never looks like a bug.
 */
import type { BossRaid, FinishedWorkout, GameSummary } from "@ascend/shared";
import { useRef } from "react";
import { createPortal } from "react-dom";

import { count, num } from "../lib/format";
import { useAppTheme } from "../lib/prefs";
import { themeArt } from "../lib/themeArt";
import { EventBackdrop } from "./EventBackdrop";
import { Confetti } from "./Celebrate";
import { SystemWindow } from "./SystemWindow";
import { TrainerPortrait, useTrainer, useTrainerOn } from "./Trainer";

/** A session counts for XP from this many sets (or 10 minutes of timed work): formulas.py. */
export const SESSION_MIN_SETS = 3;
export const SESSION_MIN_TIMED_MINUTES = 10;

export interface FinishSummary {
  result: FinishedWorkout;
  game?: GameSummary | null;
  boss?: BossRaid | null;
  /** The level before the session, to call out a level-up. */
  levelBefore?: number | null;
}

export function sessionCounted(r: FinishedWorkout): boolean {
  return r.workout.sets.length >= SESSION_MIN_SETS || r.active_minutes >= SESSION_MIN_TIMED_MINUTES;
}

/** The trainer's line for the finish screen: plain, kind and specific. */
export function finishLine(s: FinishSummary): { mood: "proud" | "hyped" | "neutral"; text: string } {
  const r = s.result;
  const sets = r.workout.sets.length;
  if (!sessionCounted(r)) {
    const more = SESSION_MIN_SETS - sets;
    return { mood: "neutral", text: `Good start. ${more === 1 ? "One more set" : `${more} more sets`} and a session counts for XP. Showing up is the hard part, and you did it.` };
  }
  if (s.levelBefore != null && s.game && s.game.xp.level > s.levelBefore) {
    return { mood: "hyped", text: `Level ${s.game.xp.level}! That session pushed you over. Rest well tonight.` };
  }
  if (s.boss && s.boss.defeated) return { mood: "hyped", text: `The ${s.boss.name} is down! Every set this week went into that.` };
  if (r.hard_sets >= 10) return { mood: "proud", text: `${r.hard_sets} hard sets. That was real work. Eat well and sleep; that is where you get stronger.` };
  return { mood: "proud", text: "That one counted. Same time next session and the streak keeps growing." };
}

function exerciseList(r: FinishedWorkout): { name: string; sets: number }[] {
  const by = new Map<string, number>();
  for (const s of r.workout.sets) by.set(s.exercise_name, (by.get(s.exercise_name) ?? 0) + 1);
  return [...by.entries()].map(([name, sets]) => ({ name, sets }));
}

export function WorkoutFinish({ summary, onClose, onToday }: { summary: FinishSummary; onClose: () => void; onToday?: () => void }) {
  const theme = useAppTheme();
  const art = themeArt(theme, "event");
  const trainerOn = useTrainerOn();
  const trainer = useTrainer();
  const done = useRef<HTMLButtonElement>(null);
  const { result: r, game, boss } = summary;
  const counted = sessionCounted(r);
  const line = finishLine(summary);
  const xp = game?.xp;
  const pct = xp && xp.xp_for_next > 0 ? Math.min(100, Math.round((xp.xp_into_level / xp.xp_for_next) * 100)) : 0;
  const exercises = exerciseList(r);
  return createPortal(
    <div className="fixed inset-0 z-50 flex overflow-y-auto p-6" data-testid="workout-finish" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <EventBackdrop art={art} />
      {counted && <Confetti pieces={18} />}
      <div className="relative z-10 m-auto grid w-full max-w-4xl grid-cols-1 items-center gap-6 md:grid-cols-[auto_minmax(0,1fr)]">
        {trainerOn && (
          <div className="hidden flex-col items-center gap-2 md:flex">
            <TrainerPortrait mood={line.mood} size={220} className="shadow-2xl" />
            <span className="rounded-md bg-panel px-2 py-0.5 text-xs text-muted">{trainer.name}</span>
          </div>
        )}
        <SystemWindow variant="levelup" title="Workout complete" rank={xp?.rank} initialFocus={done} className="bg-panel"
          actions={
            <>
              {onToday && <button type="button" className="btn-ghost" onClick={onToday}>Back to Today</button>}
              <button ref={done} type="button" className="btn-primary" onClick={onClose}>Done</button>
            </>
          }>
          <p className="font-display text-4xl font-bold text-ink" data-testid="finish-xp">+{r.xp_awarded} XP</p>
          <p className="mt-1 text-sm text-muted">
            {count(r.workout.sets.length, "set")} · {count(r.hard_sets, "hard set")} · {r.active_minutes < 1 ? "under 1 min" : `${Math.round(r.active_minutes)} min`}
          </p>
          {trainerOn && <p className="mt-3 rounded-md border border-line-2 bg-panel-2 px-3 py-2 text-sm text-ink" data-testid="finish-trainer">{line.text}</p>}

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {xp && (
              <div className="rounded-md bg-panel-2 p-3">
                <p className="text-xs text-muted">Level {xp.level} · Rank {xp.rank}</p>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-line" role="progressbar" aria-label="Progress to the next level" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
                  <span className="block h-full rounded-full bg-xp" style={{ width: `${pct}%` }} />
                </div>
                <p className="mt-1 text-[11px] text-muted">{num(xp.xp_into_level)} / {num(xp.xp_for_next)} XP to level {xp.level + 1}</p>
              </div>
            )}
            {game && (
              <div className="rounded-md bg-panel-2 p-3">
                <p className="text-xs text-muted">Streak</p>
                <p className="font-display text-xl font-bold text-ink">{count(game.streak.current, "day")}</p>
                <p className="text-[11px] text-muted">Best {game.streak.best}</p>
              </div>
            )}
            {boss && (
              <div className="rounded-md bg-panel-2 p-3">
                <p className="text-xs text-muted">Weekly boss</p>
                <p className="truncate text-sm font-semibold text-ink">{boss.name}</p>
                <p className="text-[11px] text-muted">{boss.defeated ? "Defeated this week" : `${boss.hp_left} HP left · ${count(boss.days_left, "day")} to go`}</p>
              </div>
            )}
          </div>

          {exercises.length > 0 && (
            <ul className="mt-4 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2" aria-label="What you did">
              {exercises.map((e) => (
                <li key={e.name} className="flex justify-between gap-3">
                  <span className="truncate text-ink">{e.name}</span>
                  <span className="shrink-0 text-xs text-muted">{count(e.sets, "set")}</span>
                </li>
              ))}
            </ul>
          )}

          <details className="mt-4 rounded-md bg-panel-2 px-3 py-2 text-xs text-muted" open={!counted}>
            <summary className="cursor-pointer text-ink">How XP works</summary>
            <p className="mt-1">
              A workout counts once it has {SESSION_MIN_SETS} sets (or {SESSION_MIN_TIMED_MINUTES} minutes of cardio, martial arts or mobility).
              Each hard set (effort 7 out of 10 or more, or not rated) is worth 3 XP and an easier set 1 XP, plus a bonus for finishing.
              {counted ? "" : " This session had fewer, so it earned no XP, but every set is saved."}
            </p>
          </details>
        </SystemWindow>
      </div>
    </div>,
    document.body,
  );
}
