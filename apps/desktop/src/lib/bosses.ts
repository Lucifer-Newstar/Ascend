/**
 * Boss portraits (v1.1), one per boss in boss-v1's rotation. Original art; provenance in
 * assets/trainer/ART_PROVENANCE.md. A boss without art (a name added later) falls back to
 * the crest.
 *
 * v1.4: CATEGORY_LABEL moved here from the old boss ladder (Profile now has a trophy shelf).
 */
import type { BossCategory } from "@ascend/shared";

export const CATEGORY_LABEL: Record<BossCategory, string> = {
  strength: "Strength",
  calisthenics: "Calisthenics",
  cardio: "Cardio",
  martial_arts: "Martial arts",
};

const art = import.meta.glob<string>("../assets/bosses/*.webp", { eager: true, import: "default" });

export const bossSlug = (name: string): string => name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export function bossArt(name: string): string | null {
  return art[`../assets/bosses/${bossSlug(name)}.webp`] ?? null;
}
