/**
 * Wardrobe (v1.2): the cosmetics catalog on the Profile page. Pick a look, then an
 * outfit, weapon, relic and pet you have unlocked; locked items say how to earn them.
 * Themed (faith-flavoured) items can be hidden; the default look never uses them.
 */
import type { EarnedTitle, GameSummary } from "@ascend/shared";

import {
  SLOTS, byId, cosmeticArt, cosmeticFilter, equippedGear, isUnlocked, unlockProgress, unlockText, visibleCatalog,
  type AvatarLook, type Cosmetic, type CosmeticSlot, type Progress,
} from "../lib/cosmetics";
import { usePrefs } from "../lib/prefs";
import { Avatar } from "./Avatar";
import { useToast } from "./Toast";

export function progressFrom(game: GameSummary | null | undefined, prs: number, titles: EarnedTitle[] | null | undefined): Progress {
  return {
    rank: game?.xp.rank ?? "E",
    bestStreak: game?.streak.best ?? 0,
    sessions: game?.streak.lifetime_sessions ?? 0,
    prs,
    bossesBeaten: (titles ?? []).map((t) => t.boss),
    bossWeeks: (titles ?? []).map((t) => t.week_start).filter(Boolean),
  };
}

export function Wardrobe({ progress }: { progress: Progress }) {
  const { settings, update } = usePrefs();
  const toast = useToast();
  const look: AvatarLook = settings.avatar ?? "male";
  const themed = settings.themed_cosmetics ?? true;
  const worn: Record<CosmeticSlot, string> = {
    outfit: settings.outfit ?? "", weapon: settings.weapon ?? "", relic: settings.relic ?? "", pet: settings.pet ?? "",
  };
  const items = visibleCatalog(themed);
  const owned = items.filter((c) => isUnlocked(c, progress)).length;

  async function save(patch: Parameters<typeof update>[0]) {
    try {
      await update(patch);
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  function toggle(c: Cosmetic) {
    void save({ [c.slot]: worn[c.slot] === c.id ? "" : c.id });
  }

  function setThemed(on: boolean) {
    const off: Partial<Record<CosmeticSlot, string>> = {};
    if (!on) for (const s of SLOTS) if (byId(worn[s.key])?.themed) off[s.key] = "";
    void save({ themed_cosmetics: on, ...off });
  }

  return (
    <div className="flex flex-col gap-5 md:flex-row" data-testid="wardrobe">
      <div className="flex flex-col items-center gap-3 md:w-48">
        <Avatar look={look} rank={progress.rank} height={240} {...equippedGear(worn, { themed, progress })} />
        <div className="flex gap-1" role="radiogroup" aria-label="Avatar look">
          {(["male", "female"] as const).map((l) => (
            <button key={l} type="button" role="radio" aria-checked={look === l} onClick={() => void save({ avatar: l })}
              className={`chip ${look === l ? "border-accent text-ink" : "hover:text-ink"}`}>{l === "male" ? "Male" : "Female"}</button>
          ))}
        </div>
        <p className="text-center text-[11px] text-muted">Your rank shows as gear and aura, never as a body change.</p>
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-muted"><span className="text-ink">{owned}</span> of {items.length} unlocked</p>
          <label className="flex items-center gap-2 text-xs text-muted">
            <input type="checkbox" checked={themed} onChange={(e) => setThemed(e.target.checked)} />
            Show themed cosmetics
          </label>
        </div>
        {SLOTS.map((slot) => (
          <div key={slot.key} className="mb-4">
            <h3 className="mb-1.5 text-[11px] uppercase tracking-wider text-faint">{slot.label}</h3>
            <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
              {items.filter((c) => c.slot === slot.key).map((c) => {
                const open = isUnlocked(c, progress);
                const on = worn[c.slot] === c.id;
                const art = cosmeticArt(c.id, look);
                const tint = cosmeticFilter(c.id);
                const how = open ? null : unlockProgress(c.unlock, progress);
                return (
                  <li key={c.id}>
                    <button type="button" disabled={!open} aria-pressed={on} onClick={() => toggle(c)} data-testid={`cosmetic-${c.id}`}
                      title={open ? c.blurb : unlockText(c.unlock)} aria-label={open ? undefined : `Locked ${slot.label.toLowerCase().replace(/s$/, "")}: ${unlockText(c.unlock)}`}
                      className={`flex w-full flex-col items-center gap-1 rounded-lg border p-2 text-center transition-colors ${on ? "border-accent bg-accent/10" : "border-line-2 hover:border-line"} ${open ? "" : "opacity-60"}`}>
                      <span className="flex h-16 w-full items-center justify-center">
                        {art ? <img src={art} alt="" className="max-h-16 object-contain" data-locked={!open || undefined}
                          style={{ filter: open ? tint || undefined : "brightness(0)", opacity: open ? undefined : 0.45 }} /> : <span className="text-[10px] text-faint">Art coming</span>}
                      </span>
                      {/* D6: a locked item is a silhouette with its unlock rule, not its name. */}
                      <span className="text-xs font-medium text-ink">{open ? c.name : "???"}</span>
                      <span className="text-[10px] text-muted">{on ? "Wearing" : open ? "Unlocked" : <><span className="sr-only">How to unlock: </span>{unlockText(c.unlock)}</>}</span>
                      {how && <span className="text-[10px] tabular-nums text-faint" data-testid="unlock-progress">{how}</span>}
                      {c.themed && <span className="text-[9px] uppercase tracking-wider text-faint">Themed</span>}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
