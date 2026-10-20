/**
 * The "Skill acquired" moment: shown when a logged set unlocks a skill-tree step.
 * A modal dialog (focus moves to Continue, Esc closes). With Reduce motion on (OS or
 * Settings) it appears without the pop, glow or confetti, and nothing moves.
 */
import type { SkillUnlock } from "@ascend/shared";
import { useEffect, useRef } from "react";

import { useReducedMotion } from "../lib/motion";
import { Confetti } from "./Celebrate";
import { IconSkill } from "./Icons";

export function SkillAcquired({ unlocks, onClose, onView }: { unlocks: SkillUnlock[]; onClose: () => void; onView: (skillKey: string) => void }) {
  const reduce = useReducedMotion();
  const button = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    button.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  if (unlocks.length === 0) return null;
  const [first, ...rest] = unlocks;
  const xp = unlocks.reduce((n, u) => n + u.xp, 0);
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" data-testid="skill-acquired">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="skill-acquired-title"
        aria-describedby="skill-acquired-desc"
        className="card relative w-full max-w-sm overflow-visible p-6 text-center"
        style={reduce ? undefined : { animation: "asc-pop 420ms cubic-bezier(0.2, 0.9, 0.3, 1.2) both" }}
        data-motion={reduce ? "reduced" : "full"}
      >
        <Confetti pieces={18} spread={110} duration={1100} />
        <div
          className={`mx-auto grid h-14 w-14 place-items-center rounded-full border-2 border-xp text-xp ${reduce ? "" : "shadow-[0_0_28px_color-mix(in_srgb,var(--color-xp)_45%,transparent)]"}`}
          aria-hidden="true"
        >
          <IconSkill width={26} height={26} />
        </div>
        <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.25em] text-xp">{first.final ? "Skill acquired · tree complete" : "Skill acquired"}</p>
        <h2 id="skill-acquired-title" className="mt-1 font-display text-2xl font-bold text-ink">{first.step_name}</h2>
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
        <div className="mt-5 flex justify-center gap-2">
          <button type="button" className="btn-ghost" onClick={() => onView(first.skill_key)}>View tree</button>
          <button ref={button} type="button" className="btn btn-primary" onClick={onClose}>Continue</button>
        </div>
      </div>
    </div>
  );
}
