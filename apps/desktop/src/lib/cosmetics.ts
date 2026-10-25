/**
 * The cosmetics catalog (v1.2). Outfits, relics, pets and weapons the avatar can wear,
 * each unlocked by playing: rank, sessions, PRs, weekly bosses and seasonal bosses.
 *
 * v1.3 (review decision 7): the 7/14/30-day streak unlocks became 10/25/50 lifetime
 * sessions, so a three-days-a-week plan can earn them. An old best streak still counts
 * (`legacyStreak`): nothing already earned is taken away.
 *
 * Adding an item is art plus one entry: drop `<id>.webp` (or `<id>_male.webp` and
 * `<id>_female.webp` for an outfit) into assets/cosmetics and add a line to CATALOG.
 * Items marked `themed` are faith-flavoured looks under neutral names; they are optional
 * (Settings > "Show themed cosmetics") and never the default look.
 */
export type Rank = "E" | "D" | "C" | "B" | "A" | "S";

export type CosmeticSlot = "outfit" | "relic" | "pet" | "weapon";
export type AvatarLook = "male" | "female";

export type Unlock =
  | { kind: "start" }
  | { kind: "rank"; rank: Rank }
  | { kind: "sessions"; count: number; legacyStreak?: number }
  | { kind: "prs"; count: number }
  | { kind: "bosses"; count: number }
  | { kind: "boss"; boss: string };

export interface Cosmetic {
  id: string;
  name: string;
  slot: CosmeticSlot;
  unlock: Unlock;
  blurb: string;
  /** Faith-flavoured look under a neutral name: optional, hidden when themed items are off. */
  themed?: boolean;
}

export const SLOTS: { key: CosmeticSlot; label: string }[] = [
  { key: "outfit", label: "Outfits" },
  { key: "weapon", label: "Weapons" },
  { key: "relic", label: "Relics" },
  { key: "pet", label: "Pets" },
];

export const CATALOG: Cosmetic[] = [
  // outfits (4 sets + the Harvest Festival set from its seasonal boss)
  { id: "outfit_cyber_hunter", name: "Cyber Hunter", slot: "outfit", unlock: { kind: "start" }, blurb: "Neon-lined field gear. Yours from day one." },
  { id: "outfit_ronin", name: "Ronin", slot: "outfit", unlock: { kind: "sessions", count: 10, legacyStreak: 7 }, blurb: "A wanderer's coat for your first ten sessions." },
  { id: "outfit_celestial_warrior", name: "Celestial Warrior", slot: "outfit", unlock: { kind: "rank", rank: "C" }, blurb: "Gold and starlight armour.", themed: true },
  { id: "outfit_shadow_monarch", name: "Shadow Monarch", slot: "outfit", unlock: { kind: "boss", boss: "Shadow Sovereign" }, blurb: "Dropped by the Shadow Sovereign." },
  { id: "outfit_harvest_festival", name: "Harvest Festival set", slot: "outfit", unlock: { kind: "boss", boss: "Harvest Colossus" }, blurb: "Festive harvest colours, dropped by the Harvest Colossus.", themed: true },
  // weapons
  { id: "weapon_shadow_dagger", name: "Shadow Dagger", slot: "weapon", unlock: { kind: "bosses", count: 1 }, blurb: "For your first boss win." },
  { id: "weapon_katana", name: "Katana", slot: "weapon", unlock: { kind: "prs", count: 10 }, blurb: "Ten personal records, one clean edge." },
  { id: "weapon_energy_gauntlet", name: "Energy Gauntlet", slot: "weapon", unlock: { kind: "boss", boss: "Monsoon Serpent" }, blurb: "Storm-charged, dropped by the Monsoon Serpent." },
  { id: "weapon_spear_of_valor", name: "Spear of Valor", slot: "weapon", unlock: { kind: "sessions", count: 50, legacyStreak: 30 }, blurb: "Fifty sessions of showing up.", themed: true },
  // relics
  { id: "relic_ancient_tome", name: "Ancient Tome", slot: "relic", unlock: { kind: "prs", count: 3 }, blurb: "Your first three records, written down." },
  { id: "relic_plume_charm", name: "Plume Charm", slot: "relic", unlock: { kind: "rank", rank: "D" }, blurb: "A feather charm on a gold cord.", themed: true },
  { id: "relic_focus_charm", name: "Focus Charm", slot: "relic", unlock: { kind: "sessions", count: 25, legacyStreak: 14 }, blurb: "A flute charm with a calm blue glow.", themed: true },
  { id: "relic_monarch_ring", name: "Monarch Ring", slot: "relic", unlock: { kind: "rank", rank: "A" }, blurb: "Worn by A-rank hunters." },
  // pets
  { id: "pet_tiger_cub", name: "Tiger Cub", slot: "pet", unlock: { kind: "start" }, blurb: "Follows you from day one." },
  { id: "pet_shadow_raven", name: "Shadow Raven", slot: "pet", unlock: { kind: "bosses", count: 3 }, blurb: "Comes after three boss wins." },
  { id: "pet_spirit_wolf", name: "Spirit Wolf", slot: "pet", unlock: { kind: "boss", boss: "Winter Wraith" }, blurb: "Dropped by the Winter Wraith." },
  { id: "pet_baby_dragon", name: "Baby Dragon", slot: "pet", unlock: { kind: "rank", rank: "B" }, blurb: "Hatches at rank B." },
];

