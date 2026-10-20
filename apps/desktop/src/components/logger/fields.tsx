/** Small form controls shared by every logger form. */
import { IconTimer } from "../Icons";

export function NumberField({ label, value, step, onChange, min = 0 }: {
  label: string;
  value: number;
  step: number;
  onChange: (n: number) => void;
  min?: number;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs text-muted">{label}</span>
      <div className="flex">
        <button type="button" className="rounded-l-md border border-r-0 border-line-input bg-panel-2 px-2.5 text-muted transition-colors duration-150 hover:text-ink active:bg-panel-3" onClick={() => onChange(Math.max(min, +(value - step).toFixed(1)))} aria-label={`decrease ${label}`}>−</button>
        <input className="input no-spin min-w-0 rounded-none px-1 text-center" type="number" aria-label={label} value={value} step={step} min={min} onChange={(e) => onChange(Number(e.target.value))} />
        <button type="button" className="rounded-r-md border border-l-0 border-line-input bg-panel-2 px-2.5 text-muted transition-colors duration-150 hover:text-ink active:bg-panel-3" onClick={() => onChange(+(value + step).toFixed(1))} aria-label={`increase ${label}`}>+</button>
      </div>
    </label>
  );
}

export const RPE_OPTIONS = [5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10];

export function RpeSelect({ value, onChange, label = "RPE (effort)" }: { value: number | null; onChange: (v: number | null) => void; label?: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs text-muted">{label}</span>
      <select className="input" value={value ?? ""} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
        <option value="">not logged</option>
        {RPE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
      </select>
    </label>
  );
}

export function RestTimer({ seconds, onSkip }: { seconds: number; onSkip: () => void }) {
  if (seconds <= 0) return <div className="flex items-center gap-1.5 text-xs text-faint"><IconTimer width={14} height={14} /> rest timer starts after a set</div>;
  const mm = Math.floor(seconds / 60);
  const ss = String(seconds % 60).padStart(2, "0");
  return (
    <div className="flex items-center gap-2 rounded-md border border-accent/30 bg-accent/[0.06] px-3 py-1.5" role="timer" aria-label="Rest timer">
      <IconTimer width={16} height={16} className="text-accent" />
      <span className="font-display text-lg font-bold text-accent">{mm}:{ss}</span>
      <button type="button" className="text-xs text-muted hover:text-ink" onClick={onSkip}>skip</button>
    </div>
  );
}
