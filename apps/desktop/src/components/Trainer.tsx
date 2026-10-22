/**
 * The trainer's portrait and speech bubble. The portrait crossfades between expressions
 * (opacity only; instant with Reduce motion). The image is decorative next to the words,
 * so its alt text names who is speaking and how.
 */
import { useEffect, useState, type ReactNode } from "react";

import { useReducedMotion } from "../lib/motion";
import { useOptionalPrefs } from "../lib/prefs";
import { TRAINER_ART, TRAINER_ICON, TRAINER_NAME, moodLabel, type TrainerMood } from "../lib/trainer";

export function useTrainerOn(): boolean {
  return useOptionalPrefs()?.settings.trainer !== false;
}

export function TrainerPortrait({ mood, size = 72, className = "" }: { mood: TrainerMood; size?: number; className?: string }) {
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(mood);
  const [prev, setPrev] = useState<TrainerMood | null>(null);
  useEffect(() => {
    if (mood === shown) return;
    if (reduce) {
      setShown(mood);
      return;
    }
    setPrev(shown);
    setShown(mood);
    const t = window.setTimeout(() => setPrev(null), 320);
    return () => window.clearTimeout(t);
  }, [mood, shown, reduce]);
  return (
    <span
      className={`trainer-portrait relative inline-block shrink-0 overflow-hidden rounded-xl border border-accent/40 bg-panel-3 ${className}`}
      style={{ width: size, height: size }}
      data-mood={shown}
      data-testid="trainer-portrait"
    >
      {prev && <img src={TRAINER_ART[prev]} alt="" className="trainer-fade-out absolute inset-0 h-full w-full object-cover object-top" />}
      <img src={TRAINER_ART[shown]} alt={moodLabel(shown)} className={`absolute inset-0 h-full w-full object-cover object-top ${prev ? "trainer-fade-in" : ""}`} />
    </span>
  );
}

export function TrainerSays({ mood, children, size = 56 }: { mood: TrainerMood; children: ReactNode; size?: number }) {
  return (
    <div className="flex items-start gap-3" data-testid="trainer-says">
      <TrainerPortrait mood={mood} size={size} />
      <div className="trainer-bubble relative min-w-0 flex-1 rounded-lg border border-line-2 bg-panel-2/80 px-3 py-2">
        <span className="sr-only">{TRAINER_NAME} says: </span>
        {children}
      </div>
    </div>
  );
}

/** Top-bar switch: trainer voice on, or plain System mode. */
export function TrainerToggle() {
  const prefs = useOptionalPrefs();
  if (!prefs) return null;
  const on = prefs.settings.trainer !== false;
  return (
    <button
      type="button"
      onClick={() => void prefs.update({ trainer: !on })}
      aria-pressed={on}
      title={on ? `${TRAINER_NAME} speaks your insights. Click for plain mode.` : "Plain mode. Click to bring the trainer back."}
      className={`flex items-center gap-2 rounded-full border px-2 py-1 text-xs transition-colors ${on ? "border-accent/50 text-ink" : "border-line-2 text-muted hover:text-ink"}`}
    >
      <img src={TRAINER_ICON} alt="" width={22} height={22} className={`rounded-full ${on ? "" : "opacity-50 grayscale"}`} />
      Trainer
    </button>
  );
}
