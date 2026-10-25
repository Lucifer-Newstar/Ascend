/**
 * The unlock watcher (v1.4). Lists what is unlocked right now (ranks reached, bosses
 * beaten, skill steps, cosmetics earned) and reports it to the sidecar's unlock log, which
 * keeps the date each first appeared and says which are new. New boss clears, ranks and
 * cosmetics play the full-screen unlock scene. Skill steps already have their own "Skill
 * acquired" window, so they are logged for the Unlocks page without a second scene.
 */
import type { EarnedTitle, GameSummary, SkillUnlock, UnlockEntry, UnlockItem } from "@ascend/shared";
import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import { CATALOG, isUnlocked, type Progress } from "./cosmetics";
import { useApi } from "./useApi";

const RANKS = ["E", "D", "C", "B", "A", "S"];

export function currentUnlocks({ game, prs, titles, skills }: {
  game: GameSummary;
  prs: number;
  titles: EarnedTitle[];
  skills: SkillUnlock[];
}): UnlockItem[] {
  const out: UnlockItem[] = [];
  const reached = RANKS.indexOf(game.xp.rank);
  for (const r of RANKS.slice(1, reached + 1)) out.push({ key: `rank:${r}`, kind: "rank", title: `Rank ${r}`, detail: `You reached rank ${r}.` });
  const seen = new Set<string>();
  for (const t of titles) {
    if (seen.has(t.boss)) continue;
    seen.add(t.boss);
    out.push({ key: `boss:${t.boss}`, kind: "boss", title: t.boss, detail: `Title earned: ${t.title}.` });
  }
  for (const s of skills) out.push({ key: `skill:${s.skill_key}.${s.step_key}`, kind: "skill", title: s.step_name, detail: s.skill_name });
  const progress: Progress = {
    rank: game.xp.rank, bestStreak: game.streak.best, sessions: game.streak.lifetime_sessions ?? 0, prs,
    bossesBeaten: titles.map((t) => t.boss), bossWeeks: titles.map((t) => t.week_start),
  };
  for (const c of CATALOG) {
    if (c.unlock.kind !== "start" && isUnlocked(c, progress)) out.push({ key: `cosmetic:${c.id}`, kind: "cosmetic", title: c.name, detail: c.blurb });
  }
  return out;
}

/** Report unlocks after every change and hand back the new ones to play. */
export function useUnlockWatcher(refreshKey: number): { playing: UnlockEntry[]; done: () => void } {
  const game = useApi(api.game, [refreshKey]);
  const prs = useApi(api.prs, [refreshKey]);
  const titles = useApi(api.titles, [refreshKey]);
  const skills = useApi(() => api.skillUnlocks(200), [refreshKey]);
  const [playing, setPlaying] = useState<UnlockEntry[]>([]);
  const last = useRef("");
  useEffect(() => {
    if (!game.data || !prs.data || !titles.data || !skills.data) return;
    const items = currentUnlocks({ game: game.data, prs: prs.data.length, titles: titles.data, skills: skills.data });
    const sig = items.map((i) => i.key).join("|");
    if (sig === last.current) return;
    last.current = sig;
    api.syncUnlocks(items)
      .then((r) => {
        const show = r.new.filter((u) => u.kind !== "skill");
        if (show.length) setPlaying((p) => [...p, ...show]);
      })
      .catch(() => undefined); // the log is a nicety: never block the app on it
  }, [game.data, prs.data, titles.data, skills.data]);
  return { playing, done: () => setPlaying([]) };
}
