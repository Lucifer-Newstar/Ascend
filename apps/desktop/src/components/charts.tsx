/**
 * Minimal SVG charts that follow the theme tokens: a line chart (one or two
 * series, optional dots) and a bar chart. Both carry an accessible summary.
 */
import { compact, extent, linePath, linearScale, niceTicks, showLabel } from "../lib/chart";

const W = 560;
const PAD = { top: 12, right: 20, bottom: 24, left: 52 };

/**
 * "Show the numbers" disclosure under a chart: the same data as a real table, for
 * screen readers and for anyone who wants exact values instead of a line.
 */
export function ChartData({ labels, columns, unit = "" }: {
  labels: string[];
  columns: { label: string; values: (number | null)[] }[];
  unit?: string;
}) {
  return (
    <details className="mt-1 text-xs text-muted">
      <summary className="cursor-pointer select-none hover:text-ink">Show the numbers</summary>
      <div className="mt-2 max-h-48 overflow-y-auto">
        <table className="w-full text-left">
          <thead className="text-faint">
            <tr>
              <th scope="col" className="py-1 font-medium">Date</th>
              {columns.map((c) => <th key={c.label} scope="col" className="py-1 text-right font-medium">{c.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {labels.map((l, i) => (
              <tr key={`${l}-${i}`} className="border-t border-line">
                <th scope="row" className="py-1 font-normal">{l}</th>
                {columns.map((c) => (
                  <td key={c.label} className="py-1 text-right text-ink">
                    {c.values[i] === null || c.values[i] === undefined ? "–" : `${c.values[i]}${unit}`}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export interface Series {
  label: string;
  values: (number | null)[];
  className: string; // stroke colour utility, e.g. "stroke-accent"
  dots?: boolean;
  dashed?: boolean;
}

export function LineChart({ labels, series, height = 200, unit = "", summary, table = true }: {
  labels: string[];
  series: Series[];
  height?: number;
  unit?: string;
  summary: string;
  table?: boolean;
}) {
  const ext = extent(series.flatMap((s) => s.values));
  if (!ext || labels.length === 0) return null;
  const ticks = niceTicks(ext[0], ext[1], 4);
  const lo = Math.min(ext[0], ticks[0]);
  const hi = Math.max(ext[1], ticks[ticks.length - 1]);
  const x = linearScale([0, Math.max(1, labels.length - 1)], [PAD.left, W - PAD.right]);
  const y = linearScale([lo, hi], [height - PAD.bottom, PAD.top]);
  const every = Math.max(1, Math.ceil(labels.length / 6));

  return (
    <figure className="w-full">
      <svg viewBox={`0 0 ${W} ${height}`} className="w-full" role="img" aria-label={summary}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="stroke-line" strokeWidth={1} />
            <text x={PAD.left - 6} y={y(t) + 3} textAnchor="end" className="fill-faint text-[10px]">{compact(t)}{unit}</text>
          </g>
        ))}
        {labels.map((l, i) => showLabel(i, labels.length, every) && (
          <text key={`${l}-${i}`} x={x(i)} y={height - 6} textAnchor={i === 0 ? "start" : i === labels.length - 1 ? "end" : "middle"} className="fill-faint text-[10px]">{l}</text>
        ))}
        {series.map((s) => (
          <g key={s.label}>
            <path
              d={linePath(s.values.map((v, i) => (v === null ? null : { x: x(i), y: y(v) })))}
              fill="none"
              strokeWidth={2}
              strokeDasharray={s.dashed ? "4 4" : undefined}
              strokeLinecap="round"
              strokeLinejoin="round"
              className={s.className}
            />
            {s.dots && s.values.map((v, i) => v !== null && (
              <circle key={i} cx={x(i)} cy={y(v)} r={2.5} className={`${s.className} fill-panel`} strokeWidth={1.5} />
            ))}
          </g>
        ))}
      </svg>
      <figcaption className="mt-1 flex gap-4 text-[11px] text-muted">
        {series.map((s) => (
          <span key={s.label} className="flex items-center gap-1.5">
            <svg width="16" height="4" aria-hidden="true"><line x1="0" x2="16" y1="2" y2="2" strokeWidth={2} strokeDasharray={s.dashed ? "3 3" : undefined} className={s.className} /></svg>
            {s.label}
          </span>
        ))}
      </figcaption>
      {table && <ChartData labels={labels} unit={unit} columns={series.map((s) => ({ label: s.label, values: s.values }))} />}
    </figure>
  );
}

export function BarChart({ labels, values, height = 160, width = W, unit = "", summary, className = "fill-accent", table = true, valueLabel = "Value" }: {
  labels: string[];
  values: number[];
  height?: number;
  width?: number; // viewBox width: match the rendered width so text keeps its size
  unit?: string;
  summary: string;
  className?: string;
  table?: boolean;
  valueLabel?: string;
}) {
  if (!values.length) return null;
  const every = Math.max(1, Math.ceil(values.length / Math.floor(width / 70)));
  const max = Math.max(...values, 0);
  const ticks = niceTicks(0, max || 1, 3);
  const top = ticks[ticks.length - 1] || 1;
  const y = linearScale([0, top], [height - PAD.bottom, PAD.top]);
  const band = (width - PAD.left - PAD.right) / values.length;
  const bw = Math.min(36, band * 0.6);

  return (
    <div className="w-full">
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label={summary}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} className="stroke-line" strokeWidth={1} />
          <text x={PAD.left - 6} y={y(t) + 3} textAnchor="end" className="fill-faint text-[10px]">{compact(t)}{unit}</text>
        </g>
      ))}
      {values.map((v, i) => {
        const cx = PAD.left + band * i + band / 2;
        return (
          <g key={`${labels[i]}-${i}`}>
            <rect x={cx - bw / 2} y={y(v)} width={bw} height={Math.max(0, y(0) - y(v))} rx={3} className={className}>
              <title>{`${labels[i]}: ${v}${unit}`}</title>
            </rect>
            {showLabel(i, values.length, every) && (
              <text x={cx} y={height - 6} textAnchor="middle" className="fill-faint text-[10px]">{labels[i]}</text>
            )}
          </g>
        );
      })}
    </svg>
    {table && <ChartData labels={labels} unit={unit} columns={[{ label: valueLabel, values }]} />}
    </div>
  );
}
