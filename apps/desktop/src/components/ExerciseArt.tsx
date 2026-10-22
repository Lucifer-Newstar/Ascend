/**
 * The picture for an exercise. Library entries show their bundled photo (free-exercise-db,
 * public domain); everything else (custom exercises, curated skills with no photo, or a
 * file that fails to load) gets a designed tile built from the section and the main
 * muscles, so no card ever shows an empty box.
 */
import { useState, type ReactNode } from "react";
import type { Exercise, Section } from "@ascend/shared";

import { muscleLabel } from "../lib/muscles";

type ArtExercise = Pick<Exercise, "image" | "name" | "section"> & { muscles?: Exercise["muscles"] };

const SECTION_HUE: Record<Section, string> = {
  gym: "var(--color-accent)",
  calisthenics: "var(--color-xp)",
  cardio: "var(--color-ring-out)",
  flexibility: "var(--color-good)",
  martial_arts: "var(--color-bad)",
  meditation: "var(--color-under)",
};

const SECTION_NAME: Record<Section, string> = {
  gym: "Strength",
  calisthenics: "Calisthenics",
  cardio: "Cardio",
  flexibility: "Mobility",
  martial_arts: "Martial arts",
  meditation: "Mind",
};

const stroke = { fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round" } as const;

/** Simple line glyphs, one per section (original drawings). */
const GLYPH: Record<Section, ReactNode> = {
  gym: (
    <g {...stroke}>
      <path d="M4 12h16M6.5 8v8M17.5 8v8M3 10v4M21 10v4" />
    </g>
  ),
  calisthenics: (
    <g {...stroke}>
      <path d="M4 5h16" />
      <circle cx="12" cy="9" r="1.6" />
      <path d="M8 5l2.5 6.5h3L16 5M10.5 11.5L10 19M13.5 11.5L14 19" />
    </g>
  ),
  cardio: (
    <g {...stroke}>
      <path d="M12 20s-7-4.4-7-9.6A3.9 3.9 0 0 1 12 8a3.9 3.9 0 0 1 7 2.4C19 15.6 12 20 12 20Z" />
      <path d="M6.5 13h3l1.5-2.5 2 4 1.5-1.5h3" />
    </g>
  ),
  flexibility: (
    <g {...stroke}>
      <circle cx="16.5" cy="5.5" r="1.6" />
      <path d="M15.5 8l-4 5 4.5 1.5L19 19M11.5 13L5 17M15.5 8L19 10.5" />
    </g>
  ),
  martial_arts: (
    <g {...stroke}>
      <path d="M7 11V7.5a1.5 1.5 0 0 1 3 0V10m0-2.5a1.5 1.5 0 0 1 3 0V10m0-1.5a1.5 1.5 0 0 1 3 0V12a6 6 0 0 1-6 6H9.5A2.5 2.5 0 0 1 7 15.5V11a1.5 1.5 0 0 0-1.5 1.5" />
    </g>
  ),
  meditation: (
    <g {...stroke}>
      <circle cx="12" cy="6" r="1.8" />
      <path d="M12 8.5v5M7 11.5l5 2 5-2M5 17.5c2.5-1.8 4.6-2.2 7-2.2s4.5.4 7 2.2" />
    </g>
  ),
};

function mainMuscles(e: ArtExercise): string[] {
  return (e.muscles ?? [])
    .filter((m) => m.weight >= 1)
    .slice(0, 2)
    .map((m) => muscleLabel(m.muscle));
}

/** The designed tile used when an exercise has no photo. */
export function ExerciseTile({ exercise: e, className = "" }: { exercise: ArtExercise; className?: string }) {
  const hue = SECTION_HUE[e.section] ?? SECTION_HUE.gym;
  const muscles = mainMuscles(e);
  return (
    <div
      aria-hidden
      data-testid="exercise-tile"
      className={`exercise-tile relative w-full overflow-hidden ${className}`}
      style={{ ["--tile-hue" as string]: hue }}
    >
      <svg viewBox="0 0 24 24" className="absolute left-1/2 top-[42%] h-[52%] -translate-x-1/2 -translate-y-1/2" style={{ color: hue }}>
        {GLYPH[e.section] ?? GLYPH.gym}
      </svg>
      <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-2 px-2.5 pb-2">
        <span className="truncate font-display text-[11px] font-bold uppercase tracking-[0.12em] text-ink/90">
          {muscles.length ? muscles.join(" · ") : SECTION_NAME[e.section]}
        </span>
      </div>
    </div>
  );
}

/** Photo when there is one (and it loads), otherwise the designed tile. */
export function ExerciseArt({ exercise, className = "" }: { exercise: ArtExercise; className?: string }) {
  const [broken, setBroken] = useState(false);
  if (exercise.image && !broken) {
    return (
      <img
        src={exercise.image}
        alt=""
        loading="lazy"
        decoding="async"
        data-testid="exercise-photo"
        onError={() => setBroken(true)}
        className={`w-full bg-white object-contain ${className}`}
      />
    );
  }
  return <ExerciseTile exercise={exercise} className={className} />;
}
