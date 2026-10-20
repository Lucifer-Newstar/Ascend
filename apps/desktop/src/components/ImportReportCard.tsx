import type { ImportReport } from "@ascend/shared";

const FORMAT_LABEL: Record<ImportReport["format"], string> = {
  strong_csv: "Strong (classic export)",
  strong_csv_2025: "Strong (2025 export)",
  hevy_csv: "Hevy",
  ascend_plan_csv: "ASCEND plan",
};

function Stat({ label, value, tone = "text-ink" }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-lg bg-panel-2 px-3 py-2">
      <div className={`font-display text-2xl font-semibold ${tone}`}>{value}</div>
      <div className="text-[11px] uppercase tracking-wider text-muted">{label}</div>
    </div>
  );
}

/** What an import will do (dry run) or did. Unmatched names are shown, never hidden. */
export function ImportReportCard({ report }: { report: ImportReport }) {
  const matched = Object.entries(report.matched_exercises);
  const nothing = report.workouts === 0;
  return (
    <section aria-label="Import report" className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">
          {report.dry_run ? "Ready to import" : "Imported"} · {FORMAT_LABEL[report.format]}
        </h3>
        {report.dry_run && <span className="chip">Preview: nothing saved yet</span>}
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Workouts" value={report.workouts} tone="text-accent" />
        <Stat label="Sets" value={report.sets} />
        <Stat label="Already imported" value={report.skipped_duplicates} tone="text-muted" />
        <Stat label="Warm-ups skipped" value={report.skipped_warmups} tone="text-muted" />
      </div>
      {nothing && (
        <p className="text-sm text-muted">
          {report.skipped_duplicates > 0
            ? "Every workout in this file is already in ASCEND."
            : "No sets in this file could be imported."}
        </p>
      )}
      {report.unmatched_exercises.length > 0 && (
        <div className="rounded-lg border border-warn/40 bg-warn/10 p-3">
          <div className="text-xs font-semibold text-warn">
            {report.unmatched_exercises.length} exercise{report.unmatched_exercises.length === 1 ? "" : "s"} not in the
            ASCEND library (their sets are skipped)
          </div>
          <ul className="mt-1 list-inside list-disc text-xs text-muted">
            {report.unmatched_exercises.map((name) => <li key={name}>{name}</li>)}
          </ul>
        </div>
      )}
      {report.warnings.length > 0 && (
        <details className="text-xs text-muted">
          <summary className="cursor-pointer text-ink">{report.warnings.length} row{report.warnings.length === 1 ? "" : "s"} dropped</summary>
          <ul className="mt-1 list-inside list-disc">{report.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </details>
      )}
      {matched.length > 0 && (
        <details className="text-xs text-muted">
          <summary className="cursor-pointer text-ink">How names were matched ({matched.length})</summary>
          <table className="mt-2 w-full text-left">
            <thead className="text-faint">
              <tr><th className="py-1 font-medium">In the file</th><th className="py-1 font-medium">In ASCEND</th></tr>
            </thead>
            <tbody>
              {matched.map(([from, to]) => (
                <tr key={from} className="border-t border-line"><td className="py-1">{from}</td><td className="py-1 text-ink">{to}</td></tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </section>
  );
}
