/**
 * Muscle map: one body that flips front/back, coloured either by recovery status
 * (7-day effective sets vs the target band, Fitbod-style) or by training volume
 * over 1, 7 or 30 days (Hevy-style distribution). Hover shows sets, volume and
 * when the region was last trained; click opens the drill-down.
 *
 * Body artwork: react-muscle-highlighter 1.2.0 (MIT licence,
 * https://github.com/soroojshehryar/react-muscle-highlighter). See README credits.
 */
import type { MuscleState, MuscleStatus } from "@ascend/shared";
import { useMemo, useState } from "react";
import type { ExtendedBodyPart, Slug } from "react-muscle-highlighter";

import { api } from "../api/client";
import { readyAtLabel } from "../lib/format";
import {
  STATUS_COLORS,
  STATUS_LABELS,
  agoLabel,
  heatColor,
  primaryRegion,
  regionsForSlug,
  summarizeSlugs,
  type SlugSummary,
} from "../lib/muscleMap";
import { usePrefsTheme } from "../lib/prefs";
import { cssVar } from "../lib/theme";
import { useApi } from "../lib/useApi";
import { MuscleDrilldown } from "./MuscleDrilldown";
import { MuscleFigure } from "./MuscleFigure";
import { Segmented } from "./Segmented";

const LEGEND: MuscleStatus[] = ["under", "optimal", "recovering", "over", "no_data"];

type View = "recovery" | "volume";
type Range = "1" | "7" | "30";
const RANGE_WORDS: Record<Range, string> = { "1": "today", "7": "last 7 days", "30": "last 30 days" };

/** "No data" follows the theme (a dark blob on a light page reads as a warning). */
function statusColor(status: MuscleStatus): string {
  return status === "no_data" ? cssVar("--color-nodata", STATUS_COLORS.no_data) : STATUS_COLORS[status];
}

