/**
 * The trainer's portrait and speech bubble. The portrait crossfades between expressions
 * (opacity only; instant with Reduce motion). The image is decorative next to the words,
 * so its alt text names who is speaking and how.
 */
import { useEffect, useState, type ReactNode } from "react";

import { useReducedMotion } from "../lib/motion";
import { useOptionalPrefs } from "../lib/prefs";
import { ROSTER, moodLabel, trainerById, type TrainerMood, type TrainerProfile } from "../lib/trainer";

export function useTrainerOn(): boolean {
  return useOptionalPrefs()?.settings.trainer !== false;
}

/** The trainer the user picked (Settings, or "change trainer" in the chat). */
export function useTrainer(): TrainerProfile {
  return trainerById(useOptionalPrefs()?.settings.trainer_id);
}

export function TrainerPortrait({ mood, size = 72, className = "", trainer }: { mood: TrainerMood; size?: number; className?: string; trainer?: TrainerProfile }) {
  const chosen = useTrainer();
  const t = trainer ?? chosen;
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
      data-trainer={t.id}
    >
      {prev && <img src={t.art[prev]} alt="" className="trainer-fade-out absolute inset-0 h-full w-full object-cover object-top" />}
      <img src={t.art[shown]} alt={moodLabel(shown, t.name)} className={`absolute inset-0 h-full w-full object-cover object-top ${prev ? "trainer-fade-in" : ""}`} />
    </span>
  );
}

export function TrainerSays({ mood, children, size = 56 }: { mood: TrainerMood; children: ReactNode; size?: number }) {
  const t = useTrainer();
  return (
    <div className="flex items-start gap-3" data-testid="trainer-says">
      <TrainerPortrait mood={mood} size={size} />
      <div className="trainer-bubble relative min-w-0 flex-1 rounded-lg border border-line-2 bg-panel-2/80 px-3 py-2">
        <span className="sr-only">{t.name} says: </span>
        {children}
      </div>
    </div>
  );
}

/** Top-bar switch: trainer voice on, or plain System mode. */
export function TrainerToggle() {
  const prefs = useOptionalPrefs();
  const t = useTrainer();
  if (!prefs) return null;
  const on = prefs.settings.trainer !== false;
  return (
    <button
      type="button"
      onClick={() => void prefs.update({ trainer: !on })}
      aria-pressed={on}
      title={on ? `${t.name} speaks your insights. Click for plain mode.` : "Plain mode. Click to bring the trainer back."}
      className={`flex items-center gap-2 rounded-full border px-2 py-1 text-xs transition-colors ${on ? "border-accent/50 text-ink" : "border-line-2 text-muted hover:text-ink"}`}
    >
      <img src={t.icon} alt="" width={22} height={22} className={`rounded-full ${on ? "" : "opacity-50 grayscale"}`} />
      Trainer
    </button>
  );
}

/** Pick who speaks. Saved at once; the chat and every card switch voice and portrait. */
export function TrainerPicker({ onPicked }: { onPicked?: (t: TrainerProfile) => void }) {
  const prefs = useOptionalPrefs();
  const current = useTrainer();
  return (
    <div role="radiogroup" aria-label="Choose your trainer" className="grid grid-cols-[repeat(auto-fill,minmax(132px,1fr))] gap-3" data-testid="trainer-picker">
      {ROSTER.map((t) => {
        const on = t.id === current.id;
        return (
          <button key={t.id} type="button" role="radio" aria-checked={on} data-trainer={t.id}
            onClick={() => { void prefs?.update({ trainer_id: t.id }); onPicked?.(t); }}
            className={`flex flex-col items-center gap-2 rounded-xl border p-3 text-center transition-colors ${on ? "border-accent bg-accent/10" : "border-line-2 hover:border-accent/50"}`}>
            <TrainerPortrait mood={on ? "proud" : "neutral"} size={96} trainer={t} />
            <span className="text-sm font-semibold text-ink">{t.name}</span>
            <span className="text-[11px] uppercase tracking-wider text-accent">{t.style}</span>
            <span className="text-xs text-muted">{t.blurb}</span>
            <span className="text-[11px] text-ink">Best at: {t.specialty}</span>
          </button>
        );
      })}
    </div>
  );
}
