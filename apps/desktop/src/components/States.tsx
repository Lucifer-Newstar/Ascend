/** Shared loading / error / empty states so every screen handles them the same way. */
export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 p-6 text-sm text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry, offline = false }: { message: string; onRetry?: () => void; offline?: boolean }) {
  return (
    <div className="card m-6 border-bad/40 p-5" role="alert">
      <div className="text-sm font-semibold text-bad">{offline ? "The local engine isn't responding" : "Something went wrong"}</div>
      <p className="mt-1 text-sm text-muted">
        {offline ? "Your data is safe on this PC. ASCEND restarts the engine on its own; try again in a few seconds." : message}
      </p>
      {offline && <p className="mt-1 text-xs text-faint">Details: {message}</p>}
      {onRetry && <button type="button" className="btn-ghost mt-3" onClick={onRetry}>Retry</button>}
    </div>
  );
}

/** Small inline notice when a refresh failed but older data is still on screen. */
export function StaleNotice({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="status" className="flex items-center justify-between gap-3 rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn">
      <span>Couldn't refresh ({message}). Showing the last data loaded.</span>
      <button type="button" className="font-medium underline-offset-2 hover:underline" onClick={onRetry}>Retry</button>
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
