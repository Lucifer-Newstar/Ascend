/**
 * The loadout (v1.2): the kit chosen at setup drives what the app shows. The same rules
 * as the sidecar's workouts/equipment.py: an empty checklist or "gym" filters nothing;
 * otherwise floor moves always fit, plus what each piece of kit adds. Lists show the moves
 * that fit, and "Explore all" shows the rest greyed out with what they need.
 */
import type { EquipmentChoice } from "@ascend/shared";

import { api } from "../api/client";
import { useApi } from "./useApi";

const ALWAYS = ["bodyweight", "none", "mat"];
const BY_CHOICE: Record<EquipmentChoice, string[]> = {
  none: [],
  pullup_bar: ["bar"],
  // v1.3: rings hang where a bar does, so bar moves (pull-ups, hangs) fit too
  rings: ["rings", "bar"],
  dumbbells: ["dumbbell"],
  bench: ["bench"],
  gym: [],
};
/** Moves that need a bench whatever their library equipment says (same list as the sidecar). */
const NEEDS_BENCH = /\b(bench press|incline (?:dumbbell|barbell|bench)|decline|chest fly(?:e)?s?|dumbbell flyes?|hip thrust|pullover|preacher)\b/i;

export function needsBench(name: string | null | undefined): boolean {
  return !!name && NEEDS_BENCH.test(name);
}

/** Library equipment the player can use, or null for "no filter". */
export function allowedEquipment(choices: readonly EquipmentChoice[] | null | undefined): Set<string> | null {
  if (!choices || choices.length === 0 || choices.includes("gym")) return null;
  const out = new Set(ALWAYS);
  for (const c of choices) for (const e of BY_CHOICE[c] ?? []) out.add(e);
  return out;
}

export function fitsKit(equipment: string | null | undefined, allowed: Set<string> | null, name?: string): boolean {
  if (allowed === null) return true;
  if (needsBench(name) && !allowed.has("bench")) return false;
  return allowed.has(equipment || "none");
}

const NEEDS: Record<string, string> = {
  bar: "a pull-up bar",
  rings: "rings",
  dumbbell: "dumbbells",
  barbell: "a barbell",
  ez_bar: "an EZ bar",
  cable: "a cable machine",
  machine: "a machine",
  kettlebell: "a kettlebell",
  band: "a band",
  medicine_ball: "a medicine ball",
  exercise_ball: "an exercise ball",
  foam_roller: "a foam roller",
  other: "extra kit",
};

/** "needs: a barbell" for a move outside the loadout ("needs: a bench" for a bench press). */
export function needsLabel(equipment: string | null | undefined, name?: string, allowed?: Set<string> | null): string {
  if (needsBench(name) && allowed && !allowed.has("bench") && allowed.has(equipment || "none")) return "needs: a bench";
  return `needs: ${NEEDS[equipment ?? ""] ?? (equipment ?? "kit").replace(/_/g, " ")}`;
}

/** Whether the loadout has any gym kit (barbell work); without it Train opens on Calisthenics. */
export function hasGymKit(choices: readonly EquipmentChoice[] | null | undefined): boolean {
  return !choices || choices.length === 0 || choices.includes("gym") || choices.includes("dumbbells");
}

export interface HunterClass {
  name: "Home Hunter" | "Bar Ronin" | "Calisthenics Ronin" | "Iron Duelist" | "Iron Lifter";
  blurb: string;
}

/**
 * Your class, from your kit (v1.2): a full gym makes an Iron Lifter, dumbbells an Iron
 * Duelist, rings a Calisthenics Ronin, a pull-up bar a Bar Ronin, and nothing at all a
 * Home Hunter. Add kit later and the class (and what the app shows) grows with it.
 */
export function hunterClass(choices: readonly EquipmentChoice[] | null | undefined): HunterClass {
  const c = new Set(choices ?? []);
  if (c.has("gym")) return { name: "Iron Lifter", blurb: "Barbells, machines and everything else." };
  if (c.has("dumbbells")) return { name: "Iron Duelist", blurb: "Dumbbell strength plus body weight." };
  if (c.has("rings")) return { name: "Calisthenics Ronin", blurb: "Rings and body weight." };
  if (c.has("pullup_bar")) return { name: "Bar Ronin", blurb: "A pull-up bar and the floor." };
  return { name: "Home Hunter", blurb: "No kit needed: floor and body weight." };
}

export interface Loadout {
  /** null until the profile has loaded (or when there is none). */
  choices: EquipmentChoice[] | null;
  allowed: Set<string> | null;
  loaded: boolean;
}

/** The player's loadout from the profile (no profile = no filter). */
export function useLoadout(): Loadout {
  const p = useApi(() => Promise.resolve().then(() => api.profile()).catch(() => null), [], { cacheKey: "profile-loadout" });
  const choices = p.data?.equipment ?? null;
  return { choices, allowed: allowedEquipment(choices), loaded: !p.loading };
}
