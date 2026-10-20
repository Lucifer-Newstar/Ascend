/**
 * "Add your own exercise": type a name, ASCEND proposes every field (library match,
 * rules, the local model if installed) with a confidence for each. When the offline
 * data is not enough it says so and offers online research (wger.de + Wikipedia):
 * Allow once / Always (turns the setting on) / No. Online findings arrive as a research
 * report with a link per field; the user reviews and confirms. Every field shows where
 * its value came from; anything the user changes becomes "You".
 */
import type { Confidence, CustomExerciseIn, Difficulty, ExerciseAnalysis, FieldSource, Measure, ResearchReport, Section } from "@ascend/shared";
import { useState, type ReactNode } from "react";

import { api } from "../api/client";
import { IconPlus, IconTrash } from "../components/Icons";
import { useToast } from "../components/Toast";
import { MUSCLE_LABEL } from "../lib/muscles";
import { usePrefs } from "../lib/prefs";
import { SECTION_TYPE_LABEL, SOURCE_LABEL } from "./Library";

export const EQUIPMENT_OPTIONS = [
  "bodyweight", "barbell", "dumbbell", "kettlebell", "cable", "machine", "band", "rings",
  "bar", "bench", "medicine_ball", "exercise_ball", "none", "other",
] as const;
const PATTERNS = ["push", "pull", "squat", "hinge", "lunge", "core", "isometric", "carry", "olympic", "locomotion", "mobility", "other"] as const;
const SECTIONS: Section[] = ["gym", "calisthenics", "cardio", "martial_arts", "flexibility", "meditation"];
const label = (s: string) => s.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

const AI_TEXT: Record<string, string> = {
  ok: "Local AI filled in",
  off: "Local AI is off in Settings: rules only",
  unavailable: "Local AI model not installed: rules only",
  error: "Local AI did not answer: rules only",
  invalid: "Local AI's answer did not pass the checks: rules only",
};
const ONLINE_TEXT: Record<string, string> = {
  ok: "Online research filled in",
  not_found: "Online research found nothing under this name",
  offline: "No internet connection: offline details only",
  timeout: "Online research timed out: offline details only",
  rate_limited: "wger.de asked to slow down: try again in a minute",
  error: "Online research failed: offline details only",
};
const CALL_TEXT: Record<string, string> = {
  ok: "found",
  not_found: "nothing under this name",
  offline: "no connection",
  timeout: "timed out",
  rate_limited: "rate limited",
  error: "failed",
  skipped: "not asked (no connection)",
};
const FIELD_NAME: Record<string, string> = {
  section: "type", equipment: "equipment", measure: "measure", pattern: "movement pattern", muscles: "muscles",
};

export function toPayload(a: ExerciseAnalysis): CustomExerciseIn {
  return { name: a.name, ...a.proposal, field_sources: { ...a.field_sources }, attribution: a.attribution };
}

