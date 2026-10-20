/** Shared loading / error / empty states so every screen handles them the same way. */
export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 p-6 text-sm text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card m-6 border-bad/40 p-5">
      <div className="text-sm font-semibold text-bad">Something went wrong</div>
      <p className="mt-1 text-sm text-muted">{message}</p>
      {onRetry && <button type="button" className="btn-ghost mt-3" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Empty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-line-2 p-6 text-center">
      <div className="text-sm text-muted">{title}</div>
      {hint && <div className="mt-1 text-xs text-faint">{hint}</div>}
    </div>
  );
}
