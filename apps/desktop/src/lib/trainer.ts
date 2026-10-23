/**
 * The trainers: Instructor Iskra Vey (the default) and, from v1.1, Vera Kestrine, Kai
 * Hoshimura and Dario Halvorn. All original characters (art provenance in
 * assets/trainer/ART_PROVENANCE.md). One trainer speaks at a time; they all read the same
 * numbers, only the voice and the portrait change. The original notes on Iskra follow.
 * Voice rules (docs/research/v8-trainer-persona.md §2.2): second person, calls the user
 * "Hunter", fact first, stern but encouraging, never shames, no medical claims.
 *
 * Everything here is deterministic: the mood comes from the insight's kind, and the line
 * is a fixed opener + the engine's own sentence, so every number is the engine's number.
 * (A tip worded by the local model has already passed the coach's number guard.)
 * With the trainer off, the same facts show in the plain System style.
 */
import type { TrainerId } from "@ascend/shared";

import darioHyped from "../assets/trainer/dario-hyped.webp";
import darioIcon from "../assets/trainer/dario-icon.webp";
import darioNeutral from "../assets/trainer/dario-neutral.webp";
import darioProud from "../assets/trainer/dario-proud.webp";
import darioWarning from "../assets/trainer/dario-warning.webp";
import kaiHyped from "../assets/trainer/kai-hyped.webp";
import kaiIcon from "../assets/trainer/kai-icon.webp";
import kaiNeutral from "../assets/trainer/kai-neutral.webp";
import kaiProud from "../assets/trainer/kai-proud.webp";
import kaiWarning from "../assets/trainer/kai-warning.webp";
import hyped from "../assets/trainer/trainer-hyped.webp";
import icon from "../assets/trainer/trainer-icon.webp";
import neutral from "../assets/trainer/trainer-neutral.webp";
import proud from "../assets/trainer/trainer-proud.webp";
import warning from "../assets/trainer/trainer-warning.webp";
import veraHyped from "../assets/trainer/vera-hyped.webp";
import veraIcon from "../assets/trainer/vera-icon.webp";
import veraNeutral from "../assets/trainer/vera-neutral.webp";
import veraProud from "../assets/trainer/vera-proud.webp";
import veraWarning from "../assets/trainer/vera-warning.webp";

export type TrainerMood = "neutral" | "proud" | "warning" | "hyped";

export const TRAINER_NAME = "Instructor Iskra Vey";
export const TRAINER_SHORT = "Iskra";
export const TRAINER_ICON = icon;
export const TRAINER_ART: Record<TrainerMood, string> = { neutral, proud, warning, hyped };

const MOOD_WORDS: Record<TrainerMood, string> = {
  neutral: "calm",
  proud: "proud",
  warning: "stern",
  hyped: "fired up",
};

export const moodLabel = (m: TrainerMood, name: string = TRAINER_NAME): string => `${name}, ${MOOD_WORDS[m]}`;

export interface TrainerProfile {
  id: TrainerId;
  name: string;
  short: string;
  style: string;
  blurb: string;
  icon: string;
  art: Record<TrainerMood, string>;
}

/** The roster, in picker order. Same numbers and rules for all; only voice and art differ. */
export const ROSTER: TrainerProfile[] = [
  { id: "iskra", name: TRAINER_NAME, short: TRAINER_SHORT, style: "Stern drill instructor",
    blurb: "Fact first, stern but fair. Celebrates hard when you earn it.", icon, art: TRAINER_ART },
  { id: "vera", name: "Vera Kestrine", short: "Vera", style: "Playful hype coach",
    blurb: "Teasing but kind. Keeps it light and keeps you moving.", icon: veraIcon,
    art: { neutral: veraNeutral, proud: veraProud, warning: veraWarning, hyped: veraHyped } },
  { id: "kai", name: "Kai Hoshimura", short: "Kai", style: "High-energy hype-man",
    blurb: "Big energy, loud cheers, straight talk when it matters.", icon: kaiIcon,
    art: { neutral: kaiNeutral, proud: kaiProud, warning: kaiWarning, hyped: kaiHyped } },
  { id: "dario", name: "Dario Halvorn", short: "Dario", style: "Calm strategist",
    blurb: "Quiet, tactical, long-game. Explains the why behind the plan.", icon: darioIcon,
    art: { neutral: darioNeutral, proud: darioProud, warning: darioWarning, hyped: darioHyped } },
];

export function trainerById(id: string | null | undefined): TrainerProfile {
  return ROSTER.find((t) => t.id === id) ?? ROSTER[0];
}

/** Kinds of thing the trainer can say, mapped to an expression (persona §2.3). */
const WARNING = /deload|over|overreach|recovering|shortfall|deficit|low_protein|too_fast|too_slow|plateau|stall|under_eat|missed|drop/i;
const PROUD = /pr\b|record|streak|clear|complete|adherence|on_track|consistent|good|gain|improv|raised/i;
const HYPED = /level|rank|boss|comeback|ready|recovered|unlock/i;

export function moodFor(code: string, severity = 0): TrainerMood {
  if (WARNING.test(code) || severity >= 3) return "warning";
  if (HYPED.test(code)) return "hyped";
  if (PROUD.test(code)) return "proud";
  return "neutral";
}

const OPENERS: Record<TrainerMood, string[]> = {
  neutral: ["Hunter, here is the read.", "Listen up, Hunter.", "Status report, Hunter."],
  proud: ["Good work, Hunter.", "That is earned, Hunter.", "Noted, Hunter. Well done."],
  warning: ["Hunter, eyes on this.", "Careful, Hunter.", "Hold up, Hunter."],
  hyped: ["Now we move, Hunter!", "This is it, Hunter!", "Up and at it, Hunter!"],
};

const CLOSERS: Record<TrainerMood, string[]> = {
  neutral: [""],
  proud: [" Keep that pace.", " Hold that standard.", " More of this."],
  warning: [" Your call, but choose on purpose.", " Plan around it.", " Adjust, then train."],
  hyped: [" Go.", " Move.", " Make it count."],
};

/** A small stable hash, so the same insight always gets the same opener. */
function pick(key: string, n: number): number {
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return h % n;
}

const words = (s: string) => s.trim().split(/\s+/).filter(Boolean).length;

/**
 * The trainer's line for an engine sentence. The sentence is kept word for word; the
 * opener and closer add no numbers. The closer is left out when the line would pass 40 words.
 */
export function trainerLine(key: string, text: string, mood: TrainerMood, position = 0): string {
  // `position` (the line's place in a list) keeps neighbouring lines from repeating an opener
  // or a closer.
  const opener = OPENERS[mood][(pick(key, OPENERS[mood].length) + position) % OPENERS[mood].length];
  const raw = text.trim().replace(/\s+/g, " ");
  const body = /[.!?]$/.test(raw) ? raw : `${raw}.`;
  const line = `${opener} ${body}`;
  const closers = CLOSERS[mood];
  const closer = closers[(pick(key, closers.length) + position) % closers.length];
  return closer && words(line) + words(closer) <= 40 ? `${line}${closer}` : line;
}

/** Digits in a string, for tests and the guard: the trainer never adds or changes one. */
export const numbersIn = (s: string): string[] => s.match(/\d+(?:[.,]\d+)?/g) ?? [];
