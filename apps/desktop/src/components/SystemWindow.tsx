/**
 * The System window: ASCEND's one "Solo Leveling" surface.
 *
 * Reserved for System events only (daily quest, level up / rank up, quest complete,
 * skill acquired, deload and other warnings). Everything else is a normal card, so the
 * window stays special.
 *
 * Look: translucent navy glass, a 1 px border in the window's accent at 45%, a soft
 * inner glow, 8 px corner brackets and a bracketed, uppercase header. The light theme
 * keeps the shape and drops the glow and blur (index.css).
 *
 * Motion: a 220 ms entrance (scale 0.98 → 1 and fade) and one 600 ms scan line, both
 * transform/opacity only. With Reduce motion (OS or Settings) it is a 120 ms fade and
 * the scan line is not rendered.
 *
 * Modal windows trap focus, close on Esc and give focus back to where it was.
 */
import { useEffect, useId, useRef, type CSSProperties, type ReactNode, type RefObject } from "react";

import { useReducedMotion } from "../lib/motion";

export type SystemVariant = "notice" | "quest" | "warning" | "levelup" | "skill";

/** Window accent per variant. Notices, quests and skills follow the rank tint. */
const VARIANT_TOKEN: Record<SystemVariant, string | null> = {
  notice: null,
  quest: null,
  skill: null,
  levelup: "--color-xp",
  warning: "--color-warn",
};

/**
 * Colour as progression (System UI only, never data): E-C System blue, B-A arcane
 * violet, S crimson. Charts and status colours never change with rank.
 */
export function rankTint(rank: string | null | undefined): string {
  if (rank === "S") return "--color-rank-s";
  if (rank === "A" || rank === "B") return "--color-xp";
  return "--color-accent";
}

export function windowAccent(variant: SystemVariant, rank?: string | null): string {
  return VARIANT_TOKEN[variant] ?? rankTint(rank);
}

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export interface SystemWindowProps {
  variant?: SystemVariant;
  /** Shown as "[ TITLE ]" in the window header. */
  title: string;
  children?: ReactNode;
  /** Buttons along the bottom edge. */
  actions?: ReactNode;
  /** Extra content on the right of the header (a timer, a count). */
  headerExtra?: ReactNode;
  /** Current rank: tints notice, quest and skill windows. */
  rank?: string | null;
  /** Render as a centred modal dialog with a backdrop, focus trap and Esc to close. */
  modal?: boolean;
  onClose?: () => void;
  /** Element to focus when a modal opens (default: the first focusable element). */
  initialFocus?: RefObject<HTMLElement | null>;
  /** id of the element naming the window (default: its header). */
  labelledBy?: string;
  describedBy?: string;
  className?: string;
  testId?: string;
}

export function SystemWindow({
  variant = "notice",
  title,
  children,
  actions,
  headerExtra,
  rank,
  modal = false,
  onClose,
  initialFocus,
  labelledBy,
  describedBy,
  className = "",
  testId,
}: SystemWindowProps) {
  const reduce = useReducedMotion();
  const headerId = useId();
  const ref = useRef<HTMLElement>(null);

  // Modal: focus moves in, Tab cycles inside, Esc closes, focus returns on close.
  useEffect(() => {
    if (!modal) return;
    const previous = document.activeElement as HTMLElement | null;
    const box = ref.current;
    const first = initialFocus?.current ?? box?.querySelector<HTMLElement>(FOCUSABLE) ?? box;
    first?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && onClose) {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !box) return;
      const items = [...box.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (items.length === 0) {
        e.preventDefault();
        return;
      }
      const head = items[0];
      const tail = items[items.length - 1];
      const active = document.activeElement;
      if (e.shiftKey && (active === head || !box.contains(active))) {
        e.preventDefault();
        tail.focus();
      } else if (!e.shiftKey && (active === tail || !box.contains(active))) {
        e.preventDefault();
        head.focus();
      }
    };
    document.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("keydown", onKey, true);
      if (previous && typeof previous.focus === "function" && document.contains(previous)) previous.focus();
    };
    // initialFocus and onClose are read when the window opens; re-running would steal focus.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modal]);

  const accent = windowAccent(variant, rank);
  const style = { "--sw": `var(${accent})` } as CSSProperties;

  const body = (
    <section
      ref={ref}
      role={modal ? "dialog" : "region"}
      aria-modal={modal ? true : undefined}
      aria-labelledby={labelledBy ?? headerId}
      aria-describedby={describedBy}
      tabIndex={modal ? -1 : undefined}
      className={`sys-window ${modal ? "m-auto w-full max-w-md" : ""} ${className}`}
      style={style}
      data-variant={variant}
      data-motion={reduce ? "reduced" : "full"}
      data-testid={testId}
    >
      <span aria-hidden="true" className="sys-corner sys-tl" />
      <span aria-hidden="true" className="sys-corner sys-tr" />
      <span aria-hidden="true" className="sys-corner sys-bl" />
      <span aria-hidden="true" className="sys-corner sys-br" />
      {!reduce && <span aria-hidden="true" className="sys-scan motion-decor" />}
      <header className="sys-header">
        <h2 id={headerId} className="sys-title">
          <span aria-hidden="true">[ </span>
          {title}
          <span aria-hidden="true"> ]</span>
        </h2>
        {headerExtra}
      </header>
      {children !== undefined && <div className="sys-body">{children}</div>}
      {actions && <div className="sys-actions">{actions}</div>}
    </section>
  );

  if (!modal) return body;
  return (
    <div className="sys-backdrop fixed inset-0 z-50 flex overflow-y-auto p-4" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose?.(); }}>
      {body}
    </div>
  );
}