export function AddExerciseView({ onBack, onCreated, onOpenExisting }: {
  onBack: () => void;
  onCreated: (id: number) => void;
  onOpenExisting: (id: number) => void;
}) {
  const { settings, update } = usePrefs();
  const toast = useToast();
  const [name, setName] = useState("");
  const [equipment, setEquipment] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [researching, setResearching] = useState(false);
  const [runs, setRuns] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<ExerciseAnalysis | null>(null);
  const [draft, setDraft] = useState<CustomExerciseIn | null>(null);

  async function run(opts: { online?: boolean; allow_once?: boolean } = {}) {
    if (name.trim().length < 2) return;
    setBusy(true);
    setResearching(Boolean(opts.online));
    setError(null);
    try {
      const body: Parameters<typeof api.analyzeExercise>[0] = { name: name.trim(), equipment: equipment || null, notes, online: Boolean(opts.online) };
      if (opts.allow_once) body.allow_once = true;
      const a = await api.analyzeExercise(body);
      setAnalysis(a);
      setDraft(toPayload(a));
      setRuns((n) => n + 1);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
      setResearching(false);
    }
  }

  function analyse(e: React.FormEvent) {
    e.preventDefault();
    void run();
  }

  /** The three answers to "Look it up online?". */
  async function research(choice: "once" | "always") {
    if (choice === "always" && !settings.online_lookup) {
      try {
        await update({ online_lookup: true });
        toast("Online research: on", "info");
      } catch (err) {
        setError((err as Error).message);
        return;
      }
    }
    await run({ online: true, allow_once: choice === "once" });
  }

  async function save() {
    if (!draft) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createExercise(draft);
      toast(`Added ${created.name} to your library`, "xp");
      onCreated(created.id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-4xl space-y-4">
      <button type="button" className="btn-ghost" onClick={onBack}>← All exercises</button>
      <section className="card p-5" aria-labelledby="add-title">
        <h2 id="add-title" className="card-title">Add your own exercise</h2>
        <p className="mt-1 text-xs text-muted">ASCEND suggests the details and shows where each one came from. You check them before anything is saved.</p>
        <form className="mt-4 grid gap-3 md:grid-cols-[2fr_1fr]" onSubmit={analyse}>
          <label className="block">
            <span className="mb-1.5 block text-xs text-muted">Exercise name</span>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Banded Pallof hold" maxLength={80} required minLength={2} />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs text-muted">Equipment (optional)</span>
            <select className="input" value={equipment} onChange={(e) => setEquipment(e.target.value)}>
              <option value="">Let ASCEND guess</option>
              {EQUIPMENT_OPTIONS.map((x) => <option key={x} value={x}>{label(x)}</option>)}
            </select>
          </label>
          <label className="block md:col-span-2">
            <span className="mb-1.5 block text-xs text-muted">Notes for the local AI (optional)</span>
            <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={300} placeholder="e.g. anti-rotation core hold with a band" />
          </label>
          <div className="flex flex-wrap items-center gap-3 md:col-span-2">
            {settings.online_lookup ? (
              <span className="text-xs text-muted">Online research is on: when the offline details are not enough, ASCEND sends only the name to wger.de and Wikipedia.</span>
            ) : (
              <span className="text-xs text-faint">Online research is off. Everything runs on this PC.</span>
            )}
            <button type="submit" className="btn btn-primary ml-auto" disabled={busy || name.trim().length < 2}>
              {busy && !analysis ? "Checking…" : analysis ? "Check again" : "Suggest details"}
            </button>
          </div>
        </form>
        {error && <p role="alert" className="mt-3 text-sm text-bad">{error}</p>}
      </section>

      {analysis && draft && (
        <OnlineOffer
          key={runs}
          analysis={analysis}
          settingOn={Boolean(settings.online_lookup)}
          busy={busy}
          researching={researching}
          onResearch={research}
        />
      )}
      {analysis?.research && draft && analysis.offline && (
        <ResearchReportCard report={analysis.research} analysis={analysis} draft={draft} setDraft={setDraft} />
      )}
      {analysis && draft && (
        <Review analysis={analysis} draft={draft} setDraft={setDraft} onSave={save} busy={busy} onOpenExisting={onOpenExisting} />
      )}
    </div>
  );
}

function Review({ analysis: a, draft, setDraft, onSave, busy, onOpenExisting }: {
  analysis: ExerciseAnalysis;
  draft: CustomExerciseIn;
  setDraft: (d: CustomExerciseIn) => void;
  onSave: () => void;
  busy: boolean;
  onOpenExisting: (id: number) => void;
}) {
  // Any edit makes that field the user's own.
  const edit = <K extends keyof CustomExerciseIn>(key: K, value: CustomExerciseIn[K], source = String(key)) =>
    setDraft({ ...draft, [key]: value, field_sources: { ...draft.field_sources, [source]: "user" } });
  const src = (key: string) => draft.field_sources[key] as FieldSource | undefined;
  // Confidence belongs to the proposed value; once the source changes (an edit, or the
  // offline guess kept over the research) it no longer applies as is.
  const conf = (key: string) => (draft.field_sources[key] === a.field_sources[key] ? a.confidence?.[key] as Confidence | undefined : undefined);
  const unit = draft.measure === "hold" ? "seconds" : "reps";
  const others = a.matches.filter((m) => m.id !== a.duplicate_of?.id);
  return (
    <>
      {a.duplicate_of && (
        <section className="card border-warn/50 p-4" role="alert">
          <p className="text-sm text-ink"><strong>{a.duplicate_of.name}</strong> is already in the library under this name.</p>
          <button type="button" className="btn-ghost mt-2" onClick={() => onOpenExisting(a.duplicate_of!.id)}>Open {a.duplicate_of.name}</button>
        </section>
      )}
      {others.length > 0 && (
        <section className="card p-4" aria-labelledby="similar-title">
          <h3 id="similar-title" className="text-[11px] uppercase tracking-wider text-faint">Similar exercises already in the library</h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {others.map((m) => (
              <li key={m.id}>
                <button type="button" className="chip hover:border-accent hover:text-accent" onClick={() => onOpenExisting(m.id)}>
                  {m.name} <span className="text-faint">· {Math.round(m.score * 100)}% match</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      <section className="card p-5" aria-labelledby="review-title">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 id="review-title" className="card-title">Check the details</h3>
          <p className="text-xs text-muted" role="status">
            {AI_TEXT[a.ai.status] ?? a.ai.status}{a.ai.status === "ok" ? ` ${a.ai.applied.length} field${a.ai.applied.length === 1 ? "" : "s"}` : ""}
            {ONLINE_TEXT[a.online.status] ? ` · ${ONLINE_TEXT[a.online.status]}` : ""}
          </p>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Field label="Name" source={src("name") ?? "user"}>
            <input className="input" value={draft.name} maxLength={80} onChange={(e) => edit("name", e.target.value)} />
          </Field>
          <Field label="Type" source={src("section")} confidence={conf("section")}>
            <select className="input" value={draft.section} onChange={(e) => edit("section", e.target.value as Section)}>
              {SECTIONS.map((s) => <option key={s} value={s}>{SECTION_TYPE_LABEL[s]}</option>)}
            </select>
          </Field>
          <Field label="Equipment" source={src("equipment")} confidence={conf("equipment")}>
            <select className="input" value={draft.equipment} onChange={(e) => edit("equipment", e.target.value)}>
              {[...new Set([draft.equipment, ...EQUIPMENT_OPTIONS])].map((x) => <option key={x} value={x}>{label(x)}</option>)}
            </select>
          </Field>
          <Field label="Measured in" source={src("measure")} confidence={conf("measure")}>
            <select className="input" value={draft.measure} onChange={(e) => edit("measure", e.target.value as Measure)}>
              <option value="reps">Reps</option>
              <option value="hold">Seconds held (isometric)</option>
              <option value="time">Time (cardio, stretching, mind)</option>
            </select>
          </Field>
          <Field label="Movement pattern" source={src("pattern")} confidence={conf("pattern")}>
            <select className="input" value={draft.pattern} onChange={(e) => edit("pattern", e.target.value)}>
              {PATTERNS.map((p) => <option key={p} value={p}>{label(p)}</option>)}
            </select>
          </Field>
          <Field label="Difficulty" source={src("difficulty")} confidence={conf("difficulty")}>
            <select className="input" value={draft.difficulty ?? ""} onChange={(e) => edit("difficulty", (e.target.value || null) as Difficulty | null)}>
              <option value="">Not set</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="expert">Expert</option>
            </select>
          </Field>
          {draft.measure !== "time" && (
            <Field label={`Target range (${unit})`} source={src("rep_low")}>
              <div className="flex items-center gap-2">
                <input className="input w-24" type="number" min={1} aria-label={`Lowest ${unit}`} value={draft.rep_low ?? ""} onChange={(e) => edit("rep_low", e.target.value ? Number(e.target.value) : null, "rep_low")} />
                <span className="text-faint">to</span>
                <input className="input w-24" type="number" min={1} aria-label={`Highest ${unit}`} value={draft.rep_high ?? ""} onChange={(e) => edit("rep_high", e.target.value ? Number(e.target.value) : null, "rep_low")} />
              </div>
            </Field>
          )}
          {draft.measure === "time" && (
            <Field label="MET (energy, optional)" source={src("met")}>
              <input className="input w-28" type="number" min={1} max={23} step={0.1} value={draft.met ?? ""} onChange={(e) => edit("met", e.target.value ? Number(e.target.value) : null)} />
            </Field>
          )}
        </div>
        <Muscles draft={draft} source={src("muscles")} confidence={conf("muscles")} onChange={(muscles) => edit("muscles", muscles)} />
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Field label="How to do it (one step per line)" source={src("instructions")} confidence={draft.instructions.length ? conf("instructions") : undefined}>
            <textarea className="input min-h-24" value={draft.instructions.join("\n")} onChange={(e) => edit("instructions", e.target.value.split("\n").map((s) => s.trimStart()).filter((s, i, all) => s || i < all.length - 1).slice(0, 12))} />
          </Field>
          <Field label="Other names (comma-separated)" source={src("aliases")}>
            <input className="input" value={draft.aliases.join(", ")} onChange={(e) => edit("aliases", e.target.value.split(",").map((s) => s.trim()).filter(Boolean).slice(0, 10))} />
          </Field>
        </div>
        {draft.attribution.length > 0 && (
          <p className="mt-3 text-xs text-muted">
            Details from{" "}
            {draft.attribution.map((x, i) => (
              <span key={x.url}>
                {i > 0 && "; "}
                <a href={x.url} target="_blank" rel="noreferrer" className="text-accent underline-offset-2 hover:underline">{x.title}</a> ({x.license})
              </span>
            ))}
            .
          </p>
        )}
        <div className="mt-5 flex flex-wrap items-center justify-end gap-3">
          <p className="mr-auto text-xs text-faint">Sources: Library = a similar library exercise, Rules = keyword rules, Local AI = the model on this PC, wger = wger.de (online research), You = your edit. High / Medium / Low = how far each suggestion can be trusted.</p>
          <button type="button" className="btn btn-primary" onClick={onSave} disabled={busy || Boolean(a.duplicate_of) || draft.name.trim().length < 2}>
            {busy ? "Saving…" : "Add to my library"}
          </button>
        </div>
      </section>
    </>
  );
}

/**
 * "Not enough offline data" and the three answers to "Look it up online?". Shown when a
 * core field is low confidence and online research has not filled it yet; the user can
 * also ask for a lookup on any exercise.
 */
function OnlineOffer({ analysis: a, settingOn, busy, researching, onResearch }: {
  analysis: ExerciseAnalysis;
  settingOn: boolean;
  busy: boolean;
  researching: boolean;
  onResearch: (choice: "once" | "always") => void;
}) {
  const [dismissed, setDismissed] = useState(false);
  const [asking, setAsking] = useState(false);
  const status = a.online.status;
  const failed = ["offline", "timeout", "rate_limited", "error"].includes(status);
  const gaps = a.insufficient.map((k) => FIELD_NAME[k] ?? k);
  const offer = a.insufficient.length > 0 && status !== "ok" && status !== "not_found" && !dismissed;
  if (researching) {
    return (
      <section className="card p-4" role="status" aria-live="polite">
        <p className="text-sm text-ink">Researching <strong>{a.name}</strong> on wger.de and Wikipedia…</p>
      </section>
    );
  }
  if (offer || failed) {
    return (
      <section className="card border-warn/50 p-4" aria-labelledby="offer-title">
        <h3 id="offer-title" className="text-sm font-medium text-ink">
          {failed ? (ONLINE_TEXT[status] ?? "Online research failed") : <>Not enough offline data for <strong>{a.name}</strong></>}
        </h3>
        {!failed && (
          <p className="mt-1 text-xs text-muted">
            The library, the keyword rules{a.ai.status === "ok" ? " and the local AI" : ""} could not pin down its {gaps.join(", ")}: those fields are guesses (marked Low below).
            Look it up online? Only the name is sent, to wger.de and Wikipedia, and you check everything before it is saved.
          </p>
        )}
        <div className="mt-3 flex flex-wrap gap-2">
          {settingOn ? (
            <button type="button" className="btn btn-primary px-3 py-1.5 text-xs" disabled={busy} onClick={() => onResearch("always")}>
              {failed ? "Try again" : "Look it up online"}
            </button>
          ) : (
            <>
              <button type="button" className="btn btn-primary px-3 py-1.5 text-xs" disabled={busy} onClick={() => onResearch("once")}>Allow once</button>
              <button type="button" className="btn-ghost px-3 py-1.5 text-xs" disabled={busy} onClick={() => onResearch("always")}>Always (turns on Online research)</button>
            </>
          )}
          <button type="button" className="btn-ghost px-3 py-1.5 text-xs" disabled={busy} onClick={() => setDismissed(true)}>No</button>
        </div>
      </section>
    );
  }
  if (status === "ok") return null;
  return (
    <div className="flex flex-wrap items-center justify-end gap-2 text-xs text-muted">
      {status === "not_found" && <span>Online research found nothing under this name: check the fields below yourself.</span>}
      {status !== "not_found" && !asking && (
        <button type="button" className="btn-ghost px-2 py-1 text-xs" disabled={busy} onClick={() => (settingOn ? onResearch("always") : setAsking(true))}>Look it up online</button>
      )}
      {asking && (
        <span role="group" aria-label="Look it up online?" className="flex flex-wrap items-center gap-2">
          <span>Send only the name to wger.de and Wikipedia?</span>
          <button type="button" className="btn btn-primary px-2 py-1 text-xs" disabled={busy} onClick={() => onResearch("once")}>Allow once</button>
          <button type="button" className="btn-ghost px-2 py-1 text-xs" disabled={busy} onClick={() => onResearch("always")}>Always</button>
          <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={() => setAsking(false)}>No</button>
        </span>
      )}
    </div>
  );
}

/** What online research asked, where, and each field it filled with its link. */
function ResearchReportCard({ report: r, analysis: a, draft, setDraft }: {
  report: ResearchReport;
  analysis: ExerciseAnalysis;
  draft: CustomExerciseIn;
  setDraft: (d: CustomExerciseIn) => void;
}) {
  const offline = a.offline!;
  const keep = (field: string) => {
    const key = field as keyof CustomExerciseIn;
    const value = (offline as unknown as Record<string, unknown>)[field];
    const source = a.offline_sources[field] ?? "rules";
    const sources = { ...draft.field_sources, [field]: source };
    if (field === "measure" && offline.measure !== "time") {
      setDraft({ ...draft, measure: offline.measure, rep_low: offline.rep_low, rep_high: offline.rep_high, field_sources: sources });
      return;
    }
    setDraft({ ...draft, [key]: value, field_sources: sources });
  };
  const kept = (field: string) => draft.field_sources[field] !== "wger";
  const sources = [...new Set(r.calls.map((c) => c.source))];
  return (
    <section className="card p-5" aria-labelledby="report-title">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="report-title" className="card-title">Research report</h3>
        <p className="text-xs text-muted">
          “{r.query}” · {r.consent === "once" ? "allowed once" : "Online research is on"} · {r.fields.length} field{r.fields.length === 1 ? "" : "s"} found
        </p>
      </div>
      <ul className="mt-2 flex flex-wrap gap-2 text-xs" aria-label="Sources asked">
        {sources.map((s) => {
          const calls = r.calls.filter((c) => c.source === s);
          const best = calls.find((c) => c.status === "ok") ?? calls[calls.length - 1];
          return (
            <li key={s} className="chip">
              {s === "wger" ? "wger.de" : "Wikipedia"}: {CALL_TEXT[best.status] ?? best.status}
              <span className="text-faint"> · {calls.length} request{calls.length === 1 ? "" : "s"}</span>
            </li>
          );
        })}
      </ul>
      {r.fields.length > 0 ? (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <caption className="sr-only">Fields found online, with their source and the offline guess</caption>
            <thead className="text-faint">
              <tr>
                <th scope="col" className="py-1.5 pr-3 font-normal">Field</th>
                <th scope="col" className="py-1.5 pr-3 font-normal">Found online</th>
                <th scope="col" className="py-1.5 pr-3 font-normal">Source</th>
                <th scope="col" className="py-1.5 pr-3 font-normal">Offline guess</th>
                <th scope="col" className="py-1.5 font-normal"><span className="sr-only">Choice</span></th>
              </tr>
            </thead>
            <tbody>
              {r.fields.map((f) => (
                <tr key={f.field} className="border-t border-line">
                  <th scope="row" className="py-2 pr-3 font-normal text-muted">{f.label}</th>
                  <td className="py-2 pr-3 text-ink">{f.value}</td>
                  <td className="py-2 pr-3">
                    <a href={f.url} target="_blank" rel="noreferrer" className="text-accent underline-offset-2 hover:underline">wger.de</a>
                  </td>
                  <td className="py-2 pr-3 text-muted">
                    {f.offline_value}
                    {f.conflict && <span className="ml-1 text-warn">(differs)</span>}
                  </td>
                  <td className="py-2 text-right">
                    {f.conflict && !kept(f.field) && (
                      <button type="button" className="btn-ghost px-2 py-0.5 text-xs" onClick={() => keep(f.field)} aria-label={`Keep the offline ${f.label.toLowerCase()}`}>Keep offline</button>
                    )}
                    {kept(f.field) && <span className="text-faint">kept offline</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-3 text-xs text-muted">{a.online.detail || "Nothing found online."} The offline details below stand.</p>
      )}
      {r.summary && (
        <blockquote className="mt-3 border-l-2 border-line-2 pl-3 text-xs text-muted">
          {r.summary}{" "}
          <a href={r.summary_url} target="_blank" rel="noreferrer" className="text-accent underline-offset-2 hover:underline">Wikipedia</a> (CC BY-SA 4.0)
        </blockquote>
      )}
      <p className="mt-3 text-xs text-faint">Nothing is saved yet. Edit anything below, then press “Add to my library”. Each lookup is listed in Settings → Online research.</p>
    </section>
  );
}

const CONFIDENCE_TEXT: Record<Confidence, string> = { high: "High", medium: "Medium", low: "Low" };

function ConfidenceChip({ level }: { level: Confidence | undefined }) {
  if (!level) return null;
  const tone = level === "low" ? "border-warn/60 text-warn" : level === "high" ? "border-good/50 text-good" : "border-line-2 text-faint";
  return (
    <span className={`rounded border px-1.5 py-px text-[10px] uppercase tracking-wide ${tone}`} title={`${CONFIDENCE_TEXT[level]} confidence`}>
      {CONFIDENCE_TEXT[level]}<span className="sr-only"> confidence</span>
    </span>
  );
}

function Field({ label: text, source, confidence, children }: { label: string; source: FieldSource | undefined; confidence?: Confidence; children: ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-2 text-xs text-muted">
        <span>{text}</span>
        {source && <span className="rounded border border-line-2 px-1.5 py-px text-[10px] uppercase tracking-wide text-faint">{SOURCE_LABEL[source] ?? source}</span>}
        {source !== "user" && <ConfidenceChip level={confidence} />}
      </div>
      {/* The control inside carries its own accessible name via the wrapping label. */}
      <label className="block"><span className="sr-only">{text}</span>{children}</label>
    </div>
  );
}

function Muscles({ draft, source, confidence, onChange }: { draft: CustomExerciseIn; source: FieldSource | undefined; confidence?: Confidence; onChange: (m: CustomExerciseIn["muscles"]) => void }) {
  const used = new Set(draft.muscles.map((m) => m.muscle));
  const free = Object.keys(MUSCLE_LABEL).filter((k) => !used.has(k));
  const set = (i: number, patch: Partial<{ muscle: string; weight: number }>) => onChange(draft.muscles.map((m, j) => (j === i ? { ...m, ...patch } : m)));
  return (
    <fieldset className="mt-4">
      <legend className="mb-1.5 flex items-center gap-2 text-xs text-muted">
        Muscles worked
        {source && <span className="rounded border border-line-2 px-1.5 py-px text-[10px] uppercase tracking-wide text-faint">{SOURCE_LABEL[source] ?? source}</span>}
        {source !== "user" && <ConfidenceChip level={confidence} />}
      </legend>
      {draft.muscles.length === 0 && <p className="text-xs text-warn">No muscles yet: add at least one so it counts toward muscle load and quests.</p>}
      <ul className="space-y-2">
        {draft.muscles.map((m, i) => (
          <li key={m.muscle} className="flex items-center gap-2">
            <select className="input w-52" aria-label={`Muscle ${i + 1}`} value={m.muscle} onChange={(e) => set(i, { muscle: e.target.value })}>
              {[m.muscle, ...free].map((k) => <option key={k} value={k}>{MUSCLE_LABEL[k as keyof typeof MUSCLE_LABEL] ?? k}</option>)}
            </select>
            <select className="input w-36" aria-label={`Role of muscle ${i + 1}`} value={m.weight >= 1 ? "1" : "0.5"} onChange={(e) => set(i, { weight: Number(e.target.value) })}>
              <option value="1">Primary</option>
              <option value="0.5">Secondary</option>
            </select>
            <button type="button" className="btn-ghost px-2 py-1" aria-label={`Remove ${MUSCLE_LABEL[m.muscle as keyof typeof MUSCLE_LABEL] ?? m.muscle}`} onClick={() => onChange(draft.muscles.filter((_, j) => j !== i))}>
              <IconTrash width={14} />
            </button>
          </li>
        ))}
      </ul>
      {free.length > 0 && draft.muscles.length < 8 && (
        <button type="button" className="btn-ghost mt-2 px-2 py-1 text-xs" onClick={() => onChange([...draft.muscles, { muscle: free[0], weight: 1 }])}>
          <IconPlus width={14} className="mr-1 inline" /> Add muscle
        </button>
      )}
    </fieldset>
  );
}
