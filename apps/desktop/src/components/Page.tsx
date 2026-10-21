/**
 * Page building blocks shared by the redesigned screens.
 *
 * - `PageGrid`: the 12-column grid every screen sits on.
 * - `KpiStrip` / `KpiTile`: the row of headline numbers at the top of a screen.
 * - `Panel`: a titled card that owns its loading, error and empty states, so every card on
 *   every screen shows them the same way (skeleton lines, a compact error with Retry, a
 *   dashed empty box with one next action).
 *
 * Panels and tiles enter with a short staggered rise (transform + opacity). With Reduce
 * motion the rise is a no-op and the stagger delay is dropped (see `.rise-in` in index.css).
 */
import type { CSSProperties, ReactNode } from "react";

import { Skeleton } from "./Skeleton";
import { Empty, ErrorState } from "./States";

const stagger = (index: number): CSSProperties => ({ ["--i" as string]: index }) as CSSProperties;

export function PageGrid({ children, label }: { children: ReactNode; label?: string }) {
  return (
    <div className="grid grid-cols-12 gap-5" aria-label={label}>
      {children}
    </div>
  );
}

export type Tone = "ink" | "good" | "warn" | "bad" | "accent" | "xp";

const TONE_CLASS: Record<Tone, string> = {
  ink: "text-ink",
  good: "text-good",
  warn: "text-warn",
  bad: "text-bad",
  accent: "text-accent",
  xp: "text-xp",
};

export function KpiStrip({ children, label = "Headline numbers" }: { children: ReactNode; label?: string }) {
  return (
    <section className="col-span-12 grid grid-cols-2 gap-3 md:grid-cols-4" aria-label={label}>
      {children}
    </section>
  );
}

export function KpiTile({ label, value, sub, tone = "ink", index = 0, loading = false }: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: Tone;
  index?: number;
  loading?: boolean;
}) {
  return (
    <div className="card rise-in px-4 py-3" style={stagger(index)}>
      <div className="text-[11px] font-medium uppercase tracking-wider text-muted">{label}</div>
      {loading ? (
        <Skeleton className="mt-2 h-6 w-20" />
      ) : (
        <div className={`mt-1 text-xl font-semibold tabular-nums ${TONE_CLASS[tone]}`}>{value}</div>
      )}
      {sub && !loading && <div className="mt-0.5 truncate text-xs text-muted">{sub}</div>}
    </div>
  );
}

export interface PanelState {
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  /** When set (and not loading or failed), the panel shows this empty state instead of children. */
  empty?: { title: string; hint?: string; action?: { label: string; onClick: () => void } } | null;
}

export function Panel({ id, title, action, hint, className = "col-span-12", index = 0, skeletonLines = 3, hover = true, children, ...state }: {
  id: string;
  title: ReactNode;
  action?: ReactNode;
  hint?: ReactNode;
  className?: string;
  index?: number;
  skeletonLines?: number;
  hover?: boolean;
  children?: ReactNode;
} & PanelState) {
  const titleId = `${id}-title`;
  let body: ReactNode;
  if (state.loading) {
    body = (
      <div role="status" aria-busy="true" className="space-y-3">
        <span className="sr-only">Loading…</span>
        {Array.from({ length: skeletonLines }, (_, i) => (
          <Skeleton key={i} className={`h-4 ${i === skeletonLines - 1 ? "w-2/3" : "w-full"}`} />
        ))}
      </div>
    );
  } else if (state.error) {
    body = <ErrorState compact message={state.error} onRetry={state.onRetry} />;
  } else if (state.empty) {
    body = <Empty {...state.empty} />;
  } else {
    body = children;
  }
  return (
    <section className={`card rise-in self-start p-5 ${hover ? "card-hover" : ""} ${className}`} style={stagger(index)} aria-labelledby={titleId} data-panel={id}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id={titleId} className="card-title">{title}</h2>
          {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      {body}
    </section>
  );
}
