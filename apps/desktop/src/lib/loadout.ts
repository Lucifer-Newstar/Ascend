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
  rings: ["rings"],
  dumbbells: ["dumbbell"],
  gym: [],
};

/** Library equipment the player can use, or null for "no filter". */
export function allowedEquipment(choices: readonly EquipmentChoice[] | null | undefined): Set<string> | null {
  if (!choices || choices.length === 0 || choices.includes("gym")) return null;
  const out = new Set(ALWAYS);
  for (const c of choices) for (const e of BY_CHOICE[c] ?? []) out.add(e);
  return out;
}

export function fitsKit(equipment: string | null | undefined, allowed: Set<string> | null): boolean {
  return allowed === null || allowed.has(equipment || "none");
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

/** "needs: a barbell" for a move outside the loadout. */
export function needsLabel(equipment: string | null | undefined): string {
  return `needs: ${NEEDS[equipment ?? ""] ?? (equipment ?? "kit").replace(/_/g, " ")}`;
}

/** Whether the loadout has any gym kit (barbell work); without it Train opens on Calisthenics. */
export function hasGymKit(choices: readonly EquipmentChoice[] | null | undefined): boolean {
  return !choices || choices.length === 0 || choices.includes("gym") || choices.includes("dumbbells");
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
