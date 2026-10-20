import type { StreakInfo, XpInfo } from "@ascend/shared";

import { IconFlame, IconSnow } from "./Icons";

export const RANK_COLORS: Record<string, string> = {
  E: "#94a3b8",
  D: "#4ade80",
  C: "#22d3ee",
  B: "#818cf8",
  A: "#f59e0b",
  S: "#f43f5e",
};

export function RankBadge({ rank, size = 44 }: { rank: string; size?: number }) {
  const color = RANK_COLORS[rank] ?? "#94a3b8";
  return (
    <div className="grid shrink-0 place-items-center rounded-lg border font-display font-bold"
      style={{ width: size, height: size, borderColor: `${color}66`, color, background: `${color}14`, fontSize: size * 0.55 }}>
      {rank}
    </div>
  );
}

export function XpBar({ xp, streak }: { xp: XpInfo; streak: StreakInfo }) {
  const p = Math.min(1, xp.xp_into_level / xp.xp_for_next);
  return (
    <div className="flex items-center gap-4">
      <RankBadge rank={xp.rank} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <div className="flex items-baseline gap-2">
            <span className="font-display text-2xl font-bold leading-none text-ink">LV {xp.level}</span>
            <span className="text-xs text-muted">Rank {xp.rank} · {xp.rank_title}</span>
          </div>
          <span className="text-xs text-muted">
            <span className="text-ink">{xp.xp_into_level.toLocaleString()}</span> / {xp.xp_for_next.toLocaleString()} XP
          </span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-xp/15">
          <div className="h-full rounded-full bg-xp shadow-[0_0_10px_rgba(139,124,255,0.6)]" style={{ width: `${p * 100}%`, transition: "width 600ms ease" }} />
        </div>
        <div className="mt-2 flex gap-4 text-xs text-muted">
          <span>+{xp.today} XP today <span className="text-faint">(cap {xp.daily_cap})</span></span>
          <span className="flex items-center gap-1"><IconFlame width={14} height={14} className="text-warn" /> {streak.current}-day streak</span>
          <span className="flex items-center gap-1" title="Earn 1 freeze per 7-day streak (max 2); used automatically on a missed day">
            <IconSnow width={14} height={14} className="text-accent" /> {streak.freezes_held} freeze{streak.freezes_held === 1 ? "" : "s"}
          </span>
        </div>
      </div>
    </div>
  );
}
