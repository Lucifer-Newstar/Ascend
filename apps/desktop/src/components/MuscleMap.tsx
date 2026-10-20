/**
 * Front + back muscle map coloured by recovery/volume status.
 *
 * Body artwork: react-muscle-highlighter 1.2.0 (MIT licence,
 * https://github.com/soroojshehryar/react-muscle-highlighter). See README credits.
 */
import type { MuscleState, MuscleStatus } from "@ascend/shared";
import { useMemo, useState } from "react";
import Body, { type ExtendedBodyPart, type Slug } from "react-muscle-highlighter";

import { readyAtLabel } from "../lib/format";
import { cssVar } from "../lib/theme";
import { STATUS_COLORS, STATUS_LABELS, regionsForSlug, statusBySlug } from "../lib/muscleMap";

const LEGEND: MuscleStatus[] = ["under", "optimal", "recovering", "over", "no_data"];

/** "No data" follows the theme (a dark blob on a light page reads as a warning). */
function statusColor(status: MuscleStatus): string {
  return status === "no_data" ? cssVar("--color-nodata", STATUS_COLORS.no_data) : STATUS_COLORS[status];
}

export function MuscleMap({ muscles, scale = 0.86 }: { muscles: MuscleState[]; scale?: number }) {
  const [selected, setSelected] = useState<string | null>(null);
  const bySlug = useMemo(() => statusBySlug(muscles), [muscles]);
  const data: ExtendedBodyPart[] = useMemo(
    () => [...bySlug.entries()].map(([slug, status]) => ({ slug: slug as Slug, color: statusColor(status) })),
    [bySlug],
  );
  const regions = selected ? regionsForSlug(muscles, selected) : [];
  const attention = muscles
    .filter((m) => m.status === "over" || m.status === "recovering" || m.status === "under")
    .sort((a, b) => ({ over: 0, recovering: 1, under: 2 })[a.status as "over"] - ({ over: 0, recovering: 1, under: 2 })[b.status as "over"])
    .slice(0, 5);

  const common = {
    data,
    scale,
    // The artwork needs literal colours, so read the current theme's tokens.
    border: cssVar("--color-line-2", "#2a3446"),
    defaultFill: cssVar("--color-map-fill", "#1a2232"),
    onBodyPartPress: (part: ExtendedBodyPart) => setSelected(part.slug ?? null),
  };

  return (
    <div className="flex gap-5">
      <div className="flex shrink-0 gap-2" aria-label="Muscle map, front and back">
        <div className="text-center">
          <Body {...common} side="front" />
          <div className="mt-1 text-[10px] uppercase tracking-widest text-faint">Front</div>
        </div>
        <div className="text-center">
          <Body {...common} side="back" />
          <div className="mt-1 text-[10px] uppercase tracking-widest text-faint">Back</div>
        </div>
      </div>
      <div className="min-w-0 flex-1 space-y-4">
        <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs">
          {LEGEND.map((s) => (
            <li key={s} className="flex items-center gap-2 text-muted">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: statusColor(s) }} />
              {STATUS_LABELS[s]}
            </li>
          ))}
        </ul>
        {regions.length > 0 ? (
          <div className="rounded-lg border border-line bg-panel-2 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-accent">{selected}</span>
              <button type="button" className="text-xs text-faint hover:text-ink" onClick={() => setSelected(null)}>close</button>
            </div>
            {regions.map((r) => <RegionRow key={r.key} m={r} />)}
          </div>
        ) : (
          <div>
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted">Needs attention</div>
            {attention.length === 0 ? (
              <p className="text-xs text-faint">Log a workout to see per-muscle load. Click a muscle for details.</p>
            ) : (
              attention.map((m) => <RegionRow key={m.key} m={m} />)
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function RegionRow({ m }: { m: MuscleState }) {
  const band = `${m.weekly_low}–${m.weekly_high}`;
  return (
    <div className="flex items-center justify-between gap-2 border-b border-line/60 py-1.5 text-xs last:border-0">
      <span className="flex min-w-0 items-center gap-2">
        <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: STATUS_COLORS[m.status] }} />
        <span className="truncate text-ink">{m.label}</span>
      </span>
      <span className="shrink-0 text-right text-muted" title="Effective sets in the last 7 days vs the weekly target band (estimate)">
        {m.es_7d} / {band} sets · {Math.round(m.readiness * 100)}%{m.status === "recovering" ? ` · ${readyAtLabel(m.ready_at)}` : ""}
      </span>
    </div>
  );
}
