/**
 * The cosmetics catalog (v1.2). Outfits, relics, pets and weapons the avatar can wear,
 * each unlocked by playing: rank, sessions, PRs, weekly bosses and seasonal bosses.
 *
 * v1.3 (review decision 7): the 7/14/30-day streak unlocks became 10/25/50 lifetime
 * sessions, so a three-days-a-week plan can earn them. An old best streak still counts
 * (`legacyStreak`): nothing already earned is taken away.
 *
 * v1.4: six more items for weekly, monthly, yearly and seasonal clears, drawn as recolours of
 * existing art (`base` + `tint`, a CSS hue turn: no new image files), and a catch-up total on
 * every time-bound unlock.
 *
 * Adding an item is art plus one entry: drop `<id>.webp` (or `<id>_male.webp` and
 * `<id>_female.webp` for an outfit) into assets/cosmetics and add a line to CATALOG.
 * Items marked `themed` are faith-flavoured looks under neutral names; they are optional
 * (Settings > "Show themed cosmetics") and never the default look.
 */
export type Rank = "E" | "D" | "C" | "B" | "A" | "S";

export type CosmeticSlot = "outfit" | "relic" | "pet" | "weapon";
export type AvatarLook = "male" | "female";

/**
 * v1.4: every time-bound unlock has a catch-up path (design rule: no loss aversion). A
 * seasonal drop also comes from enough boss wins in total, and a monthly or yearly clear
 * from a larger total at any pace, so missing a week never locks an item for good.
 */
export type Unlock =
  | { kind: "start" }
  | { kind: "rank"; rank: Rank }
  | { kind: "sessions"; count: number; legacyStreak?: number }
  | { kind: "prs"; count: number }
  | { kind: "bosses"; count: number }
  | { kind: "boss"; boss: string; orWins?: number }
  | { kind: "period"; period: "month" | "year"; wins: number; orWins: number }
  | { kind: "seasonals"; count: number; orWins: number };

/** The four seasonal bosses (gamification/boss.py SEASONS), each back every year. */
export const SEASONAL_BOSSES = ["Winter Wraith", "Shadow Sovereign", "Monsoon Serpent", "Harvest Colossus"];

