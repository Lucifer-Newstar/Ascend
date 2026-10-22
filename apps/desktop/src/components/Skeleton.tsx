/**
 * Placeholder blocks shown while a screen loads, shaped like the content that will
 * replace them so the layout does not jump. A light band sweeps across them (the
 * .skeleton shimmer in index.css); it stays still with reduced motion.
 */
import { useEffect, useState } from "react";

export function Skeleton({ className = "" }: { className?: string }) {
  return <span aria-hidden="true" className={`skeleton block rounded-md bg-line/70 ${className}`} />;
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

/**
 * Renders its children only once `ms` have passed. Local requests usually answer in
 * well under that, and a skeleton that appears for a few frames and vanishes reads as
 * a flash; a real wait still gets the skeleton.
 */
export function Delayed({ ms = 250, children }: { ms?: number; children: React.ReactNode }) {
  const [shown, setShown] = useState(ms <= 0);
  useEffect(() => {
    if (ms <= 0) return;
    const t = setTimeout(() => setShown(true), ms);
    return () => clearTimeout(t);
  }, [ms]);
  return shown ? <>{children}</> : null;
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
