/**
 * Level and XP in the header, on every page. When a logged set, a quest or a
 * finished workout earns XP, the bar slides forward, "+N XP" floats up, and a
 * level-up bursts a little confetti (decoration only; reduced motion hides it and
 * the new numbers simply appear).
 */
import type { XpInfo } from "@ascend/shared";

import { api } from "../api/client";
import { CountUp } from "../lib/motion";
import { useApi } from "../lib/useApi";
import { Confetti, Flash, Transient, useRise } from "./Celebrate";
import { XpFill } from "./XpBar";

export function XpChip({ refreshKey }: { refreshKey: number }) {
  const game = useApi(api.game, [refreshKey]);
  const xp: XpInfo | undefined = game.data?.xp;
  const { riseKey, delta } = useRise(xp?.total);
  const { riseKey: levelKey } = useRise(xp?.level);
  if (!xp) return null;
  const fill = Math.min(1, xp.xp_into_level / Math.max(1, xp.xp_for_next));
  return (
    <div className="relative flex items-center gap-2.5 rounded-full border border-line-2 py-1.5 pl-3 pr-3.5 text-xs" data-testid="xp-chip">
      <Transient trigger={levelKey}><Flash /><Confetti pieces={12} spread={46} /></Transient>
      <span className="font-display text-sm font-bold leading-none text-ink">LV {xp.level}</span>
      <XpFill fill={fill} className="h-1.5 w-24" sheenKey={riseKey} />
      <span className="text-muted">
        <span className="text-ink"><CountUp value={xp.xp_into_level} /></span>
        <span className="sr-only"> of {xp.xp_for_next} XP to the next level</span>
        <span aria-hidden="true"> XP</span>
      </span>
      <Transient trigger={riseKey}>
        <span aria-hidden="true" className="float-up motion-decor pointer-events-none absolute -top-2 right-3 font-semibold text-xp" data-testid="xp-gain">
          +{delta} XP
        </span>
      </Transient>
      <span role="status" className="sr-only">{levelKey > 0 ? `Level up! You reached level ${xp.level}.` : ""}</span>
    </div>
  );
}