export interface Cosmetic {
  id: string;
  name: string;
  slot: CosmeticSlot;
  unlock: Unlock;
  blurb: string;
  /** Faith-flavoured look under a neutral name: optional, hidden when themed items are off. */
  themed?: boolean;
  /** v1.4: a recolour of another item's art (`base`), turned `tint` degrees round the colour wheel. */
  base?: string;
  tint?: number;
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
  { id: "outfit_shadow_monarch", name: "Shadow Monarch", slot: "outfit", unlock: { kind: "boss", boss: "Shadow Sovereign", orWins: 10 }, blurb: "Dropped by the Shadow Sovereign." },
  { id: "outfit_harvest_festival", name: "Harvest Festival set", slot: "outfit", unlock: { kind: "boss", boss: "Harvest Colossus", orWins: 10 }, blurb: "Festive harvest colours, dropped by the Harvest Colossus.", themed: true },
  // weapons
  { id: "weapon_shadow_dagger", name: "Shadow Dagger", slot: "weapon", unlock: { kind: "bosses", count: 1 }, blurb: "For your first boss win." },
  { id: "weapon_katana", name: "Katana", slot: "weapon", unlock: { kind: "prs", count: 10 }, blurb: "Ten personal records, one clean edge." },
  { id: "weapon_energy_gauntlet", name: "Energy Gauntlet", slot: "weapon", unlock: { kind: "boss", boss: "Monsoon Serpent", orWins: 10 }, blurb: "Storm-charged, dropped by the Monsoon Serpent." },
  { id: "weapon_spear_of_valor", name: "Spear of Valor", slot: "weapon", unlock: { kind: "sessions", count: 50, legacyStreak: 30 }, blurb: "Fifty sessions of showing up.", themed: true },
  // relics
  { id: "relic_ancient_tome", name: "Ancient Tome", slot: "relic", unlock: { kind: "prs", count: 3 }, blurb: "Your first three records, written down." },
  { id: "relic_plume_charm", name: "Plume Charm", slot: "relic", unlock: { kind: "rank", rank: "D" }, blurb: "A feather charm on a gold cord.", themed: true },
  { id: "relic_focus_charm", name: "Focus Charm", slot: "relic", unlock: { kind: "sessions", count: 25, legacyStreak: 14 }, blurb: "A flute charm with a calm blue glow.", themed: true },
  { id: "relic_monarch_ring", name: "Monarch Ring", slot: "relic", unlock: { kind: "rank", rank: "A" }, blurb: "Worn by A-rank hunters." },
  // pets
  { id: "pet_tiger_cub", name: "Tiger Cub", slot: "pet", unlock: { kind: "start" }, blurb: "Follows you from day one." },
  { id: "pet_shadow_raven", name: "Shadow Raven", slot: "pet", unlock: { kind: "bosses", count: 3 }, blurb: "Comes after three boss wins." },
  { id: "pet_spirit_wolf", name: "Spirit Wolf", slot: "pet", unlock: { kind: "boss", boss: "Winter Wraith", orWins: 10 }, blurb: "Dropped by the Winter Wraith." },
  { id: "pet_baby_dragon", name: "Baby Dragon", slot: "pet", unlock: { kind: "rank", rank: "B" }, blurb: "Hatches at rank B." },
  // v1.4: clears. Weekly, monthly, yearly and seasonal, each with a catch-up total.
  { id: "relic_ember_tome", name: "Ember Tome", slot: "relic", base: "relic_ancient_tome", tint: 300, unlock: { kind: "bosses", count: 5 }, blurb: "Five weekly bosses, written in red." },
  { id: "weapon_storm_dagger", name: "Storm Dagger", slot: "weapon", base: "weapon_shadow_dagger", tint: 190, unlock: { kind: "period", period: "month", wins: 3, orWins: 8 }, blurb: "A monthly clear, edged in blue." },
  { id: "pet_storm_raven", name: "Storm Raven", slot: "pet", base: "pet_shadow_raven", tint: 200, unlock: { kind: "period", period: "month", wins: 4, orWins: 12 }, blurb: "Every boss of a month, beaten." },
  { id: "outfit_crimson_ronin", name: "Crimson Ronin", slot: "outfit", base: "outfit_ronin", tint: 320, unlock: { kind: "period", period: "year", wins: 20, orWins: 40 }, blurb: "A year of boss fights in one coat." },
  { id: "pet_frost_cub", name: "Frost Cub", slot: "pet", base: "pet_tiger_cub", tint: 180, unlock: { kind: "seasonals", count: 1, orWins: 6 }, blurb: "For your first seasonal boss." },
  { id: "relic_season_ring", name: "Season Ring", slot: "relic", base: "relic_monarch_ring", tint: 120, unlock: { kind: "seasonals", count: 2, orWins: 15 }, blurb: "Two seasons conquered." },
];

const ART = import.meta.glob<string>("../assets/cosmetics/*.webp", { eager: true, import: "default" });
const AVATARS = import.meta.glob<string>("../assets/avatars/*.webp", { eager: true, import: "default" });

/** An item's picture: the look-specific file for outfits, else the single file; null when not drawn yet. */
export function cosmeticArt(id: string, look: AvatarLook = "male"): string | null {
  const art = byId(id)?.base ?? id;
  return ART[`../assets/cosmetics/${art}_${look}.webp`] ?? ART[`../assets/cosmetics/${art}.webp`] ?? null;
}

/** The CSS filter that recolours a v1.4 item drawn from another item's art ("" for the rest). */
export function cosmeticFilter(id: string | null | undefined): string {
  const tint = byId(id)?.tint;
  return tint ? `hue-rotate(${tint}deg) saturate(1.25)` : "";
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
  /** v1.4: each boss win's week (YYYY-MM-DD, its Monday), for monthly and yearly clears. */
  bossWeeks?: string[];
}

/** Most boss wins in one calendar month or year (by the week's Monday, local dates). */
export function bestPeriod(weeks: string[], period: "month" | "year"): number {
  const n = new Map<string, number>();
  for (const w of weeks) {
    const key = period === "month" ? w.slice(0, 7) : w.slice(0, 4);
    n.set(key, (n.get(key) ?? 0) + 1);
  }
  return Math.max(0, ...n.values());
}

const seasonalsBeaten = (p: Progress) => new Set(p.bossesBeaten.filter((b) => SEASONAL_BOSSES.includes(b))).size;

