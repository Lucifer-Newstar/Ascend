/**
 * The "Skill acquired" moment: shown when a logged set unlocks a skill-tree step.
 * A modal System window (focus moves to Continue, Tab stays inside, Esc closes).
 * With Reduce motion on (OS or Settings) it fades in without the glow or confetti.
 */
import type { SkillUnlock } from "@ascend/shared";
import { useRef } from "react";

import { useReducedMotion } from "../lib/motion";
import { Confetti } from "./Celebrate";
import { IconSkill } from "./Icons";
import { SystemWindow } from "./SystemWindow";

export function SkillAcquired({ unlocks, onClose, onView, rank }: {
  unlocks: SkillUnlock[];
  onClose: () => void;
  onView: (skillKey: string) => void;
  rank?: string | null;
}) {
  const reduce = useReducedMotion();
  const button = useRef<HTMLButtonElement>(null);
  if (unlocks.length === 0) return null;
  const [first, ...rest] = unlocks;
  const xp = unlocks.reduce((n, u) => n + u.xp, 0);
  return (
    <div data-testid="skill-acquired">
      <SystemWindow
        modal
        variant="skill"
        rank={rank}
        title={first.final ? "Skill acquired · tree complete" : "Skill acquired"}
        labelledBy="skill-acquired-title"
        describedBy="skill-acquired-desc"
        onClose={onClose}
        initialFocus={button}
        className="max-w-sm overflow-visible text-center"
        actions={
          <div className="flex w-full justify-center gap-2">
            <button type="button" className="btn-ghost" onClick={() => onView(first.skill_key)}>View tree</button>
            <button ref={button} type="button" className="btn btn-primary" onClick={onClose}>Continue</button>
          </div>
        }
      >
        {!reduce && <Confetti pieces={18} spread={110} duration={1100} />}
        <div
          className={`mx-auto grid h-14 w-14 place-items-center rounded-full border-2 border-[var(--sw)] text-[var(--sw)] ${reduce ? "" : "shadow-[0_0_28px_color-mix(in_srgb,var(--sw)_45%,transparent)]"}`}
          aria-hidden="true"
        >
          <IconSkill width={26} height={26} />
        </div>
        <p id="skill-acquired-title" className="mt-4 font-display text-[32px] font-semibold leading-9 text-ink">{first.step_name}</p>
        <p id="skill-acquired-desc" className="mt-1 text-sm text-muted">
          {first.skill_name}
          {xp > 0 ? ` · +${xp} XP` : ""}
          {first.next_step_name && !first.final ? `. Next up: ${first.next_step_name}.` : "."}
        </p>
        {rest.length > 0 && (
          <ul className="mt-3 space-y-1 text-xs text-muted">
            {rest.map((u) => <li key={u.id}>Also unlocked: <span className="text-ink">{u.step_name}</span> ({u.skill_name})</li>)}
          </ul>
        )}
      </SystemWindow>
    </div>
  );
}
