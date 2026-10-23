/**
 * The program card on Train (programs-v1, ADR-0020): the next session of the program the
 * user follows, with prog-v1's target per exercise and the sets already done today, or a
 * chooser when no program is followed. Picking an exercise opens it in the logger.
 */
import type { Plan, PlanItem, ProgramSummary } from "@ascend/shared";
import { useState } from "react";

import { api } from "../api/client";
import { Panel } from "./Page";
import { useToast } from "./Toast";
import { WhyButton } from "./WhyPanel";
import { useApi } from "../lib/useApi";

const WEEKDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** "3 × 8–12", or "3 × 20–30 s" for a hold (holds are dosed in seconds). */
export function planTarget(it: PlanItem): string {
  const range = it.rep_low === it.rep_high ? `${it.rep_low}` : `${it.rep_low}–${it.rep_high}`;
  return `${it.sets} × ${range}${it.measure === "hold" ? " s" : ""}`;
}
const LEVEL: Record<string, string> = { beginner: "Beginner", intermediate: "Intermediate", advanced: "Advanced" };

export function ProgramCard({ refreshKey = 0, onPick }: {
  refreshKey?: number;
  /** v1.2: the item's logger section comes along, so a calisthenics or hold item opens there. */
  onPick: (exerciseId: number, section?: string) => void;
}) {
  const [tick, setTick] = useState(0);
  const plan = useApi(api.currentPlan, [refreshKey, tick]);
  const [choosing, setChoosing] = useState(false);
  // v1.2: no program is a normal answer (null), not an error.
  const none = !plan.loading && !plan.error && plan.data === null;
  const p: Plan | null = plan.data ?? null;

  if (choosing || none) {
    return <ProgramChooser current={p?.program_key ?? null} onCancel={p ? () => setChoosing(false) : undefined}
      onChosen={() => { setChoosing(false); setTick((t) => t + 1); }} />;
  }
  return (
    <Panel id="program" title="Program" hover={false} className=""
      hint={p ? `${p.name} · ${p.sessions_done} ${p.sessions_done === 1 ? "session" : "sessions"} done, ${p.this_week_done}/${p.days_per_week} this week` : undefined}
      action={p && <button type="button" className="text-xs text-accent hover:underline" onClick={() => setChoosing(true)}>Change</button>}
      loading={plan.loading && !p} error={!p ? plan.error ?? null : null} onRetry={plan.reload} skeletonLines={4}>
      {p && (
        <>
          <div className="flex items-baseline justify-between gap-2">
            <div className="text-sm font-semibold text-ink">Next: {p.next.name}</div>
            {p.deload_week && <span className="chip border-warn/50 text-warn">Deload week</span>}
          </div>
          <div className="text-xs text-muted">{p.next.focus} · planned {WEEKDAY[p.next.weekday]}</div>
          <ul className="mt-3 space-y-1" aria-label={`${p.next.name} exercises`}>
            {p.next.items.map((it) => {
              const done = it.done_sets ?? 0;
              const complete = done >= it.sets;
              return (
                <li key={it.exercise}>
                  <button type="button" disabled={it.exercise_id === null} onClick={() => it.exercise_id !== null && onPick(it.exercise_id, it.section)}
                    className="flex w-full items-start justify-between gap-2 rounded-md px-2 py-1.5 text-left transition-colors duration-150 hover:bg-panel-2 disabled:cursor-default">
                    <span className="min-w-0">
                      <span className={`block truncate text-sm ${complete ? "text-muted line-through" : "text-ink"}`}>{it.exercise}</span>
                      <span className="block truncate text-xs text-muted">{it.target ?? planTarget(it)}</span>
                    </span>
                    <span className={`shrink-0 text-xs ${complete ? "text-good" : "text-muted"}`} aria-label={`${done} of ${it.sets} sets done`}>{done}/{it.sets}</span>
                  </button>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-xs text-muted">{p.reason}</p>
          <div className="mt-2">
            <WhyButton label="Why this session?" title="What is next" why={p.why} />
          </div>
        </>
      )}
    </Panel>
  );
}

function ProgramChooser({ current, onChosen, onCancel }: { current: string | null; onChosen: () => void; onCancel?: () => void }) {
  const progs = useApi(api.programs, []);
  const toast = useToast();
  const [busy, setBusy] = useState<string | null>(null);
  // v1.2: programs your kit can't do are hidden until you ask to explore them.
  const [explore, setExplore] = useState(false);
  const all = progs.data ?? [];
  const locked = all.filter((p) => !p.fits_equipment).length;
  const list = explore ? all : all.filter((p) => p.fits_equipment || p.key === current);

  async function choose(p: ProgramSummary) {
    setBusy(p.key);
    try {
      await api.choosePlan(p.key);
      toast(`Following ${p.name}`, "info");
      onChosen();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not choose that program", "error");
    } finally {
      setBusy(null);
    }
  }

  async function leave() {
    setBusy("leave");
    try {
      await api.leavePlan();
      toast("Program stopped. Your workouts stay in History.", "info");
      onChosen();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not stop the program", "error");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Panel id="program" title={current ? "Change program" : "Follow a program"} hover={false} className=""
      hint="The program picks the exercises; your progression sets the weights."
      action={onCancel && <button type="button" className="text-xs text-accent hover:underline" onClick={onCancel}>Cancel</button>}
      loading={progs.loading && !progs.data} error={!progs.data ? progs.error ?? null : null} onRetry={progs.reload} skeletonLines={4}>
      <ul className="space-y-2">
        {list.map((p) => (
          <li key={p.key} className={`rounded-lg border border-line bg-panel-2 p-3 ${p.fits_equipment ? "" : "opacity-60"}`}>
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-sm font-semibold text-ink">{p.name}</span>
              <span className="text-[11px] text-muted">{LEVEL[p.level] ?? p.level}</span>
            </div>
            <p className="mt-1 text-xs text-muted">{p.summary}</p>
            <p className="mt-1 text-[11px] text-muted">{p.days.map((d) => `${WEEKDAY[d.weekday]} ${d.name}`).join(" · ")}</p>
            {!p.fits_equipment && <p className="mt-1 text-[11px] text-warn">Needs equipment you didn't list at setup.</p>}
            <button type="button" className="btn-ghost mt-2 px-2 py-1 text-xs" disabled={busy !== null || p.key === current}
              aria-label={`Follow ${p.name}`} onClick={() => void choose(p)}>
              {p.key === current ? "Following" : busy === p.key ? "Choosing…" : "Follow"}
            </button>
          </li>
        ))}
      </ul>
      {locked > 0 && (
        <button type="button" className="mt-3 block text-xs text-accent hover:underline" aria-pressed={explore} onClick={() => setExplore((x) => !x)}>
          {explore ? "Hide programs that need other kit" : `Explore all (${locked} need other kit)`}
        </button>
      )}
      {current && (
        <button type="button" className="mt-3 text-xs text-muted hover:text-ink hover:underline" disabled={busy !== null} onClick={() => void leave()}>Stop following a program</button>
      )}
    </Panel>
  );
}