export function isUnlocked(c: Cosmetic, p: Progress): boolean {
  const u = c.unlock;
  switch (u.kind) {
    case "start": return true;
    case "rank": return RANKS.indexOf(p.rank as Rank) >= RANKS.indexOf(u.rank);
    case "sessions": return (p.sessions ?? 0) >= u.count || (u.legacyStreak !== undefined && p.bestStreak >= u.legacyStreak);
    case "prs": return p.prs >= u.count;
    case "bosses": return p.bossesBeaten.length >= u.count;
    case "boss": return p.bossesBeaten.includes(u.boss) || (u.orWins !== undefined && p.bossesBeaten.length >= u.orWins);
    case "period": return bestPeriod(p.bossWeeks ?? [], u.period) >= u.wins || p.bossesBeaten.length >= u.orWins;
    case "seasonals": return seasonalsBeaten(p) >= u.count || p.bossesBeaten.length >= u.orWins;
  }
}

/** How far along a counted unlock is ("3 of 8 boss wins"); null for the rest. */
export function unlockProgress(u: Unlock, p: Progress): string | null {
  const wins = p.bossesBeaten.length;
  switch (u.kind) {
    case "sessions": return `${Math.min(p.sessions ?? 0, u.count)} of ${u.count} sessions`;
    case "prs": return `${Math.min(p.prs, u.count)} of ${u.count} records`;
    case "bosses": return `${Math.min(wins, u.count)} of ${u.count} boss wins`;
    case "boss": return u.orWins ? `${Math.min(wins, u.orWins)} of ${u.orWins} boss wins` : null;
    case "period": return `best ${u.period}: ${Math.min(bestPeriod(p.bossWeeks ?? [], u.period), u.wins)} of ${u.wins} · total ${Math.min(wins, u.orWins)} of ${u.orWins}`;
    case "seasonals": return `${Math.min(seasonalsBeaten(p), u.count)} of ${u.count} seasonal · total ${Math.min(wins, u.orWins)} of ${u.orWins}`;
    default: return null;
  }
}

export function unlockText(u: Unlock): string {
  switch (u.kind) {
    case "start": return "Starter item";
    case "rank": return `Reach rank ${u.rank}`;
    case "sessions": return `Finish ${u.count} training sessions`;
    case "prs": return `Set ${u.count} personal record${u.count === 1 ? "" : "s"}`;
    case "bosses": return u.count === 1 ? "Beat a weekly boss" : `Beat ${u.count} weekly bosses`;
    case "boss": return u.orWins ? `Beat the ${u.boss} (back every year), or win ${u.orWins} bosses in total` : `Beat the ${u.boss}`;
    case "period": return u.period === "month"
      ? `Win ${u.wins} bosses in one month, or ${u.orWins} in total`
      : `Win ${u.wins} bosses in one year, or ${u.orWins} in total`;
    case "seasonals": return u.count === 1
      ? `Beat any seasonal boss, or win ${u.orWins} bosses in total`
      : `Beat ${u.count} different seasonal bosses, or win ${u.orWins} bosses in total`;
  }
}

export function byId(id: string | null | undefined): Cosmetic | undefined {
  return id ? CATALOG.find((c) => c.id === id) : undefined;
}

/** What a seasonal boss drops, by name ("Harvest Festival set"). */
export function dropName(id: string | null | undefined): string | null {
  return byId(id)?.name ?? null;
}

export type Gear = Partial<Record<CosmeticSlot, string>>;

/**
 * What the avatar actually wears (v1.4 rule: "cosmetics shown only when equipped"): the
 * item picked for each slot, if it is a real item for that slot, allowed by the themed
 * switch and (when progress is known) unlocked. Owned-but-unequipped items appear only in
 * the Wardrobe.
 */
export function equippedGear(worn: Gear, { themed = true, progress = null }: { themed?: boolean; progress?: Progress | null } = {}): Gear {
  const out: Gear = {};
  for (const { key } of SLOTS) {
    const c = byId(worn[key]);
    if (!c || c.slot !== key || (c.themed && !themed) || (progress && !isUnlocked(c, progress))) continue;
    out[key] = c.id;
  }
  return out;
}

/** The catalog as shown: themed items only when they are switched on. */
export function visibleCatalog(themed: boolean): Cosmetic[] {
  return CATALOG.filter((c) => themed || !c.themed);
}