const ART = import.meta.glob<string>("../assets/cosmetics/*.webp", { eager: true, import: "default" });
const AVATARS = import.meta.glob<string>("../assets/avatars/*.webp", { eager: true, import: "default" });

/** An item's picture: the look-specific file for outfits, else the single file; null when not drawn yet. */
export function cosmeticArt(id: string, look: AvatarLook = "male"): string | null {
  return ART[`../assets/cosmetics/${id}_${look}.webp`] ?? ART[`../assets/cosmetics/${id}.webp`] ?? null;
}

const RANKS: Rank[] = ["E", "D", "C", "B", "A", "S"];
/** The avatar's art for a rank: four drawn stages (E, C, A, S); D shares E's, B shares C's. */
export function avatarArt(look: AvatarLook, rank: string): string | null {
  const stages: Record<string, string> = { E: "e", D: "e", C: "c", B: "c", A: "a", S: "s" };
  const stage = stages[rank] ?? "e";
  return AVATARS[`../assets/avatars/${look}-${stage}.webp`] ?? null;
}

export interface Progress {
  rank: string;
  bestStreak: number;
  /** v1.3: lifetime training sessions (never goes down). */
  sessions?: number;
  prs: number;
  bossesBeaten: string[];
}

export function isUnlocked(c: Cosmetic, p: Progress): boolean {
  const u = c.unlock;
  switch (u.kind) {
    case "start": return true;
    case "rank": return RANKS.indexOf(p.rank as Rank) >= RANKS.indexOf(u.rank);
    case "sessions": return (p.sessions ?? 0) >= u.count || (u.legacyStreak !== undefined && p.bestStreak >= u.legacyStreak);
    case "prs": return p.prs >= u.count;
    case "bosses": return p.bossesBeaten.length >= u.count;
    case "boss": return p.bossesBeaten.includes(u.boss);
  }
}

export function unlockText(u: Unlock): string {
  switch (u.kind) {
    case "start": return "Starter item";
    case "rank": return `Reach rank ${u.rank}`;
    case "sessions": return `Finish ${u.count} training sessions`;
    case "prs": return `Set ${u.count} personal record${u.count === 1 ? "" : "s"}`;
    case "bosses": return u.count === 1 ? "Beat a weekly boss" : `Beat ${u.count} weekly bosses`;
    case "boss": return `Beat the ${u.boss}`;
  }
}

export function byId(id: string | null | undefined): Cosmetic | undefined {
  return id ? CATALOG.find((c) => c.id === id) : undefined;
}

/** What a seasonal boss drops, by name ("Harvest Festival set"). */
export function dropName(id: string | null | undefined): string | null {
  return byId(id)?.name ?? null;
}

/** The catalog as shown: themed items only when they are switched on. */
export function visibleCatalog(themed: boolean): Cosmetic[] {
  return CATALOG.filter((c) => themed || !c.themed);
}
