/**
 * Skill trees: calisthenics progressions computed from logged sets. The grid shows
 * every tree with its current step and % to the next; a tree's page shows each step,
 * its unlock criteria and progress, feeder exercises, a time-to-unlock estimate (only
 * with enough data) and a "Train this skill" action that adds work to today's quest.
 * Deep links: #skills (grid) and #skills/<key> (one tree).
 */
import type { SkillCriterion, SkillDetail, SkillFamily, SkillStep, SkillSummary } from "@ascend/shared";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import { CustomSkills } from "../components/CustomSkills";
import type { Page } from "../components/Layout";
import { IconCheck, IconLock } from "../components/Icons";
import { Segmented } from "../components/Segmented";
import { SkeletonCard } from "../components/Skeleton";
import { SkillTreeCanvas } from "../components/SkillTreeCanvas";
import { Empty, ErrorState, Loading } from "../components/States";
import { useToast } from "../components/Toast";
import { setPendingExercise } from "../lib/pending";
import { useApi } from "../lib/useApi";

type FamilyFilter = "all" | SkillFamily;

export const FAMILY_LABEL: Record<SkillFamily, string> = {
  pull: "Pull",
  push: "Push",
  core: "Core",
  balance: "Balance",
  legs: "Legs",
  levers: "Levers",
};

const FAMILY_OPTIONS: { value: FamilyFilter; label: string }[] = [
  { value: "all", label: "All" },
  ...(Object.keys(FAMILY_LABEL) as SkillFamily[]).map((f) => ({ value: f, label: FAMILY_LABEL[f] })),
];

export function skillKeyFromHash(hash: string): string | null {
  const [page, key] = hash.replace("#", "").split("/");
  return page === "skills" && key ? decodeURIComponent(key) : null;
}

