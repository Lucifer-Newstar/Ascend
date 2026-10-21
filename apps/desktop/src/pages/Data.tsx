/**
 * Import & export (12-column grid): a three-step strip (choose, check, imported) above the
 * import card (8 columns) and the export and "what gets imported" cards (4 columns).
 */
import { useState, type CSSProperties } from "react";

import type { ImportReport, ImportSource } from "@ascend/shared";

import { api } from "../api/client";
import { FileDrop } from "../components/FileDrop";
import { IconDownload } from "../components/Icons";
import { ImportReportCard } from "../components/ImportReportCard";
import { PageGrid } from "../components/Page";
import { Segmented } from "../components/Segmented";
import { useToast } from "../components/Toast";
import { readTextFile, saveFile, todayStamp } from "../lib/files";

const stagger = (i: number): CSSProperties => ({ ["--i" as string]: i }) as CSSProperties;

type Step = "pick" | "checking" | "preview" | "importing" | "done";

/** Import from Strong / Hevy (dry run first, then confirm) and export everything. */
export function DataPage({ onChanged, onOpenHistory }: { onChanged: () => void; onOpenHistory: () => void }) {
  const toast = useToast();
  const [source, setSource] = useState<ImportSource>("strong");
  const [unit, setUnit] = useState<"kg" | "lb">("kg");
  const [warmups, setWarmups] = useState(false);
  const [file, setFile] = useState<{ name: string; text: string } | null>(null);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [step, setStep] = useState<Step>("pick");
  const [error, setError] = useState<string | null>(null);

  const options = (text: string, dry_run: boolean) => ({ csv: text, dry_run, unit, include_warmups: warmups });

  async function check(text: string) {
    setStep("checking");
    setError(null);
    setReport(null);
    try {
      setReport(await api.importCsv(source, options(text, true)));
      setStep("preview");
    } catch (e) {
      setError((e as Error).message);
      setStep("pick");
    }
  }

  async function pick(f: File) {
    try {
      const text = await readTextFile(f);
      setFile({ name: f.name, text });
      await check(text);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function commit() {
    if (!file) return;
    setStep("importing");
    try {
      const done = await api.importCsv(source, options(file.text, false));
      setReport(done);
      setStep("done");
      toast(`Imported ${done.workouts} workout${done.workouts === 1 ? "" : "s"}`, "info");
      onChanged();
    } catch (e) {
      setError((e as Error).message);
      setStep("preview");
    }
  }

  function reset() {
    setFile(null);
    setReport(null);
    setError(null);
    setStep("pick");
  }

  // Changing an option re-runs the preview, so the report always matches what Import will do.
  function changeOption(apply: () => void) {
    apply();
    setReport(null);
    if (step !== "pick") setStep("pick");
  }

  async function exportData(kind: "json" | "workouts" | "meals") {
    try {
      const stamp = todayStamp();
      const content = kind === "json" ? JSON.stringify(await api.exportJson(), null, 2) : await api.exportCsv(kind);
      const name = kind === "json" ? `ascend-export-${stamp}.json` : `ascend-${kind}-${stamp}.csv`;
      const path = await saveFile(name, content);
      if (path) toast(`Exported ${name}`, "info");
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  const busy = step === "checking" || step === "importing";

  return (
    <PageGrid label="Import and export">
      <ImportSteps step={step} />
      <section className="card rise-in col-span-12 space-y-5 self-start p-5 xl:col-span-8" style={stagger(1)} aria-labelledby="import-title">
        <div>
          <h2 id="import-title" className="card-title">Import from another app</h2>
          <p className="mt-1 text-sm text-muted">
            Bring your history from Strong or Hevy. You see exactly what will be added before anything is saved,
            and importing the same file twice adds nothing.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <Segmented
            label="Import from"
            value={source}
            disabled={busy}
            options={[{ value: "strong", label: "Strong" }, { value: "hevy", label: "Hevy" }]}
            onChange={(v) => changeOption(() => setSource(v))}
          />
          {source === "strong" && (
            <div className="flex items-center gap-2 text-xs text-muted">
              Weights in
              <Segmented
                label="Weight unit in the file"
                value={unit}
                disabled={busy}
                options={[{ value: "kg", label: "kg" }, { value: "lb", label: "lb" }]}
                onChange={(v) => changeOption(() => setUnit(v))}
              />
            </div>
          )}
          <label className="flex items-center gap-2 text-xs text-muted">
            <input
              type="checkbox"
              className="h-4 w-4 accent-accent"
              checked={warmups}
              disabled={busy}
              onChange={(e) => changeOption(() => setWarmups(e.target.checked))}
            />
            Include warm-up sets
          </label>
        </div>
        {source === "strong" && (
          <p className="text-xs text-muted">
            The unit only matters for Strong's newer export, which doesn't say. The classic export carries its own unit.
          </p>
        )}

        {step !== "done" && (
          <FileDrop
            label={source === "strong" ? "Drop your Strong export (.csv) or click to choose" : "Drop your Hevy export (.csv) or click to choose"}
            hint={source === "strong" ? "Strong: Settings → Export Strong Data" : "Hevy: Profile → Settings → Export & Import Data"}
            fileName={file?.name}
            disabled={busy}
            onFile={pick}
          />
        )}

        {error && (
          <p role="alert" className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">{error}</p>
        )}
        {step === "checking" && <p className="text-sm text-muted" role="status">Checking the file…</p>}
        {file && step === "pick" && !error && (
          <button type="button" className="btn-ghost" onClick={() => check(file.text)}>Check {file.name} again</button>
        )}

        {report && <ImportReportCard report={report} />}

        {(step === "preview" || step === "importing") && report && (
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-primary" disabled={report.workouts === 0 || busy} onClick={commit}>
              {step === "importing" ? "Importing…" : `Import ${report.workouts} workout${report.workouts === 1 ? "" : "s"}`}
            </button>
            <button type="button" className="btn-ghost" disabled={busy} onClick={reset}>Cancel</button>
          </div>
        )}
        {step === "done" && (
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-primary" onClick={onOpenHistory}>See it in History</button>
            <button type="button" className="btn-ghost" onClick={reset}>Import another file</button>
          </div>
        )}
      </section>

      <div className="col-span-12 space-y-5 xl:col-span-4">
        <section className="card rise-in p-5" style={stagger(2)} aria-labelledby="export-title">
          <h2 id="export-title" className="card-title mb-1">Export your data</h2>
          <p className="mb-3 text-sm text-muted">Everything you logged, in open formats. Yours to keep or take elsewhere.</p>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-ghost" onClick={() => exportData("json")}><IconDownload width={16} height={16} /> Everything (JSON)</button>
            <button type="button" className="btn-ghost" onClick={() => exportData("workouts")}><IconDownload width={16} height={16} /> Workouts (CSV)</button>
            <button type="button" className="btn-ghost" onClick={() => exportData("meals")}><IconDownload width={16} height={16} /> Meals (CSV)</button>
          </div>
        </section>
        <section className="card rise-in p-5 text-xs leading-relaxed text-muted" style={stagger(3)} aria-labelledby="what-title">
          <h2 id="what-title" className="card-title mb-2">What gets imported</h2>
          <ul className="list-inside list-disc space-y-1">
            <li>Workouts, sets, weights, reps, RPE, and time and distance for cardio.</li>
            <li>Exercise names are matched to the ASCEND library. Names it can't match are listed and skipped, never guessed.</li>
            <li>Imported sets count towards your PRs and muscle map, but they don't earn XP.</li>
          </ul>
        </section>
      </div>
    </PageGrid>
  );
}

const STEPS = [
  { key: "pick", label: "Choose a file", hint: "Strong or Hevy CSV" },
  { key: "preview", label: "Check the preview", hint: "Nothing saved yet" },
  { key: "done", label: "Imported", hint: "Duplicates skipped" },
] as const;

/** Where the import stands: choose, check, imported. The current step is marked for screen readers. */
function ImportSteps({ step }: { step: string }) {
  const at = step === "done" ? 2 : step === "preview" || step === "importing" ? 1 : 0;
  return (
    <ol className="col-span-12 grid grid-cols-3 gap-3" aria-label="Import steps">
      {STEPS.map((s, i) => (
        <li key={s.key} aria-current={i === at ? "step" : undefined}
          className={`card rise-in flex items-center gap-3 px-4 py-3 ${i === at ? "border-accent/60" : ""}`} style={stagger(0)}>
          <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-semibold ${i < at ? "bg-good text-on-accent" : i === at ? "bg-accent text-on-accent" : "bg-panel-3 text-muted"}`}>
            {i < at ? "✓" : i + 1}
          </span>
          <span className="min-w-0">
            <span className={`block truncate text-sm font-medium ${i === at ? "text-ink" : "text-muted"}`}>{s.label}</span>
            <span className="block truncate text-xs text-muted">{s.hint}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}