export function MuscleMap({ muscles, refreshKey = 0 }: { muscles: MuscleState[]; refreshKey?: number }) {
  const theme = usePrefsTheme();
  const [view, setView] = useState<View>("recovery");
  const [range, setRange] = useState<Range>("7");
  const [side, setSide] = useState<"front" | "back">("front");
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<string | null>(null);
  // Recovery status is a 7-day measure, so its hover card uses 7 days too.
  const days = view === "volume" ? Number(range) : 7;
  const activity = useApi(() => api.muscleActivity(days), [days, refreshKey]);

  const slugs = useMemo(() => summarizeSlugs(muscles, activity.data ?? []), [muscles, activity.data]);
  const maxSets = Math.max(0, ...[...slugs.values()].map((s) => s.sets));

  const { parts, glow, pulse } = useMemo(() => {
    const parts: ExtendedBodyPart[] = [];
    const glow: string[] = [];
    const pulse: string[] = [];
    for (const s of slugs.values()) {
      if (view === "recovery") {
        parts.push({ slug: s.slug as Slug, color: statusColor(s.status) });
        if (s.fatigued) glow.push(s.slug);
        if (s.readyAgain) pulse.push(s.slug);
      } else {
        const share = maxSets > 0 ? s.sets / maxSets : 0;
        parts.push({ slug: s.slug as Slug, color: heatColor(share, theme) ?? cssVar("--color-map-fill", "#1a2232") });
        if (share >= 0.75) glow.push(s.slug);
      }
    }
    return { parts, glow, pulse };
    // theme: the colours are read from CSS tokens, so recompute when it changes.
  }, [slugs, view, maxSets, theme]);

  const interactive = useMemo(() => new Set(slugs.keys()), [slugs]);
  const hoveredSummary = hovered ? slugs.get(hovered) : undefined;

  function openSlug(slug: string) {
    setSelected(slug);
    const summary = slugs.get(slug);
    if (summary) setDetail(primaryRegion(summary).key);
  }

  const regions = selected ? regionsForSlug(muscles, selected) : [];
  const attention = muscles
    .filter((m) => m.status === "over" || m.status === "recovering" || m.status === "under")
    .sort((a, b) => ({ over: 0, recovering: 1, under: 2 })[a.status as "over"] - ({ over: 0, recovering: 1, under: 2 })[b.status as "over"])
    .slice(0, 5);
  const ready = [...slugs.values()].filter((s) => s.readyAgain).map((s) => s.label);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Segmented
          label="Map colours"
          value={view}
          onChange={setView}
          options={[{ value: "recovery", label: "Recovery" }, { value: "volume", label: "Volume" }]}
        />
        {view === "volume" && (
          <Segmented
            label="Volume range"
            value={range}
            onChange={setRange}
            options={[{ value: "1", label: "1 day" }, { value: "7", label: "7 days" }, { value: "30", label: "30 days" }]}
          />
        )}
      </div>
      <div className="flex gap-6">
        <div className="flex shrink-0 flex-col items-center gap-2">
          <MuscleFigure
            parts={parts}
            side={side}
            glow={glow}
            pulse={view === "recovery" ? pulse : []}
            interactive={interactive}
            hovered={hovered}
            onHover={setHovered}
            onSelect={openSlug}
            border={cssVar("--color-line-2", "#2a3446")}
            defaultFill={cssVar("--color-map-fill", "#1a2232")}
            tooltip={hoveredSummary && <MuscleTooltip s={hoveredSummary} view={view} rangeWords={RANGE_WORDS[view === "volume" ? range : "7"]} />}
          />
          <button
            type="button"
            className="btn-ghost px-3 py-1.5 text-xs"
            onClick={() => setSide((s) => (s === "front" ? "back" : "front"))}
            aria-label={side === "front" ? "Show the back of the body" : "Show the front of the body"}
          >
            <FlipIcon /> {side === "front" ? "Front · flip to back" : "Back · flip to front"}
          </button>
        </div>
        <div className="min-w-0 flex-1 space-y-4">
          {view === "recovery" ? (
            <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs" aria-label="Map legend">
              {LEGEND.map((s) => (
                <li key={s} className="flex items-center gap-2 text-muted">
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ background: statusColor(s) }} />
                  {STATUS_LABELS[s]}
                </li>
              ))}
              {ready.length > 0 && (
                <li className="flex items-center gap-2 text-muted">
                  <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-good motion-reduce:animate-none" /> Ready to train
                </li>
              )}
            </ul>
          ) : (
            <div className="flex items-center gap-3 text-xs text-muted" aria-label="Map legend">
              <span>Fewer sets</span>
              <span className="flex h-2.5 w-32 overflow-hidden rounded-sm" aria-hidden="true">
                {[0.1, 0.3, 0.5, 0.7, 0.95].map((v) => <span key={v} className="flex-1" style={{ background: heatColor(v, theme) ?? undefined }} />)}
              </span>
              <span>More sets · {RANGE_WORDS[range]}</span>
            </div>
          )}
          {regions.length > 0 ? (
            <div className="panel-in rounded-lg border border-line bg-panel-2 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-accent">{slugs.get(selected ?? "")?.label ?? selected}</span>
                <button type="button" className="text-xs text-faint hover:text-ink" onClick={() => setSelected(null)}>close</button>
              </div>
              {regions.map((r) => <RegionRow key={r.key} m={r} onOpen={setDetail} />)}
            </div>
          ) : (
            <div>
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted">Needs attention</div>
              {attention.length === 0 ? (
                <p className="text-xs text-faint">Log a workout to see per-muscle load. Click a muscle for details.</p>
              ) : (
                attention.map((m) => <RegionRow key={m.key} m={m} onOpen={setDetail} />)
              )}
            </div>
          )}
          {ready.length > 0 && view === "recovery" && (
            <p className="text-xs text-muted">
              <span className="font-medium text-good">Ready again:</span> {ready.join(", ")}
            </p>
          )}
          <details className="group">
            <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wider text-muted hover:text-ink">
              All muscles ({muscles.length})
            </summary>
            <div className="mt-2 max-h-64 overflow-y-auto pr-1">
              {muscles.map((m) => <RegionRow key={m.key} m={m} onOpen={setDetail} />)}
            </div>
          </details>
        </div>
      </div>
      {detail && <MuscleDrilldown key={detail} code={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}

function MuscleTooltip({ s, view, rangeWords }: { s: SlugSummary; view: View; rangeWords: string }) {
  return (
    <div data-testid="muscle-tooltip">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="font-semibold text-ink">{s.label}</span>
        <span className="flex items-center gap-1.5 text-muted">
          <span className="h-2 w-2 rounded-full" style={{ background: STATUS_COLORS[s.status] }} />
          {s.readyAgain ? "Ready to train" : STATUS_LABELS[s.status]}
        </span>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
        <dt className="text-faint">Sets</dt>
        <dd className="text-right text-ink">{s.sets} <span className="text-faint">· {rangeWords}</span></dd>
        <dt className="text-faint">Volume</dt>
        <dd className="text-right text-ink">{s.volumeKg > 0 ? `${s.volumeKg.toLocaleString()} kg` : "–"}</dd>
        <dt className="text-faint">Last trained</dt>
        <dd className="text-right text-ink">{agoLabel(s.lastTrained)}</dd>
      </dl>
      {view === "recovery" && s.regions.length > 1 && (
        <div className="mt-1.5 border-t border-line pt-1.5 text-faint">{s.regions.map((r) => r.label).join(" · ")}</div>
      )}
      <div className="mt-1.5 text-[10px] text-faint">Click for details</div>
    </div>
  );
}

function FlipIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 12a8 8 0 0 1 13.7-5.7L20 8.6" />
      <path d="M20 4v4.6h-4.6M20 12a8 8 0 0 1-13.7 5.7L4 15.4" />
      <path d="M4 20v-4.6h4.6" />
    </svg>
  );
}

function RegionRow({ m, onOpen }: { m: MuscleState; onOpen: (code: string) => void }) {
  const band = `${m.weekly_low}–${m.weekly_high}`;
  return (
    <button
      type="button"
      onClick={() => onOpen(m.key)}
      className="flex w-full items-center justify-between gap-2 border-b border-line/60 py-1.5 text-left text-xs transition-transform last:border-0 hover:translate-x-0.5 hover:bg-panel/60"
    >
      <span className="flex min-w-0 items-center gap-2">
        <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: STATUS_COLORS[m.status] }} />
        <span className="truncate text-ink">{m.label}</span>
      </span>
      <span className="shrink-0 text-right text-muted" title="Effective sets in the last 7 days vs the weekly target band (estimate)">
        {m.es_7d} / {band} sets · {Math.round(m.readiness * 100)}%{m.status === "recovering" ? ` · ${readyAtLabel(m.ready_at)}` : ""}
      </span>
      <span className="sr-only">, {STATUS_LABELS[m.status]}. Open details</span>
    </button>
  );
}
