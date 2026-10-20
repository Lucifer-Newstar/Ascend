/**
 * Placeholder blocks shown while a screen loads, shaped like the content that will
 * replace them so the layout does not jump. The pulse stops for reduced motion.
 */
export function Skeleton({ className = "" }: { className?: string }) {
  return <span aria-hidden="true" className={`block animate-pulse rounded-md bg-line/70 motion-reduce:animate-none ${className}`} />;
}

export function SkeletonCard({ lines = 3, className = "", title = true }: { lines?: number; className?: string; title?: boolean }) {
  return (
    <div className={`card space-y-3 p-5 ${className}`} aria-hidden="true">
      {title && <Skeleton className="h-3 w-28" />}
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} className={`h-4 ${i === lines - 1 ? "w-2/3" : "w-full"}`} />
      ))}
    </div>
  );
}

/** Wraps skeletons with a screen-reader status so the wait is announced once. */
export function LoadingLayout({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}
