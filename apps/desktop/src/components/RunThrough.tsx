/**
 * The full-screen timer (v1.2): a run-through view for the workout. Big rest countdown,
 * the current exercise with its picture, the set to do, what is next and a trainer cue.
 * While it is open the screen is kept awake (no dimming, no sleep) and the window goes
 * full screen; Esc or Exit leaves at any time and lets the screen sleep again.
 */
import type { Exercise } from "@ascend/shared";
import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";

import { count } from "../lib/format";
import { useKeepAwake } from "../lib/keepAwake";
import { useAppTheme } from "../lib/prefs";
import { themeArt } from "../lib/themeArt";
import { ExerciseArt } from "./ExerciseArt";
import { TrainerPortrait, useTrainerOn } from "./Trainer";

export function clock(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** The trainer's cue for the moment: resting, nearly done resting, or time to lift. */
export function timerCue(restLeft: number, setsDone: number): { mood: "neutral" | "hyped" | "proud"; text: string } {
  if (restLeft > 10) return { mood: "neutral", text: "Breathe slow. Shake out your arms. Next set when the timer ends." };
  if (restLeft > 0) return { mood: "hyped", text: "Get in position. Almost time." };
  if (setsDone === 0) return { mood: "hyped", text: "First set. Smooth reps, full range. Press Set done when you finish." };
  return { mood: "proud", text: "Rest is over. Same good form, one more set." };
}

export function RunThrough({
  exercise, target, setsDone, restLeft, restTotal, paused, busy = false, nextUp,
  onTogglePause, onSkipRest, onSetDone, onExit,
}: {
  exercise: Pick<Exercise, "name" | "image" | "section" | "muscles">;
  target: string | null;
  setsDone: number;
  restLeft: number;
  restTotal: number;
  paused: boolean;
  busy?: boolean;
  nextUp?: string | null;
  onTogglePause: () => void;
  onSkipRest: () => void;
  onSetDone: () => void;
  onExit: () => void;
}) {
  useKeepAwake(true);
  const art = themeArt(useAppTheme(), "event");
  const trainerOn = useTrainerOn();
  const root = useRef<HTMLDivElement>(null);
  const resting = restLeft > 0;
  const cue = timerCue(restLeft, setsDone);

  // Full screen while open (a no-op where the browser refuses it), and back on close.
  useEffect(() => {
    const el = root.current;
    if (el?.requestFullscreen && !document.fullscreenElement) void el.requestFullscreen().catch(() => undefined);
    return () => {
      if (document.fullscreenElement && document.exitFullscreen) void document.exitFullscreen().catch(() => undefined);
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onExit();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onExit]);

  const pct = resting && restTotal > 0 ? Math.round((restLeft / restTotal) * 100) : 0;
  return createPortal(
    <div ref={root} role="dialog" aria-modal="true" aria-label="Full-screen timer" data-testid="run-through"
      className="fixed inset-0 z-50 flex flex-col bg-bg p-8">
      <div className="event-art" style={art ? { ["--event-bg" as string]: `url(${art})` } : { background: "var(--color-bg)" }} aria-hidden="true" />
      <div className="relative z-10 flex items-center justify-between">
        <span className="rounded-md bg-panel px-3 py-1 font-display text-xs font-bold uppercase tracking-[0.2em] text-muted">[ Timer ] screen stays awake</span>
        <button type="button" className="btn-ghost bg-panel" onClick={onExit}>Exit (Esc)</button>
      </div>
      <div className="relative z-10 mx-auto grid w-full max-w-5xl flex-1 grid-cols-1 items-center gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="rounded-xl bg-panel p-6 text-center">
          <p className="text-sm text-muted">{resting ? (paused ? "Rest paused" : "Rest") : "Your set"}</p>
          <p className="event-title font-display text-[7rem] font-bold leading-none text-ink" role="timer" aria-live="off" data-testid="run-clock">
            {resting ? clock(restLeft) : "GO"}
          </p>
          {resting && (
            <div className="mx-auto mt-3 h-2 max-w-sm overflow-hidden rounded-full bg-line" aria-hidden="true">
              <span className="block h-full rounded-full bg-accent transition-[width] duration-1000 ease-linear" style={{ width: `${pct}%` }} />
            </div>
          )}
          <div className="mt-5 flex justify-center gap-3">
            {resting ? (
              <>
                <button type="button" className="btn-ghost" onClick={onTogglePause}>{paused ? "Resume" : "Pause"}</button>
                <button type="button" className="btn-primary" onClick={onSkipRest}>Skip rest</button>
              </>
            ) : (
              <button type="button" className="btn-primary px-8 text-lg" disabled={busy} onClick={onSetDone}>Set done</button>
            )}
          </div>
        </div>
        <div className="space-y-4 rounded-xl bg-panel p-6">
          <div className="flex items-start gap-4">
            <div className="w-36 shrink-0 overflow-hidden rounded-lg"><ExerciseArt exercise={exercise} className="h-36" /></div>
            <div className="min-w-0">
              <h2 className="text-h2 text-ink">{exercise.name}</h2>
              <p className="mt-1 text-sm text-muted">{target ? <>This set: <span className="text-ink">{target}</span></> : "Pick your own target"}</p>
              <p className="text-sm text-muted">{count(setsDone, "set")} done</p>
              {nextUp && <p className="mt-2 text-sm text-muted">Next up: <span className="text-ink">{nextUp}</span></p>}
            </div>
          </div>
          {trainerOn && (
            <div className="flex items-center gap-3 rounded-lg bg-panel-2 p-3" data-testid="run-cue">
              <TrainerPortrait mood={cue.mood} size={64} />
              <p className="text-sm text-ink">{cue.text}</p>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
