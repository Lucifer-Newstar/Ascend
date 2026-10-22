/**
 * "rough · based on N" (v8 hardening): marks a number computed from too little data to
 * trust yet, with how much data it rests on. Shown next to the number, never instead of it.
 */
export function isRough(n: number, enough: number): boolean {
  return n < enough;
}

export function RoughBadge({ n, unit, enough, className = "" }: { n: number; unit: string; enough: number; className?: string }) {
  if (!isRough(n, enough)) return null;
  const units = n === 1 ? unit.replace(/s$/, "") : unit;
  return (
    <span
      className={`inline-flex items-center rounded border border-warn/50 px-1.5 py-px text-[10px] font-medium uppercase tracking-wide text-warn ${className}`}
      title={`An estimate from only ${n} ${units}; it settles after about ${enough}.`}
      data-testid="rough-badge"
    >
      rough · based on {n} {units}
    </span>
  );
}
