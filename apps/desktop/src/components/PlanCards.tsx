/**
 * Weekly review and deload advice, both produced by deterministic rules in the sidecar.
 * Proposals are suggestions only: nothing here changes the plan without a click.
 */
import { useState } from "react";

import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import { ErrorState, Loading } from "./States";
import { SystemWindow } from "./SystemWindow";
import { useToast } from "./Toast";

const shortDate = (iso: string) => new Date(iso + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" });

export function WeeklyReviewCard({ refreshKey }: { refreshKey: number }) {
  const r = useApi(api.weeklyReview, [refreshKey]);
  return (
    <section className="card card-hover p-5" aria-labelledby="review-title">
      <div className="mb-2 flex items-center justify-between">
        <h2 id="review-title" className="card-title">Weekly review</h2>
        {r.data && <span className="text-[11px] text-faint">{shortDate(r.data.week_start)} – {shortDate(r.data.week_end)}</span>}
      </div>
      {r.loading && !r.data ? <Loading /> : r.error ? <ErrorState message={r.error} onRetry={r.reload} /> : r.data && (
        <>
          <div className="mb-3 flex items-baseline gap-2">
            <span className="font-display text-2xl font-bold text-ink">{r.data.sessions_done}/{r.data.sessions_planned}</span>
            <span className="text-xs text-muted">sessions this week</span>
          </div>
          {r.data.top.length === 0 ? (
            <p className="text-sm text-muted">Nothing to change: training and recovery look on track.</p>
          ) : (
            <ul className="space-y-2">
              {r.data.top.map((f) => (
                <li key={f.code + f.title} className="rounded-lg border border-line bg-panel-2 p-3">
                  <div className="text-sm font-medium text-ink">{f.title}</div>
                  <div className="mt-0.5 text-xs text-muted">{f.detail}</div>
                  {f.proposal && <div className="mt-1.5 text-xs text-accent">Suggestion: {f.proposal}</div>}
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-[10px] text-faint">
            {r.data.summary_source === "model" ? "Summary worded by the local AI from these numbers" : "Rule-based summary"} · {r.data.algo_version}
          </p>
        </>
      )}
    </section>
  );
}

export function DeloadCard({ refreshKey }: { refreshKey: number }) {
  const [tick, setTick] = useState(0);
  const d = useApi(api.deload, [refreshKey, tick]);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function start() {
    setBusy(true);
    try {
      await api.startDeload();
      toast("Deload week started: lighter targets until Sunday", "info");
      setTick((t) => t + 1);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  const content = d.loading && !d.data ? <Loading /> : d.error ? <ErrorState message={d.error} onRetry={d.reload} /> : d.data && (
    <>
      <p className={`text-sm ${d.data.recommended ? "text-warn" : d.data.kind === "active" ? "text-accent" : "text-ink"}`}>
        {d.data.kind === "active"
          ? `Deload week in progress (from ${shortDate(d.data.deload_week ?? "")}).`
          : d.data.recommended
            ? d.data.kind === "planned"
              ? `Planned deload: ${d.data.training_weeks} hard weeks in a row.`
              : "Your recovery signals suggest an easier week."
            : "No deload needed right now."}
      </p>
      {d.data.guidance && <p className="mt-1 text-xs text-muted">{d.data.guidance}</p>}
      <ul className="mt-3 space-y-1.5 text-xs">
        {d.data.signals.map((s) => (
          <li key={s.code} className="flex items-start gap-2">
            <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${s.active ? "bg-warn" : "bg-line-2"}`} aria-hidden="true" />
            <span className={s.active ? "text-ink" : "text-muted"}>
              <span className="sr-only">{s.active ? "Active: " : "Not active: "}</span>
              {s.detail}
            </span>
          </li>
        ))}
      </ul>
    </>
  );

  // A recommended deload is a System event, so it gets the System window; otherwise a plain card.
  if (d.data?.recommended && d.data.kind !== "active") {
    return (
      <SystemWindow variant="warning" title="Deload notice" testId="deload-notice"
        actions={<button type="button" className="btn-primary" disabled={busy} onClick={start}>Start deload week</button>}>
        {content}
      </SystemWindow>
    );
  }
  return (
    <section className="card card-hover p-5" aria-labelledby="deload-title">
      <h2 id="deload-title" className="card-title mb-2">Deload check</h2>
      {content}
    </section>
  );
}