export function SkillsPage({ onNavigate, onChanged }: { onNavigate: (p: Page) => void; onChanged: () => void }) {
  const [openKey, setOpenKey] = useState<string | null>(() => skillKeyFromHash(window.location.hash));
  useEffect(() => {
    const onHash = () => setOpenKey(skillKeyFromHash(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const open = (key: string | null) => {
    window.location.hash = key ? `skills/${encodeURIComponent(key)}` : "skills";
    setOpenKey(key);
  };
  return openKey ? (
    <SkillDetailView skillKey={openKey} onBack={() => open(null)} onNavigate={onNavigate} onChanged={onChanged} />
  ) : (
    <SkillGrid onOpen={open} onNavigate={onNavigate} onChanged={onChanged} />
  );
}

type View = "tree" | "cards";

function SkillGrid({ onOpen, onNavigate, onChanged }: { onOpen: (key: string) => void; onNavigate: (p: Page) => void; onChanged: () => void }) {
  const list = useApi(() => api.skills(), []);
  const [family, setFamily] = useState<FamilyFilter>("all");
  const [view, setView] = useState<View>("tree");
  // v1.2: only the trees your kit can train; "Explore all" shows the rest.
  const [explore, setExplore] = useState(false);
  const hiddenByKit = (list.data ?? []).filter((s) => s.fits_equipment === false).length;
  const shown = useMemo(
    () => (list.data ?? []).filter((s) => (family === "all" || s.family === family) && (explore || s.fits_equipment !== false)),
    [list.data, family, explore],
  );
  if (list.error && !list.data) return <ErrorState message={list.error} onRetry={list.reload} />;
  const started = (list.data ?? []).filter((s) => s.steps_unlocked > 1 || (s.pct_to_next ?? 0) > 0).length;
  const unlockedSteps = (list.data ?? []).reduce((n, s) => n + s.steps_unlocked, 0);
  return (
    <div className="space-y-4">
      <section className="card flex flex-wrap items-center gap-x-6 gap-y-3 p-4">
        <div className="min-w-0">
          <h2 className="text-h3 text-ink">Calisthenics skill trees</h2>
          <p className="mt-0.5 text-xs text-muted">
            Progress comes from the sets you log: hit a step&apos;s target in two sessions to unlock the next.
          </p>
        </div>
        {list.data && (
          <p className="text-xs text-muted" role="status">
            <span className="font-semibold text-ink">{started}</span> of {list.data.length} trees in progress ·{" "}
            <span className="font-semibold text-ink">{unlockedSteps}</span> steps unlocked
          </p>
        )}
        <div className="ml-auto flex flex-wrap items-center gap-3">
          <Segmented label="Skill family" value={family} options={FAMILY_OPTIONS} onChange={setFamily} />
          {hiddenByKit > 0 && (
            <label className="flex items-center gap-2 text-xs text-muted" title="Show trees that need kit you don't have">
              <input type="checkbox" className="accent-[var(--color-accent)]" checked={explore} onChange={(e) => setExplore(e.target.checked)} />
              Explore all ({hiddenByKit} need other kit)
            </label>
          )}
          <Segmented label="View" value={view} options={[{ value: "tree", label: "Tree" }, { value: "cards", label: "Cards" }]} onChange={setView} />
        </div>
      </section>
      {list.loading && !list.data ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{[0, 1, 2, 3, 4, 5].map((i) => <SkeletonCard key={i} lines={3} />)}</div>
      ) : view === "tree" ? (
        <TreeView keys={shown.map((s) => s.key)} family={family} onOpen={onOpen} onNavigate={onNavigate} onChanged={onChanged} />
      ) : (
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" aria-label="Skill trees">
          {shown.map((s) => (
            <li key={s.key}>
              <SkillCard skill={s} onOpen={() => onOpen(s.key)} />
            </li>
          ))}
        </ul>
      )}
      <CustomSkills onChanged={() => { list.reload(); onChanged(); }} />
    </div>
  );
}

/** Canvas (8 columns) and the step drawer (4 columns). */
function TreeView({ keys, family, onOpen, onNavigate, onChanged }: {
  keys: string[];
  family: FamilyFilter;
  onOpen: (key: string) => void;
  onNavigate: (p: Page) => void;
  onChanged: () => void;
}) {
  const joined = keys.join(",");
  const [tick, setTick] = useState(0);
  // One call for every tree (the sidecar has /skills/details for this page); asking once per
  // tree queued 17 requests and kept the canvas blank for about 2 s with a full save.
  const details = useApi(async () => {
    const all = await api.skillDetails();
    const byKey = new Map(all.map((t) => [t.key, t]));
    return keys.map((k) => byKey.get(k)).filter((t): t is SkillDetail => t !== undefined);
  }, [joined, tick]);
  const [selected, setSelected] = useState<string | null>(null);
  const trees = details.data ?? [];
  // Select the first current step when the family changes.
  useEffect(() => {
    if (!details.data) return;
    if (selected && details.data.some((t) => selected.startsWith(`${t.key}/`))) return;
    const t = details.data.find((x) => x.next_step) ?? details.data[0];
    setSelected(t ? `${t.key}/${t.next_step ?? t.steps[0]?.key}` : null);
  }, [details.data, selected]);
  if (details.error && !details.data) return <ErrorState message={details.error} onRetry={details.reload} />;
  if (!details.data) return <Loading label="Loading skill trees…" />;
  if (trees.length === 0) return <Empty title="No trees in this family." />;
  const [treeKey, stepKey] = (selected ?? "").split("/");
  const tree = trees.find((t) => t.key === treeKey) ?? null;
  const step = tree?.steps.find((s) => s.key === stepKey) ?? null;
  return (
    <div className="grid grid-cols-12 gap-4">
      <section className="card col-span-12 p-4 xl:col-span-8" aria-labelledby="canvas-title">
        <h3 id="canvas-title" className="sr-only">Skill tree canvas</h3>
        <SkillTreeCanvas trees={trees} selected={selected} onSelect={setSelected} fitAll={family !== "all"}
          label={`${family === "all" ? "All" : FAMILY_LABEL[family]} skill trees. Use the arrow keys to move between steps.`} />
      </section>
      <div className="col-span-12 xl:col-span-4">
        {tree && step ? (
          <StepDrawer tree={tree} step={step} onOpen={() => onOpen(tree.key)} onNavigate={onNavigate}
            onTrained={() => { onChanged(); setTick((t) => t + 1); }} />
        ) : (
          <section className="card p-5 text-sm text-muted">Select a step to see what unlocks it.</section>
        )}
      </div>
    </div>
  );
}

function StepDrawer({ tree, step, onOpen, onNavigate, onTrained }: {
  tree: SkillDetail;
  step: SkillStep;
  onOpen: () => void;
  onNavigate: (p: Page) => void;
  onTrained: () => void;
}) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const isNext = tree.next_step === step.key;
  async function train() {
    setBusy(true);
    try {
      const r = await api.trainSkill(tree.key);
      toast(r.message, r.added ? "xp" : "info");
      onTrained();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }
  const log = (id: number | null) => {
    if (id === null) return;
    setPendingExercise({ id, section: "calisthenics" });
    onNavigate("workout");
  };
  return (
    <section className="card panel-in sticky top-0 p-5" aria-labelledby="drawer-title" data-testid="step-drawer" key={`${tree.key}/${step.key}`}>
      <p className="card-title">{tree.name}</p>
      <h3 id="drawer-title" className="text-h2 mt-1 text-ink">{step.name}</h3>
      <p className="mt-1 text-sm text-muted">
        <span className={step.status === "unlocked" ? "text-good" : step.status === "next" ? "text-accent" : "text-muted"}>
          {step.status === "unlocked" ? `Mastered${step.unlocked_at ? ` on ${fmtDate(step.unlocked_at)}` : ""}` : step.status === "next" ? `Next step · ${Math.round(step.pct)}% to unlock` : "Locked: unlock the steps before it first"}
        </span>
        {step.xp > 0 && <span className="text-xp"> · +{step.xp} XP</span>}
      </p>
      {step.status === "next" && <ProgressBar className="mt-2" pct={step.pct} label={`Progress to ${step.name}`} />}
      {step.criteria.length > 0 ? (
        <>
          <h4 className="mt-4 text-xs font-semibold uppercase tracking-wider text-faint">Criteria</h4>
          <ul className="mt-2 space-y-3">{step.criteria.map((c) => <CriterionRow key={c.text} c={c} />)}</ul>
        </>
      ) : (
        <p className="mt-4 text-xs text-muted">An entry step: it starts unlocked.</p>
      )}
      {isNext && <Eta s={tree} />}
      {step.uncertain && <p className="mt-3 text-xs text-faint">Uncertain target: {step.note || "sources disagree on the exact number."}</p>}
      {tree.feeders.length > 0 && (
        <p className="mt-4 text-xs text-muted">
          <span className="font-medium text-ink">Feeders: </span>{tree.feeders.slice(0, 4).map((f) => f.name).join(", ")}
        </p>
      )}
      <div className="mt-5 flex flex-wrap gap-2">
        <button type="button" className="btn-primary" onClick={train} disabled={busy}>{busy ? "Adding…" : "Train this skill"}</button>
        {step.exercise_id !== null && step.status !== "locked" && (
          <button type="button" className="btn-ghost" onClick={() => log(step.exercise_id)}>Log {step.exercise}</button>
        )}
        <button type="button" className="btn-ghost" onClick={onOpen}>Open tree page</button>
      </div>
    </section>
  );
}

export function ProgressBar({ pct, label, tone = "accent", className = "" }: { pct: number; label: string; tone?: "accent" | "good" | "xp"; className?: string }) {
  const value = Math.max(0, Math.min(100, Math.round(pct)));
  const fill = tone === "good" ? "bg-good" : tone === "xp" ? "bg-xp" : "bg-accent";
  return (
    <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value} className={`h-1.5 overflow-hidden rounded-full bg-panel-2 ${className}`}>
      <div className={`h-full rounded-full ${fill} transition-[width] duration-500`} style={{ width: `${value}%` }} />
    </div>
  );
}

function SkillCard({ skill: s, onOpen }: { skill: SkillSummary; onOpen: () => void }) {
  return (
    <button type="button" onClick={onOpen} className="card card-hover card-lift group block h-full w-full p-4 text-left">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-ink group-hover:text-accent">{s.name}</div>
          <div className="mt-0.5 line-clamp-1 text-xs text-muted">{s.summary}</div>
        </div>
        <span className="chip shrink-0">{FAMILY_LABEL[s.family]}</span>
      </div>
      <div className="mt-3 flex items-baseline justify-between gap-2 text-xs">
        <span className="truncate text-muted">
          {s.current_step_name ? <>Now: <span className="text-ink">{s.current_step_name}</span></> : "Not started"}
        </span>
        <span className="shrink-0 tabular-nums text-faint">{s.steps_unlocked}/{s.steps_total} steps</span>
      </div>
      {s.acquired ? (
        <p className="mt-2 text-xs font-medium text-good">Tree complete</p>
      ) : (
        <>
          <ProgressBar className="mt-2" pct={s.pct_to_next ?? 0} label={`${s.name}: progress to ${s.next_step_name ?? "next step"}`} />
          <div className="mt-1.5 flex items-baseline justify-between gap-2 text-xs">
            <span className="truncate text-muted">Next: {s.next_step_name}</span>
            <span className="shrink-0 font-semibold tabular-nums text-ink">{Math.round(s.pct_to_next ?? 0)}%</span>
          </div>
        </>
      )}
      <StepDots unlocked={s.steps_unlocked} total={s.steps_total} />
      <div className="mt-3 flex flex-wrap gap-1">
        {s.stretch && <span className="chip border-xp/40 text-xp">Stretch goal</span>}
        {s.rusty && <span className="chip border-warn/40 text-warn">Rusty</span>}
        {s.sessions_28d > 0 && <span className="chip">{s.sessions_28d} session{s.sessions_28d === 1 ? "" : "s"} in 4 weeks</span>}
      </div>
    </button>
  );
}

function StepDots({ unlocked, total }: { unlocked: number; total: number }) {
  return (
    <div className="mt-3 flex gap-1" aria-hidden="true">
      {Array.from({ length: total }, (_, i) => (
        <span key={i} className={`h-1 flex-1 rounded-full ${i < unlocked ? "bg-good" : "bg-line-2"}`} />
      ))}
    </div>
  );
}

const fmtDate = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

function SkillDetailView({ skillKey, onBack, onNavigate, onChanged }: {
  skillKey: string;
  onBack: () => void;
  onNavigate: (p: Page) => void;
  onChanged: () => void;
}) {
  const d = useApi(() => api.skill(skillKey), [skillKey]);
  const toast = useToast();
  const [training, setTraining] = useState(false);
  const logIt = (exerciseId: number | null) => {
    if (exerciseId === null) return;
    setPendingExercise({ id: exerciseId, section: "calisthenics" });
    onNavigate("workout");
  };
  const train = async () => {
    setTraining(true);
    try {
      const r = await api.trainSkill(skillKey);
      toast(r.message, r.added ? "xp" : "info");
      onChanged();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setTraining(false);
    }
  };
  return (
    <div className="max-w-6xl space-y-4">
      <button type="button" className="btn-ghost" onClick={onBack}>← All skills</button>
      {d.loading && !d.data ? (
        <Loading label="Loading skill…" />
      ) : d.error && !d.data ? (
        <ErrorState message={d.error} onRetry={d.reload} />
      ) : (
        d.data && <SkillDetailBody s={d.data} onTrain={train} training={training} onLog={logIt} />
      )}
    </div>
  );
}

function SkillDetailBody({ s, onTrain, training, onLog }: { s: SkillDetail; onTrain: () => void; training: boolean; onLog: (id: number | null) => void }) {
  const next = s.steps.find((st) => st.key === s.next_step) ?? null;
  // What to practise now: the first unmet criterion of the next step.
  const practise = next ? (next.criteria.find((c) => !c.met) ?? next.criteria[0] ?? null) : null;
  const byKey = Object.fromEntries(s.steps.map((st) => [st.key, st]));
  return (
    <>
      <section className="card flex flex-wrap items-start gap-4 p-5">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-xl font-bold text-ink">{s.name}</h2>
            <span className="chip">{FAMILY_LABEL[s.family]}</span>
            {s.stretch && <span className="chip border-xp/40 text-xp">Stretch goal</span>}
            {s.acquired && <span className="chip border-good/40 text-good">Tree complete</span>}
            {s.rusty && <span className="chip border-warn/40 text-warn" title="Your current step has not been trained in 4 weeks">Rusty</span>}
          </div>
          <p className="mt-1 text-sm text-muted">{s.summary}</p>
          <p className="mt-2 text-xs text-faint">
            {s.steps_unlocked} of {s.steps_total} steps unlocked
            {s.last_trained ? ` · last trained ${fmtDate(s.last_trained)}` : ""} · {s.sessions_28d} session{s.sessions_28d === 1 ? "" : "s"} in 4 weeks
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {practise?.exercise_id != null && (
            <button type="button" className="btn-ghost" onClick={() => onLog(practise.exercise_id)}>
              Log {practise.exercise}
            </button>
          )}
          <button type="button" className="btn btn-primary" onClick={onTrain} disabled={training}>
            {training ? "Adding…" : "Train this skill"}
          </button>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
        <section className="card p-5" aria-labelledby="tree-heading">
          <h3 id="tree-heading" className="card-title">Progression</h3>
          <ol className="relative mt-4 space-y-0">
            {s.steps.map((st, i) => (
              <StepNode key={st.key} step={st} last={i === s.steps.length - 1} prevKey={s.steps[i - 1]?.key ?? null} names={byKey} />
            ))}
          </ol>
        </section>

        <div className="space-y-4">
          {next ? (
            <section className="card p-5" aria-labelledby="next-heading">
              <h3 id="next-heading" className="card-title">Next: {next.name}</h3>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="font-display text-4xl font-bold tabular-nums text-ink">{Math.round(next.pct)}%</span>
                <span className="text-xs text-muted">to unlock</span>
              </div>
              <ProgressBar className="mt-2" pct={next.pct} label={`Progress to ${next.name}`} />
              <ul className="mt-4 space-y-3">
                {next.criteria.map((c) => <CriterionRow key={c.text} c={c} />)}
              </ul>
              <Eta s={s} />
            </section>
          ) : (
            <section className="card p-5">
              <h3 className="card-title">Every step unlocked</h3>
              <p className="mt-2 text-sm text-muted">Keep the skill sharp: it shows as rusty after 4 weeks without training its last step.</p>
            </section>
          )}

          <section className="card p-5" aria-labelledby="feeders-heading">
            <h3 id="feeders-heading" className="card-title">Feeder exercises</h3>
            <p className="mt-1 text-xs text-muted">These build the strength the tree needs.</p>
            <ul className="mt-3 divide-y divide-line">
              {s.feeders.map((f) => (
                <li key={f.name} className="flex items-center gap-2 py-2">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm text-ink">{f.name}</div>
                    <div className="text-xs text-faint">{f.sets_28d ? `${f.sets_28d} sets in 4 weeks` : "Not trained in 4 weeks"}</div>
                  </div>
                  {f.exercise_id != null && (
                    <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={() => onLog(f.exercise_id)} aria-label={`Log ${f.name}`}>
                      Log
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </section>

          <section className="card p-5" aria-labelledby="sources-heading">
            <h3 id="sources-heading" className="card-title">Where the steps come from</h3>
            <ul className="mt-2 space-y-1 text-xs">
              {s.sources.map((src) => (
                <li key={src.key}>
                  <a className="text-accent underline-offset-2 hover:underline" href={src.url} target="_blank" rel="noreferrer">{src.title}</a>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-muted">
              The order follows these sources. The targets are ASCEND&apos;s own choices, informed by them, and steps marked
              &quot;uncertain&quot; are ones where sources disagree.
            </p>
          </section>
        </div>
      </div>
    </>
  );
}

function Eta({ s }: { s: SkillDetail }) {
  const { eta } = s;
  if (eta.days === null) {
    return (
      <p className="mt-4 rounded-lg bg-panel-2 px-3 py-2 text-xs text-muted">
        <span className="font-medium text-ink">No time estimate yet.</span> {eta.reason.charAt(0).toUpperCase() + eta.reason.slice(1)}.
      </p>
    );
  }
  const days = Math.max(1, Math.ceil(eta.days));
  return (
    <p className="mt-4 rounded-lg bg-panel-2 px-3 py-2 text-xs text-muted">
      <span className="font-medium text-ink">Estimate: about {days} day{days === 1 ? "" : "s"}</span>
      {eta.date ? ` (around ${fmtDate(eta.date)})` : ""}, if your recent trend holds. A projection, not a promise.
    </p>
  );
}

function CriterionRow({ c }: { c: SkillCriterion }) {
  const best = c.best_value === null ? "nothing logged yet" : `best ${c.best_value}${c.unit === "s" ? " s" : ""}`;
  const oneMore = c.best_score >= 1 && !c.met;
  return (
    <li>
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className={c.met ? "text-good" : "text-ink"}>
          {c.met && <IconCheck width={14} className="mr-1 inline align-[-2px]" aria-hidden="true" />}
          {c.text}
        </span>
        <span className="shrink-0 text-xs tabular-nums text-muted">{Math.round(c.pct)}%</span>
      </div>
      <ProgressBar className="mt-1" pct={c.pct} tone={c.met ? "good" : "accent"} label={c.text} />
      <p className="mt-1 text-xs text-faint">
        {best} · {Math.min(c.sessions_met, c.sessions_needed)} of {c.sessions_needed} sessions
        {oneMore && <span className="text-accent"> · hit it once more on another day to lock it in</span>}
        {c.ignored_sets > 0 && <span className="text-warn"> · {c.ignored_sets} implausibly long hold{c.ignored_sets === 1 ? "" : "s"} not counted</span>}
      </p>
    </li>
  );
}

function StepNode({ step, last, prevKey, names }: { step: SkillStep; last: boolean; prevKey: string | null; names: Record<string, SkillStep> }) {
  const branch = step.requires.length > 1 || (step.requires.length === 1 && step.requires[0] !== prevKey);
  const icon =
    step.status === "unlocked" ? (
      <span className="grid h-7 w-7 place-items-center rounded-full bg-good text-white"><IconCheck width={14} aria-hidden="true" /></span>
    ) : step.status === "next" ? (
      <span className="grid h-7 w-7 place-items-center rounded-full border-2 border-accent bg-panel text-[10px] font-semibold tabular-nums text-accent">{Math.round(step.pct)}</span>
    ) : (
      <span className="grid h-7 w-7 place-items-center rounded-full border border-line-2 bg-panel-2 text-faint"><IconLock width={12} aria-hidden="true" /></span>
    );
  const statusLabel = step.status === "unlocked" ? "Unlocked" : step.status === "next" ? `Next, ${Math.round(step.pct)}%` : "Locked";
  return (
    <li className="relative flex gap-3 pb-5" data-status={step.status}>
      {!last && <span aria-hidden="true" className={`absolute left-[13px] top-7 h-[calc(100%-1.75rem)] w-0.5 ${step.status === "unlocked" ? "bg-good/60" : "bg-line-2"}`} />}
      <div className="relative z-10 shrink-0">{icon}</div>
      <div className="min-w-0 flex-1 pt-0.5">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className={`text-sm font-medium ${step.status === "locked" ? "text-muted" : "text-ink"}`}>{step.name}</span>
          <span className="sr-only">{statusLabel}</span>
          {step.xp > 0 && <span className="text-[11px] text-xp">+{step.xp} XP</span>}
          {step.uncertain && (
            <span className="rounded border border-line-2 px-1.5 py-px text-[10px] uppercase tracking-wide text-faint" title={step.note || "Sources disagree on the exact target"}>
              uncertain
            </span>
          )}
        </div>
        {step.exercise.toLowerCase() !== step.name.toLowerCase() && <div className="text-xs text-faint">{step.exercise}</div>}
        {branch && (
          <div className="mt-0.5 text-xs text-muted">After: {step.requires.map((r) => names[r]?.name ?? r).join(" + ")}</div>
        )}
        {step.criteria.length > 0 && step.status !== "unlocked" && (
          <div className="mt-1 text-xs text-muted">Unlocks with {step.criteria.map((c) => c.text).join(" and ")}</div>
        )}
        {step.status === "unlocked" && step.unlocked_at && <div className="mt-0.5 text-xs text-faint">Unlocked {fmtDate(step.unlocked_at)}</div>}
        {step.status === "next" && <ProgressBar className="mt-2 max-w-xs" pct={step.pct} label={`Progress to ${step.name}`} />}
        {step.note && step.status !== "locked" && <div className="mt-1 text-xs text-faint">{step.note}</div>}
      </div>
    </li>
  );
}
