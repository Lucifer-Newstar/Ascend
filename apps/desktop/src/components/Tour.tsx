/**
 * Spotlight tour: dims the window, outlines one element (data-tour="…") and shows a card
 * with Back / Next / Skip. Keyboard: Enter or Right = next, Left = back, Esc = stop.
 * Steps whose element is missing are skipped. No animation with Reduce motion.
 */
import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";

import type { Tour } from "../lib/tours";
import { useReducedMotion } from "../lib/motion";

interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

function findTarget(target: string | null): HTMLElement | null {
  if (!target) return null;
  return document.querySelector<HTMLElement>(`[data-tour="${target}"]`);
}

export function TourOverlay({ tour, onDone }: { tour: Tour; onDone: (finished: boolean) => void }) {
  const steps = tour.steps;
  const [i, setI] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);
  const card = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();

  const exists = useCallback((n: number) => steps[n].target === null || findTarget(steps[n].target) !== null, [steps]);

  const go = useCallback(
    (dir: 1 | -1) => {
      let n = i + dir;
      while (n >= 0 && n < steps.length && !exists(n)) n += dir;
      if (n >= steps.length) onDone(true);
      else if (n >= 0) setI(n);
    },
    [i, steps.length, exists, onDone],
  );

  useEffect(() => {
    // Measure after paint (and skip a step whose element vanished).
    const raf = window.requestAnimationFrame(() => {
      if (!exists(i)) {
        go(1);
        return;
      }
      const el = findTarget(steps[i].target);
      if (!el) {
        setRect(null);
        return;
      }
      el.scrollIntoView?.({ block: "nearest" });
      const r = el.getBoundingClientRect();
      setRect({ top: r.top - 6, left: r.left - 6, width: r.width + 12, height: r.height + 12 });
    });
    return () => window.cancelAnimationFrame(raf);
  }, [i, steps, exists, go]);

  useEffect(() => {
    card.current?.focus();
  }, [i]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onDone(false);
      } else if (e.key === "ArrowRight" || e.key === "Enter") {
        e.preventDefault();
        go(1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        go(-1);
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [go, onDone]);

  const step = steps[i];
  const last = i === steps.length - 1;
  const vw = typeof window !== "undefined" ? window.innerWidth : 1280;
  const vh = typeof window !== "undefined" ? window.innerHeight : 800;
  const cardStyle: CSSProperties = rect
    ? {
        top: Math.min(rect.top + rect.height + 12, vh - 220),
        left: Math.max(16, Math.min(rect.left, vw - 360)),
      }
    : { top: "50%", left: "50%", transform: "translate(-50%, -50%)" };
  if (rect && rect.top + rect.height + 232 > vh && rect.top > 240) cardStyle.top = rect.top - 200;

  return (
    <div className="fixed inset-0 z-50" data-testid="tour">
      {rect ? (
        <div
          aria-hidden="true"
          className={`pointer-events-none fixed rounded-lg ring-2 ring-accent ${reduce ? "" : "transition-all duration-200"}`}
          style={{ ...rect, boxShadow: "0 0 0 9999px rgba(3, 7, 18, 0.7)" }}
        />
      ) : (
        <div aria-hidden="true" className="fixed inset-0 bg-[rgba(3,7,18,0.7)]" />
      )}
      <div
        ref={card}
        role="dialog"
        aria-modal="true"
        aria-labelledby="tour-title"
        aria-describedby="tour-body"
        tabIndex={-1}
        className="fixed w-[340px] rounded-xl border border-accent/50 bg-panel p-4 shadow-2xl outline-none"
        style={cardStyle}
      >
        <p className="text-[10px] uppercase tracking-wider text-accent">
          Step {i + 1} of {steps.length}
        </p>
        <h2 id="tour-title" className="mt-1 text-base font-semibold text-ink">{step.title}</h2>
        <p id="tour-body" className="mt-1 text-sm text-muted">{step.body}</p>
        <div className="mt-4 flex items-center justify-between gap-2">
          <button type="button" className="text-xs text-muted hover:text-ink" onClick={() => onDone(false)}>
            Skip tour
          </button>
          <div className="flex gap-2">
            {i > 0 && (
              <button type="button" className="btn-ghost px-3 py-1 text-xs" onClick={() => go(-1)}>
                Back
              </button>
            )}
            <button type="button" className="btn-primary px-3 py-1 text-xs" onClick={() => go(1)}>
              {last ? "Done" : "Next"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
