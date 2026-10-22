/**
 * The trainer, Instructor Iskra Vey: an original character who speaks ASCEND's insights.
 * Voice rules (docs/research/v8-trainer-persona.md §2.2): second person, calls the user
 * "Hunter", fact first, stern but encouraging, never shames, no medical claims.
 *
 * Everything here is deterministic: the mood comes from the insight's kind, and the line
 * is a fixed opener + the engine's own sentence, so every number is the engine's number.
 * (A tip worded by the local model has already passed the coach's number guard.)
 * With the trainer off, the same facts show in the plain System style.
 */
import hyped from "../assets/trainer/trainer-hyped.webp";
import icon from "../assets/trainer/trainer-icon.webp";
import neutral from "../assets/trainer/trainer-neutral.webp";
import proud from "../assets/trainer/trainer-proud.webp";
import warning from "../assets/trainer/trainer-warning.webp";

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

export const moodLabel = (m: TrainerMood): string => `${TRAINER_NAME}, ${MOOD_WORDS[m]}`;

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

const CLOSERS: Record<TrainerMood, string> = {
  neutral: "",
  proud: " Keep that pace.",
  warning: " Your call, but choose on purpose.",
  hyped: " Go.",
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
  // `position` (the line's place in a list) keeps neighbouring lines from repeating an opener.
  const opener = OPENERS[mood][(pick(key, OPENERS[mood].length) + position) % OPENERS[mood].length];
  const raw = text.trim().replace(/\s+/g, " ");
  const body = /[.!?]$/.test(raw) ? raw : `${raw}.`;
  const line = `${opener} ${body}`;
  const closer = CLOSERS[mood];
  return closer && words(line) + words(closer) <= 40 ? `${line}${closer}` : line;
}

/** Digits in a string, for tests and the guard: the trainer never adds or changes one. */
export const numbersIn = (s: string): string[] => s.match(/\d+(?:[.,]\d+)?/g) ?? [];
