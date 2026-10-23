/**
 * The command bar's rule-based parser (no model involved). It turns a line like
 * "bench 80x5 @8", "plank 45s", "weight 81.4", "lunch chicken rice", "train front lever",
 * "dark" or "fuel" into a command; anything it does not recognise becomes a question
 * for the trainer (the chat). Exercise names are resolved by `rankExercises` against the library.
 */
import type { Exercise, MealType, Units } from "@ascend/shared";

import type { Page } from "../components/Layout";

export type Command =
  | { kind: "nav"; page: Page; label: string }
  | { kind: "set"; query: string; weightKg: number; reps: number; rpe: number | null; sets?: number }
  | { kind: "hold"; query: string; seconds: number; rpe: number | null }
  | { kind: "weight"; kg: number }
  | { kind: "meal"; query: string; mealType: MealType; portions?: number }
  | { kind: "train"; query: string }
  | { kind: "theme"; theme: "dark" | "light" }
  | { kind: "ai"; on: boolean }
  | { kind: "ask"; question: string };

export const PAGE_WORDS: { page: Page; label: string; words: string[] }[] = [
  { page: "dashboard", label: "Today", words: ["today", "home", "dashboard", "hq", "quest", "quests"] },
  { page: "workout", label: "Train", words: ["train", "workout", "log", "logger", "session", "gym"] },
  { page: "library", label: "Exercises", words: ["exercises", "library", "exercise"] },
  { page: "skills", label: "Skills", words: ["skills", "skill", "tree", "trees", "calisthenics"] },
  { page: "progress", label: "Progress", words: ["progress", "charts", "weight", "prs", "records"] },
  { page: "diet", label: "Fuel", words: ["fuel", "diet", "food", "meals", "nutrition", "macros"] },
  { page: "planner", label: "Planner", words: ["planner", "plan", "plans", "program", "meal plan"] },
  { page: "history", label: "History", words: ["history", "calendar", "past"] },
  { page: "data", label: "Import & export", words: ["import", "export", "data", "backup", "csv"] },
  { page: "settings", label: "Settings", words: ["settings", "preferences", "prefs", "options", "units"] },
];

const LB = 0.45359237;
const num = "(\\d+(?:[.,]\\d+)?)";
const toNum = (s: string) => Number(s.replace(",", "."));

/** Meal type from the word used, else from the time of day. */
export function mealTypeFor(word: string | undefined, hour: number): MealType {
  if (word === "breakfast" || word === "lunch" || word === "dinner" || word === "snack") return word;
  if (hour < 11) return "breakfast";
  if (hour < 15) return "lunch";
  if (hour < 21) return "dinner";
  return "snack";
}

/**
 * Every reading of `text`, best first. The question for the trainer is always last, so
 * Enter on an unrecognised line asks the trainer.
 */
