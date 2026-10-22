/**
 * Exercise gallery: the whole offline library (free-exercise-db + ASCEND's own
 * calisthenics progressions + anything the user added), with search, filters and a
 * detail view that shows instructions, muscles hit, the skill trees an exercise feeds
 * and a "Log it" button that opens it in the logger.
 */
import type { Difficulty, Exercise, ExerciseDetail, FieldSource, Section } from "@ascend/shared";
import { useMemo, useState } from "react";

import { api } from "../api/client";
import type { Page } from "../components/Layout";
import { IconPlus, IconSearch } from "../components/Icons";
import { useToast } from "../components/Toast";
import { AddExerciseView } from "./AddExercise";
import { Segmented } from "../components/Segmented";
import { SkeletonCard } from "../components/Skeleton";
import { ErrorState, Loading } from "../components/States";
import { setPendingExercise } from "../lib/pending";
import { MUSCLE_LABEL, muscleLabel } from "../lib/muscles";
import { ExerciseArt } from "../components/ExerciseArt";
import { useApi } from "../lib/useApi";

export type LibraryType = "all" | "strength" | "calisthenics" | "cardio" | "mobility" | "other";

const TYPE_OPTIONS: { value: LibraryType; label: string }[] = [
  { value: "all", label: "All" },
  { value: "strength", label: "Strength" },
  { value: "calisthenics", label: "Calisthenics" },
  { value: "cardio", label: "Cardio" },
  { value: "mobility", label: "Mobility" },
  { value: "other", label: "Martial arts & mind" },
];

const TYPE_SECTIONS: Record<Exclude<LibraryType, "all">, Section[]> = {
  strength: ["gym"],
  calisthenics: ["calisthenics"],
  cardio: ["cardio"],
  mobility: ["flexibility"],
  other: ["martial_arts", "meditation"],
};

export const SECTION_TYPE_LABEL: Record<Section, string> = {
  gym: "Strength",
  calisthenics: "Calisthenics",
  cardio: "Cardio",
  flexibility: "Mobility",
  martial_arts: "Martial arts",
  meditation: "Mind",
};

export const SOURCE_LABEL: Record<FieldSource, string> = {
  library: "Library",
  rules: "Rules",
  local_ai: "Local AI",
  wger: "wger",
  wikipedia: "Wikipedia",
  user: "You",
};

const PAGE_SIZE = 60;

export interface LibraryFilters {
  q: string;
  type: LibraryType;
  muscle: string;
  equipment: string;
  difficulty: "" | Difficulty;
  customOnly: boolean;
}

export const EMPTY_FILTERS: LibraryFilters = { q: "", type: "all", muscle: "", equipment: "", difficulty: "", customOnly: false };

const normalise = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").replace(/\bups\b/g, "up").replace(/(?<=[a-z]{3})(?<!s)s\b/g, "").trim();

/** Client-side filter over the full list: instant, and the same rules as the sidecar's search. */
export function filterExercises(list: Exercise[], f: LibraryFilters): Exercise[] {
  const words = normalise(f.q).split(" ").filter(Boolean);
  return list.filter((e) => {
    if (f.type !== "all" && !TYPE_SECTIONS[f.type].includes(e.section)) return false;
    if (f.muscle && !e.muscles.some((m) => m.muscle === f.muscle && m.weight >= 0.5)) return false;
    if (f.equipment && e.equipment !== f.equipment) return false;
    if (f.difficulty && e.difficulty !== f.difficulty) return false;
    if (f.customOnly && !e.is_custom) return false;
    if (words.length === 0) return true;
    return [e.name, ...(e.aliases ?? [])].some((text) => {
      const t = normalise(text).split(" ");
      return words.every((w) => t.some((x) => x.startsWith(w)));
    });
  });
}

