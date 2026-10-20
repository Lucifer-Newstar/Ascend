/**
 * Today's Daily Quest as a System window: each task with its progress, the time left
 * until local midnight, the reward, and "Start today's session". Training and
 * auto-tracked tasks tick themselves from logged sets; only manual tasks (a walk,
 * mobility) have a "mark done" box.
 */
import type { QuestItem } from "@ascend/shared";
import { useEffect, useState } from "react";

import { IconCheck } from "./Icons";
import { SystemWindow } from "./SystemWindow";

const KIND_LABEL: Record<QuestItem["kind"], string> = { training: "Training", nutrition: "Nutrition", recovery: "Recovery" };

/** Minutes until the next local midnight. */
export function minutesToMidnight(now: Date): number {
  const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  return Math.max(0, Math.ceil((midnight.getTime() - now.getTime()) / 60_000));
}

export function timeLeftLabel(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h} h ${m} m` : `${m} m`;
}

function useMinutesLeft(): number {
  const [mins, setMins] = useState(() => minutesToMidnight(new Date()));
  useEffect(() => {
    const t = setInterval(() => setMins(minutesToMidnight(new Date())), 30_000);
    return () => clearInterval(t);
  }, []);
  return mins;
}

/** Up to 8 blocks for the task's progress (▰▰▰▱▱), text alongside for screen readers. */
function Pips({ progress, target, done }: { progress: number; target: number; done: boolean }) {
  const n = Math.min(8, Math.max(1, target));
  const filled = done ? n : Math.round((Math.min(progress, target) / Math.max(1, target)) * n);
  return (
    <span className="flex gap-[3px]" aria-hidden="true">
      {Array.from({ length: n }, (_, i) => (
        <span key={i} className={`h-2 w-3.5 rounded-[2px] transition-colors duration-150 ${i < filled ? "bg-[var(--sw)]" : "bg-line-2"}`} />
      ))}
    </span>
  );
}

export function QuestWindow({ items, rank, onComplete, onStart }: {
  items: QuestItem[];
  rank?: string | null;
  onComplete: (id: number) => void;
  onStart?: () => void;
}) {
  const mins = useMinutesLeft();
  const done = items.filter((i) => i.completed_at).length;
  const reward = items.reduce((n, q) => n + q.xp, 0);
  const cleared = items.length > 0 && done === items.length;
  return (
    <SystemWindow variant="quest" rank={rank} title="Daily quest" testId="quest-window" className="flex h-full flex-col"
      headerExtra={<span className="text-small text-muted">{cleared ? "Cleared" : <>Time left <span className="text-ink">{timeLeftLabel(mins)}</span></>}</span>}
      actions={
        <div className="flex w-full items-center justify-between gap-3">
          <span className="text-small text-muted">{done}/{items.length} complete · Reward <span className="font-semibold text-xp">{reward} XP</span></span>
          {onStart && !cleared && <button type="button" className="btn-primary" onClick={onStart}>Start today's session</button>}
        </div>
      }>
      {items.length === 0 ? (
        <p className="text-sm text-muted">No quest issued yet. Set up your profile and the System will issue one.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((q) => {
            const complete = Boolean(q.completed_at);
            const manual = q.metric === "manual";
            return (
              <li key={q.id} className={`flex items-center gap-3 rounded-md border px-3 py-2 transition-colors duration-150 ${complete ? "border-[color-mix(in_srgb,var(--sw)_35%,transparent)] bg-[color-mix(in_srgb,var(--sw)_7%,transparent)]" : "border-line bg-panel-2/60"}`}>
                <button
                  type="button"
                  aria-label={complete ? `${q.title}: completed` : manual ? `Mark "${q.title}" done` : `${q.title}: completes automatically`}
                  disabled={complete || !manual}
                  onClick={() => onComplete(q.id)}
                  className={`grid h-6 w-6 shrink-0 place-items-center rounded-sm border transition-transform duration-150 ${complete ? "pop-in border-[var(--sw)] bg-[var(--sw)] text-on-accent" : manual ? "border-line-input hover:border-accent active:scale-90" : "border-dashed border-line-2"}`}
                >
                  {complete && <IconCheck width={14} height={14} />}
                </button>
                <div className="min-w-0 flex-1">
                  <div className={`truncate text-sm font-medium ${complete ? "text-muted line-through decoration-faint" : "text-ink"}`}>{q.title}</div>
                  <div className="truncate text-xs text-muted">{KIND_LABEL[q.kind]} · {manual ? q.detail : "auto-tracked"}</div>
                </div>
                {!manual && (
                  <span className="flex shrink-0 items-center gap-2 text-xs text-muted">
                    <Pips progress={q.progress} target={q.target} done={complete} />
                    <span className="w-12 text-right tabular-nums">{Math.min(q.progress, q.target)}/{q.target}</span>
                  </span>
                )}
                <span className="shrink-0 rounded-sm bg-xp/10 px-2 py-0.5 text-xs font-semibold text-xp">+{q.xp} XP</span>
              </li>
            );
          })}
        </ul>
      )}
    </SystemWindow>
  );
}