export function parseCommand(text: string, units: Units, now = new Date()): Command[] {
  const t = text.trim().replace(/\s+/g, " ");
  if (!t) return [];
  const lower = t.toLowerCase();
  const out: Command[] = [];
  let m: RegExpMatchArray | null;

  // Several sets: "log 3x8 pull-up", "log 5×5 squat at 100 kg", "3x10 dips @8" (load only after "at").
  if ((m = lower.match(new RegExp(`^(?:log |add )?(\\d+) ?[x×*] ?(\\d+) ([a-z].*?)(?: at ${num} ?(kg|kgs|lb|lbs)?)?(?: ?(?:@|rpe) ?${num})?$`)))) {
    const unit = m[5] ? (m[5].startsWith("lb") ? "lb" : "kg") : units === "imperial" ? "lb" : "kg";
    const w = m[4] ? toNum(m[4]) : 0;
    out.push({ kind: "set", query: m[3], weightKg: unit === "lb" ? Math.round(w * LB * 100) / 100 : w, reps: Number(m[2]), rpe: m[6] ? toNum(m[6]) : null, sets: Number(m[1]) });
  } else if ((m = lower.match(new RegExp(`^(?:log |add )?(.+?) ${num} ?(kg|kgs|lb|lbs)? ?[x×*] ?(\\d+)(?: ?(?:@|rpe) ?${num})?$`)))) {
    const unit = m[3] ? (m[3].startsWith("lb") ? "lb" : "kg") : units === "imperial" ? "lb" : "kg";
    const w = toNum(m[2]);
    out.push({ kind: "set", query: m[1], weightKg: unit === "lb" ? Math.round(w * LB * 100) / 100 : w, reps: Number(m[4]), rpe: m[5] ? toNum(m[5]) : null });
  } else if ((m = lower.match(new RegExp(`^(?:log |add )?(.+?) (?:[x×*] ?(\\d+)|(\\d+) ?reps?)(?: ?(?:@|rpe) ?${num})?$`)))) {
    // A bodyweight set: "pull-up x8", "push-up 20 reps".
    out.push({ kind: "set", query: m[1], weightKg: 0, reps: Number(m[2] ?? m[3]), rpe: m[4] ? toNum(m[4]) : null });
  } else if ((m = lower.match(new RegExp(`^(?:log |add )?(.+?) (\\d+) ?(?:s|sec|secs|seconds)(?: ?(?:@|rpe) ?${num})?$`)))) {
    // A hold: "plank 45s", "tuck front lever 12 sec".
    out.push({ kind: "hold", query: m[1], seconds: Number(m[2]), rpe: m[3] ? toNum(m[3]) : null });
  }

  if ((m = lower.match(new RegExp(`^(?:weigh(?:ed|t|s)?|bw|body ?weight|scale) ${num} ?(kg|kgs|lb|lbs)?$`)))) {
    const unit = m[2] ? (m[2].startsWith("lb") ? "lb" : "kg") : units === "imperial" ? "lb" : "kg";
    const v = toNum(m[1]);
    out.push({ kind: "weight", kg: unit === "lb" ? Math.round(v * LB * 10) / 10 : v });
  }
  if ((m = lower.match(/^(?:(ate|eat|had|meal|breakfast|lunch|dinner|snack):? )(.+)$/))) {
    out.push({ kind: "meal", query: m[2], mealType: mealTypeFor(m[1], now.getHours()) });
  } else if ((m = lower.match(new RegExp(`^add ${num} (?:x |× )?([a-z].*)$`)))) {
    // "add 2 eggs": portions of a food, meal from the time of day.
    out.push({ kind: "meal", query: m[2], mealType: mealTypeFor(undefined, now.getHours()), portions: toNum(m[1]) });
  }
  if ((m = lower.match(/^(?:train|practi[cs]e|work on) (.+)$/))) out.push({ kind: "train", query: m[1] });
  if ((m = lower.match(/^(?:(?:theme|mode|switch to|go) )?(dark|light)(?: mode| theme)?$/))) out.push({ kind: "theme", theme: m[1] as "dark" | "light" });
  if ((m = lower.match(/^(?:turn )?ai (on|off)$/))) out.push({ kind: "ai", on: m[1] === "on" });

  // Pages: "fuel", "go to settings", "open skills".
  const navWord = lower.replace(/^(?:go(?: to)?|open|show) /, "");
  for (const p of PAGE_WORDS) {
    if (p.words.some((w) => w === navWord || (navWord.length >= 2 && w.startsWith(navWord))) || p.label.toLowerCase().startsWith(navWord)) {
      out.push({ kind: "nav", page: p.page, label: p.label });
    }
  }

  out.push({ kind: "ask", question: t });
  return out;
}

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const squash = (s: string) => norm(s).replace(/ /g, "");

/**
 * Library exercises that match `query`, best first. Exact names and aliases win, then
 * names whose words start with every query word; the curated library breaks ties
 * ahead of the large imported one, then shorter names.
 */
const ABBREV: Record<string, string> = { db: "dumbbell", bb: "barbell", kb: "kettlebell", bw: "bodyweight", ohp: "overhead press", rdl: "romanian deadlift", fl: "front lever", bl: "back lever", hs: "handstand" };

export function rankExercises(query: string, list: Exercise[], limit = 5, opts: { weighted?: boolean } = {}): Exercise[] {
  query = norm(query).split(" ").map((w) => ABBREV[w] ?? w).join(" ");
  const q = norm(query);
  if (!q) return [];
  const qs = squash(query);
  const tokens = q.split(" ");
  const scored: [number, Exercise][] = [];
  for (const e of list) {
    const names = [e.name, ...(e.aliases ?? [])];
    let best = 0;
    for (const [i, n] of names.entries()) {
      const nn = norm(n);
      const words = nn.split(" ");
      let s = 0;
      if (nn === q || squash(n) === qs) s = 100;
      else if (tokens.every((tk) => words.includes(tk))) s = 56;
      else if (squash(n).startsWith(qs)) s = 55;
      else if (tokens.every((tk) => words.some((w) => w.startsWith(tk)))) s = 50;
      else if (squash(n).includes(qs)) s = 30;
      else if (tokens.every((tk) => nn.includes(tk))) s = 20;
      if (i > 0) s -= 2; // an alias is a slightly weaker match than the name
      best = Math.max(best, s);
    }
    if (best <= 0) continue;
    const curated = e.source === "ascend" || e.source === "custom" ? 8 : 0;
    // A set with a load points at loaded equipment, not a bodyweight or timed move.
    const fit = opts.weighted === undefined ? 0 : opts.weighted === (!e.time_based && e.equipment !== "bodyweight" && e.equipment !== "none") ? 6 : -6;
    scored.push([best + curated + fit - e.name.length * 0.15, e]);
  }
  return scored.sort((a, b) => b[0] - a[0]).slice(0, limit).map(([, e]) => e);
}