export function LibraryPage({ onNavigate, refreshKey }: { onNavigate: (p: Page) => void; refreshKey: number }) {
  const [version, setVersion] = useState(0);
  const list = useApi(() => api.exercises(""), [refreshKey, version]);
  const [adding, setAdding] = useState(false);
  const [filters, setFilters] = useState<LibraryFilters>(EMPTY_FILTERS);
  const [shown, setShown] = useState(PAGE_SIZE);
  const [openId, setOpenId] = useState<number | null>(null);

  const equipment = useMemo(() => [...new Set((list.data ?? []).map((e) => e.equipment))].sort(), [list.data]);
  const results = useMemo(() => filterExercises(list.data ?? [], filters), [list.data, filters]);

  const set = <K extends keyof LibraryFilters>(key: K, value: LibraryFilters[K]) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setShown(PAGE_SIZE);
  };

  if (adding) {
    return (
      <AddExerciseView
        onBack={() => setAdding(false)}
        onCreated={(id) => { setAdding(false); setVersion((v) => v + 1); setOpenId(id); }}
        onOpenExisting={(id) => { setAdding(false); setOpenId(id); }}
      />
    );
  }
  if (openId !== null) {
    return <ExerciseDetailView id={openId} onBack={() => setOpenId(null)} onNavigate={onNavigate} onRemoved={() => { setOpenId(null); setVersion((v) => v + 1); }} />;
  }
  if (list.error && !list.data) return <ErrorState message={list.error} onRetry={list.reload} />;

  return (
    <div className="space-y-4">
      <section className="card p-4" aria-label="Search and filters">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[220px] flex-1">
            <IconSearch className="absolute left-3 top-2.5 text-faint" width={16} height={16} />
            <input className="input pl-9" type="search" aria-label="Search exercises" placeholder="Search name or alias, e.g. pullups, L-sit…"
              value={filters.q} onChange={(e) => set("q", e.target.value)} />
          </div>
          <button type="button" className="btn btn-primary" onClick={() => setAdding(true)}>
            <IconPlus width={16} className="mr-1 inline align-[-3px]" />Add your own
          </button>
        </div>
        <div className="mt-3 overflow-x-auto">
          <Segmented label="Exercise type" value={filters.type} options={TYPE_OPTIONS} onChange={(v) => set("type", v)} />
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
          <label className="flex items-center gap-2 text-muted">
            Muscle
            <select className="input w-40 py-1.5" value={filters.muscle} onChange={(e) => set("muscle", e.target.value)}>
              <option value="">Any</option>
              {Object.entries(MUSCLE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2 text-muted">
            Equipment
            <select className="input w-40 py-1.5" value={filters.equipment} onChange={(e) => set("equipment", e.target.value)}>
              <option value="">Any</option>
              {equipment.map((eq) => <option key={eq} value={eq}>{eq.replace(/_/g, " ")}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2 text-muted">
            Difficulty
            <select className="input w-36 py-1.5" value={filters.difficulty} onChange={(e) => set("difficulty", e.target.value as LibraryFilters["difficulty"])}>
              <option value="">Any</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="expert">Expert</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-muted">
            <input type="checkbox" className="accent-[var(--color-accent)]" checked={filters.customOnly} onChange={(e) => set("customOnly", e.target.checked)} />
            Added by me
          </label>
          {JSON.stringify(filters) !== JSON.stringify(EMPTY_FILTERS) && (
            <button type="button" className="text-accent underline-offset-2 hover:underline" onClick={() => { setFilters(EMPTY_FILTERS); setShown(PAGE_SIZE); }}>
              Clear filters
            </button>
          )}
          <span className="ml-auto text-faint" role="status" aria-live="polite">
            {list.data ? `${results.length.toLocaleString("en-IN")} of ${list.data.length.toLocaleString("en-IN")} exercises` : ""}
          </span>
        </div>
      </section>

      {list.loading && !list.data ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">{[0, 1, 2, 3, 4, 5, 6, 7].map((i) => <SkeletonCard key={i} lines={2} />)}</div>
      ) : results.length === 0 ? (
        <div className="card p-8 text-center">
          <h2 className="text-base font-semibold text-ink">No exercise matches</h2>
          <p className="mt-1 text-sm text-muted">Try fewer filters or another name.</p>
        </div>
      ) : (
        <>
          <ul className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4" aria-label="Exercises">
            {results.slice(0, shown).map((e) => (
              <li key={e.id}>
                <ExerciseCard exercise={e} onOpen={() => setOpenId(e.id)} />
              </li>
            ))}
          </ul>
          {shown < results.length && (
            <div className="flex justify-center">
              <button type="button" className="btn-ghost" onClick={() => setShown((n) => n + PAGE_SIZE)}>
                Show more ({(results.length - shown).toLocaleString("en-IN")} left)
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/** Kept for existing imports: the exercise picture (photo or designed tile). */
export function Thumb({ exercise, className = "" }: { exercise: Pick<Exercise, "image" | "name" | "section"> & { muscles?: Exercise["muscles"] }; className?: string }) {
  return <ExerciseArt exercise={exercise} className={className} />;
}

function ExerciseCard({ exercise: e, onOpen }: { exercise: Exercise; onOpen: () => void }) {
  const primary = e.muscles.filter((m) => m.weight >= 1).map((m) => muscleLabel(m.muscle));
  return (
    <button type="button" onClick={onOpen} className="card card-hover card-lift group block w-full overflow-hidden text-left">
      <Thumb exercise={e} className="aspect-[3/2]" />
      <div className="p-3">
        <div className="line-clamp-2 text-sm font-medium text-ink group-hover:text-accent">{e.name}</div>
        <div className="mt-1 truncate text-xs text-muted">{primary.length ? primary.join(", ") : SECTION_TYPE_LABEL[e.section]}</div>
        <div className="mt-2 flex flex-wrap gap-1">
          <span className="chip">{SECTION_TYPE_LABEL[e.section]}</span>
          {e.difficulty && <span className="chip capitalize">{e.difficulty}</span>}
          {e.measure === "hold" && <span className="chip">Hold</span>}
          {e.is_custom && <span className="chip border-xp/40 text-xp">Added by you</span>}
        </div>
      </div>
    </button>
  );
}

function SourceTag({ source }: { source: FieldSource | undefined }) {
  if (!source) return null;
  return <span className="ml-2 rounded border border-line-2 px-1.5 py-px text-[10px] font-normal uppercase tracking-wide text-faint">{SOURCE_LABEL[source] ?? source}</span>;
}

export function ExerciseDetailView({ id, onBack, onNavigate, onRemoved }: { id: number; onBack: () => void; onNavigate: (p: Page) => void; onRemoved?: () => void }) {
  const d = useApi(() => api.exercise(id), [id]);
  const toast = useToast();
  const [confirming, setConfirming] = useState(false);
  const remove = async (e: ExerciseDetail) => {
    try {
      await api.archiveExercise(e.id);
      toast(`Removed ${e.name}. Its logged sets stay in your history.`, "info");
      onRemoved?.();
    } catch (err) {
      toast((err as Error).message, "error");
    }
  };
  const logIt = (e: ExerciseDetail) => {
    setPendingExercise({ id: e.id, section: e.section });
    onNavigate("workout");
  };
  return (
    <div className="max-w-5xl space-y-4">
      <button type="button" className="btn-ghost" onClick={onBack}>← All exercises</button>
      {d.loading && !d.data ? <Loading label="Loading exercise…" /> : d.error && !d.data ? <ErrorState message={d.error} onRetry={d.reload} /> : d.data && (
        <>
          <ExerciseDetailBody e={d.data} onLog={() => logIt(d.data!)} onOpenSkill={(key) => { window.location.hash = `skills/${key}`; }} />
          {d.data.is_custom && (
            <section className="card flex flex-wrap items-center gap-3 p-4">
              <p className="mr-auto text-xs text-muted">You added this exercise. Removing it hides it from the library and pickers; sets you logged stay.</p>
              {confirming ? (
                <>
                  <button type="button" className="btn-ghost text-bad" onClick={() => remove(d.data!)}>Yes, remove it</button>
                  <button type="button" className="btn-ghost" onClick={() => setConfirming(false)}>Keep</button>
                </>
              ) : (
                <button type="button" className="btn-ghost" onClick={() => setConfirming(true)}>Remove from my library</button>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}

function ExerciseDetailBody({ e, onLog, onOpenSkill }: { e: ExerciseDetail; onLog: () => void; onOpenSkill: (skillKey: string) => void }) {
  const fs = e.field_sources;
  const range = e.rep_low && e.rep_high ? (e.measure === "hold" ? `${e.rep_low}–${e.rep_high} s per hold` : `${e.rep_low}–${e.rep_high} reps`) : null;
  return (
    <article className="grid grid-cols-12 gap-4" aria-labelledby="exercise-title">
      <section className="card col-span-12 overflow-hidden md:col-span-5">
        <Thumb exercise={e} className="aspect-[3/2]" />
        <div className="space-y-2 p-4 text-xs text-muted">
          <div><span className="text-faint">Type</span> · {SECTION_TYPE_LABEL[e.section]}<SourceTag source={fs.section} /></div>
          <div><span className="text-faint">Equipment</span> · {e.equipment.replace(/_/g, " ")}<SourceTag source={fs.equipment} /></div>
          {e.difficulty && <div className="capitalize"><span className="normal-case text-faint">Difficulty</span> · {e.difficulty}<SourceTag source={fs.difficulty} /></div>}
          <div><span className="text-faint">Pattern</span> · {e.pattern}<SourceTag source={fs.pattern} /></div>
          <div><span className="text-faint">Measured in</span> · {e.measure === "hold" ? "seconds per hold" : e.measure === "time" ? "time" : "reps"}{range && ` · default ${range}`}<SourceTag source={fs.default_range} /></div>
          <div><span className="text-faint">Logged</span> · {e.sets_logged} {e.sets_logged === 1 ? "set" : "sets"}</div>
        </div>
      </section>
      <section className="card col-span-12 p-5 md:col-span-7">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="exercise-title" className="text-xl font-semibold text-ink">{e.name}</h2>
            {e.aliases && e.aliases.length > 0 && <p className="mt-0.5 text-xs text-faint">Also: {e.aliases.slice(0, 4).join(", ")}</p>}
          </div>
          <button type="button" className="btn-primary shrink-0" onClick={onLog}>Log it</button>
        </div>
        <h3 className="mt-5 text-[11px] uppercase tracking-wider text-faint">Muscles hit<SourceTag source={fs.muscles} /></h3>
        {e.muscles.length === 0 ? (
          <p className="mt-1 text-sm text-muted">No muscle load (stretching, meditation and similar).</p>
        ) : (
          <ul className="mt-2 space-y-1.5">
            {e.muscles.map((m) => (
              <li key={m.muscle} className="flex items-center gap-3 text-sm">
                <span className="w-28 shrink-0 text-ink">{muscleLabel(m.muscle)}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-panel-2" aria-hidden>
                  <span className="block h-full rounded-full bg-accent" style={{ width: `${m.weight * 100}%`, opacity: 0.35 + m.weight * 0.65 }} />
                </span>
                <span className="w-24 shrink-0 text-right text-xs text-muted">{m.weight >= 1 ? "primary" : m.weight >= 0.5 ? "secondary" : "minor"} ×{m.weight}</span>
              </li>
            ))}
          </ul>
        )}
        {e.skills.length > 0 && (
          <>
            <h3 className="mt-5 text-[11px] uppercase tracking-wider text-faint">Skill trees</h3>
            <ul className="mt-2 flex flex-wrap gap-2">
              {e.skills.map((s) => (
                <li key={`${s.skill_key}-${s.role}`}>
                  <button type="button" className="chip border-accent/40 text-accent hover:bg-accent/10" onClick={() => onOpenSkill(s.skill_key)}>
                    {s.skill_name}{s.role === "step" ? ` · step: ${s.step_name}` : " · feeder"}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
        <h3 className="mt-5 text-[11px] uppercase tracking-wider text-faint">How to do it<SourceTag source={fs.instructions} /></h3>
        {e.instructions.length === 0 ? (
          <p className="mt-1 text-sm text-muted">No instructions on file.</p>
        ) : (
          <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-sm leading-relaxed text-ink">
            {e.instructions.map((step, i) => <li key={i}>{step}</li>)}
          </ol>
        )}
        <p className="mt-5 text-[11px] text-faint">
          {e.source === "free-exercise-db" || e.source_ref ? "Instructions and image: free-exercise-db (public domain). " : ""}
          {e.field_sources.image?.startsWith("similar:")
            ? `Picture: a similar movement (${e.field_sources.image.slice("similar:".length)}) from free-exercise-db (public domain). `
            : ""}
          Muscle weights are estimates used by the recovery model.
        </p>
        {e.attribution.length > 0 && (
          <div className="mt-3 text-[11px] text-faint">
            Researched online:{" "}
            {e.attribution.map((a, i) => (
              <span key={a.url}>{i > 0 && ", "}<a className="text-accent underline-offset-2 hover:underline" href={a.url} target="_blank" rel="noreferrer">{a.title}</a> ({a.source}, {a.license})</span>
            ))}
          </div>
        )}
      </section>
    </article>
  );
}
