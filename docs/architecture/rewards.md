# Rewards: trophy shelf, cosmetics and unlock scenes (v1.4)

> Owner: **Navin**. Code: `apps/desktop/src/lib/cosmetics.ts`, `lib/unlocks.ts`,
> `components/TrophyShelf.tsx`, `components/UnlockScene.tsx`, `pages/Unlocks.tsx` (Dhanush);
> the unlock log `services/sidecar/app/modules/gamification/unlocks.py` (Jegatheesan).
> Asked for by Navin on 2026-10-25 (5:20 PM); checked against the design rules in
> [RULES_AND_BASELINE.md](../RULES_AND_BASELINE.md).

## What changed for the player

| Ask | What it is now |
|---|---|
| Profile: no full boss ladder | A **trophy shelf**: only the bosses you cleared (how often, when you last won), then this week's boss as a "???" silhouette with its tier, category and how to unlock it. |
| Seasonal boss from the local date | The sidecar's clock was already the PC's local wall clock; tests now cross local midnight. The desktop's two UTC dates (photo date, weekly recap) are fixed, and the Harvest Colossus's drop now points at the real cosmetic. |
| Avatar picture bug | The Hunter card drew the trainer's portrait until the game summary loaded, so your look seemed not to apply. It always draws your avatar now. |
| Only equipped cosmetics | `equippedGear()` keeps the item picked for each slot only if it is real, allowed by the themed switch and earned. Owned items appear only in the Wardrobe. |
| More cosmetics, with catch-up | Six new items for weekly, monthly, yearly and seasonal clears (below). Every time-bound unlock also opens from a total at any pace. |
| Unlock cutscenes and a page | A full-screen CSS reveal for boss clears, ranks and cosmetics (skill steps keep their own window), and an **Unlocks** page (Profile > Achievements > All unlocks) with dates and Replay. |

## The new cosmetics

All are recolours of existing art: the same picture turned round the colour wheel with a CSS
`hue-rotate`, so there are no new image files.

| Item | Slot | Clear | Catch-up |
|---|---|---|---|
| Ember Tome | relic | 5 weekly bosses | (already a total) |
| Storm Dagger | weapon | 3 boss wins in one calendar month | 8 in total |
| Storm Raven | pet | 4 boss wins in one month | 12 in total |
| Crimson Ronin | outfit | 20 boss wins in one calendar year | 40 in total |
| Frost Cub | pet | any seasonal boss | 6 in total |
| Season Ring | relic | 2 different seasonal bosses | 15 in total |

The four seasonal drops (Spirit Wolf, Shadow Monarch, Energy Gauntlet, Harvest Festival set)
also open at 10 boss wins in total, and their bosses come back every year.

## The unlock log

`unlock_events` (migration 0033) keeps each unlock's first date. The desktop reports what is
unlocked after every refresh (`POST /game/unlocks/sync`); keys not seen before come back as
`new` and play their scene. The very first sync is recorded quietly (`seeded`), so updating
the app does not replay a year of unlocks; the page shows those as "by <date>".

## Design check

| Rule | How it holds |
|---|---|
| D1 cosmetic, tied to effort | Every item comes from training: sessions, records, boss wins. Nothing is bought or random. |
| D2 no FOMO | Every time-bound unlock has a catch-up total (R19), and seasonal bosses return each year. |
| D6 no spoilers, clear how to unlock | Trophy shelf plus "???", Wardrobe silhouettes, and season names instead of boss names (R18). |
| D8 motion optional | The scene is a still card with Reduce motion on (OS or Settings). |
| D10 viva-safe art | Recolours of the shipped art only. |
| D11 no new page | The Unlocks page is the one exception, because Navin asked for it by name. It has no nav entry and opens from Profile. |
