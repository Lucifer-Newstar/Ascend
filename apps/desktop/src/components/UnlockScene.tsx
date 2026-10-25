/**
 * Unlock scene (v1.4): a full-screen reveal for a skill step, a boss clear, a rank or a
 * cosmetic. CSS only (light rays, a burst ring and the item rising in), no video files, so
 * it costs a few hundred bytes. With Reduce motion on (OS or Settings) it is the same card
 * with no movement. Several unlocks play one after another; the Unlocks page replays any.
 */
import type { UnlockEntry, UnlockKind } from "@ascend/shared";
import { useEffect, useRef, useState } from "react";

import { bossArt } from "../lib/bosses";
import { byId, cosmeticArt, cosmeticFilter, type AvatarLook } from "../lib/cosmetics";
import { useReducedMotion } from "../lib/motion";
import { play } from "../lib/sound";
import { IconSkill } from "./Icons";
import { SystemWindow } from "./SystemWindow";
import { RankBadge } from "./XpBar";

export const KIND_LABEL: Record<UnlockKind, string> = {
  skill: "Skill acquired",
  boss: "Boss cleared",
  rank: "Rank up",
  cosmetic: "New cosmetic",
};

/** What a scene shows for an unlock: the key says which item ("cosmetic:pet_frost_cub"). */
export function SceneArt({ entry, look = "male", size = 112 }: { entry: Pick<UnlockEntry, "key" | "kind" | "title">; look?: AvatarLook; size?: number }) {
  const id = entry.key.slice(entry.key.indexOf(":") + 1);
  if (entry.kind === "rank") return <RankBadge rank={id} size={size * 0.8} />;
  const src = entry.kind === "cosmetic" ? cosmeticArt(id, look) : entry.kind === "boss" ? bossArt(id) : null;
  if (src) {
    return <img src={src} alt="" width={size} height={size} className="rounded-xl object-contain"
      style={{ width: size, height: size, filter: entry.kind === "cosmetic" ? cosmeticFilter(id) || undefined : undefined }} />;
  }
  return <span className="grid place-items-center rounded-full border-2 border-[var(--sw)] text-[var(--sw)]" style={{ width: size * 0.7, height: size * 0.7 }}><IconSkill width={size * 0.35} height={size * 0.35} /></span>;
}

export function UnlockScene({ entries, onDone, look = "male", rank }: {
  entries: Pick<UnlockEntry, "key" | "kind" | "title" | "detail">[];
  onDone: () => void;
  look?: AvatarLook;
  rank?: string | null;
}) {
  const reduce = useReducedMotion();
  const [i, setI] = useState(0);
  const button = useRef<HTMLButtonElement>(null);
  const entry = entries[i];
  useEffect(() => {
    if (entry) play(entry.kind === "skill" ? "skill" : "levelup");
  }, [entry]);
  if (!entry) return null;
  const last = i >= entries.length - 1;
  const next = () => (last ? onDone() : setI(i + 1));
  const name = entry.kind === "cosmetic" ? byId(entry.key.slice(9))?.name ?? entry.title : entry.title;
  return (
    <div data-testid="unlock-scene" data-kind={entry.kind} data-motion={reduce ? "reduced" : "full"}>
      {!reduce && (
        <div aria-hidden="true" className="unlock-stage motion-decor pointer-events-none fixed inset-0 z-50 overflow-hidden">
          <span className="unlock-rays" />
          <span className="unlock-ring" key={`ring-${i}`} />
        </div>
      )}
      <SystemWindow
        modal
        variant={entry.kind === "rank" ? "levelup" : "skill"}
        rank={rank}
        title={KIND_LABEL[entry.kind]}
        labelledBy="unlock-scene-title"
        describedBy="unlock-scene-desc"
        onClose={onDone}
        initialFocus={button}
        className="max-w-sm overflow-visible text-center"
        headerExtra={entries.length > 1 ? <span className="text-[11px] tabular-nums text-muted">{i + 1} / {entries.length}</span> : undefined}
        actions={
          <div className="flex w-full justify-center gap-2">
            {!last && <button type="button" className="btn-ghost" onClick={onDone}>Skip all</button>}
            <button ref={button} type="button" className="btn btn-primary" onClick={next}>{last ? "Continue" : "Next"}</button>
          </div>
        }
      >
        <div key={entry.key} className={`mx-auto flex justify-center ${reduce ? "" : "unlock-item"}`} aria-hidden="true">
          <SceneArt entry={entry} look={look} />
        </div>
        <p id="unlock-scene-title" className="mt-4 font-display text-[28px] font-semibold leading-8 text-ink">{name}</p>
        <p id="unlock-scene-desc" className="mt-1 text-sm text-muted">{entry.detail || KIND_LABEL[entry.kind]}</p>
      </SystemWindow>
    </div>
  );
}
