/**
 * The muscle figure: one body (front or back) drawn from ASCEND's own anatomical artwork
 * (lib/bodyMapPaths.ts, 54 muscles and heads, original drawing; see docs/research/v8-anatomy.md).
 *  - flips front/back as a card rotate (rotateY 180deg, backface hidden) and tilts a few
 *    degrees towards the cursor (CSS variables written from requestAnimationFrame, so
 *    moving the mouse never re-renders React); both are skipped with Reduce motion;
 *  - a "deep" layer ghosts the surface muscles and draws the deep ones (pectoralis minor,
 *    rotator cuff, rhomboids, transversus, iliopsoas...) where they really sit;
 *  - colours change with a CSS fill transition; fatigued or heavy muscles get a soft glow
 *    and recovered ones breathe; the hovered muscle lifts and shows a tooltip.
 * Plain SVG, no lighting filters, so it stays light on a laptop GPU. The figure is
 * aria-hidden: the lists beside it carry the same information for keyboard and screen readers.
 */
import { useCallback, useEffect, useId, useMemo, useRef, type PointerEvent, type ReactNode } from "react";

import { BODY_OUTLINE, BODY_VIEWBOX, MUSCLE_PATHS, type MusclePath } from "../lib/bodyMapPaths";
import { useReducedMotion } from "../lib/motion";
import { READY_TOKEN } from "../lib/muscleMap";

export const MAX_TILT_DEG = 5;

export interface BodyPart {
  slug: string;
  color?: string;
}

export type BodyLayer = "surface" | "deep";

export interface MuscleFigureProps {
  parts: BodyPart[];
  side: "front" | "back";
  layer?: BodyLayer;
  /** Regions drawn with a soft glow (fatigued, or the heaviest in the volume view). */
  glow: string[];
  /** Regions that breathe gently (recovered and ready to train). */
  pulse: string[];
  /** Regions with data: these react to hover and click. */
  interactive: ReadonlySet<string>;
  hovered: string | null;
  onHover: (slug: string | null) => void;
  onSelect: (slug: string) => void;
  border: string;
  defaultFill: string;
  scale?: number;
  /** Shown beside the pointer while a region is hovered. */
  tooltip?: ReactNode;
}

const [, , VB_W, VB_H] = BODY_VIEWBOX.split(" ").map(Number);
const sel = (scope: string, slugs: string[]) => slugs.map((s) => `${scope} path[data-key="${s}"]`).join(",\n");

/** One view of the body as plain SVG (also used small, for exercise tiles). */
export function BodySvg({
  view,
  layer = "surface",
  fills,
  defaultFill,
  border,
  outlineFill,
  className,
  style,
}: {
  view: "front" | "back";
  layer?: BodyLayer;
  fills: ReadonlyMap<string, string>;
  defaultFill: string;
  border: string;
  outlineFill?: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  const surface = MUSCLE_PATHS.filter((p) => p.view === view && p.layer === "surface");
  const deep = layer === "deep" ? MUSCLE_PATHS.filter((p) => p.view === view && p.layer === "deep") : [];
  const draw = (p: MusclePath, i: number, ghost: boolean) => (
    <path
      key={`${p.key}-${p.side ?? "c"}-${i}`}
      d={p.d}
      data-key={ghost ? undefined : p.key}
      fill={ghost ? defaultFill : (fills.get(p.key) ?? defaultFill)}
      stroke={border}
      strokeWidth={0.6}
      opacity={ghost ? 0.35 : 1}
    />
  );
  return (
    <svg viewBox={BODY_VIEWBOX} className={className} style={style} aria-hidden="true" focusable="false">
      <path d={BODY_OUTLINE[view]} fill={outlineFill ?? defaultFill} stroke={border} strokeWidth={0.8} opacity={0.9} />
      <g>{surface.map((p, i) => draw(p, i, layer === "deep"))}</g>
      {deep.length > 0 && <g>{deep.map((p, i) => draw(p, i, false))}</g>}
    </svg>
  );
}

export function MuscleFigure(props: MuscleFigureProps) {
  const { parts, side, layer = "surface", glow, pulse, interactive, hovered, onHover, onSelect, border, defaultFill, scale = 1.2, tooltip } = props;
  const reduce = useReducedMotion();
  const scope = `mf-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const stage = useRef<HTMLDivElement>(null);
  const tilt = useRef<HTMLDivElement>(null);
  const tip = useRef<HTMLDivElement>(null);
  const frame = useRef<number | null>(null);
  const pointer = useRef({ x: 0, y: 0, tx: 0, ty: 0 });
  const hoveredRef = useRef(hovered);
  hoveredRef.current = hovered;
  const width = 200 * scale;
  const height = (200 * scale * VB_H) / VB_W;

  const fills = useMemo(() => new Map(parts.filter((p) => p.color).map((p) => [p.slug, p.color as string])), [parts]);

  const schedule = useCallback(() => {
    if (frame.current !== null) return;
    frame.current = requestAnimationFrame(() => {
      frame.current = null;
      const { x, y, tx, ty } = pointer.current;
      if (tilt.current && !reduce) {
        tilt.current.style.setProperty("--tx", tx.toFixed(3));
        tilt.current.style.setProperty("--ty", ty.toFixed(3));
      }
      if (tip.current) tip.current.style.transform = `translate3d(${x + 14}px, ${y + 14}px, 0)`;
    });
  }, [reduce]);

  useEffect(() => () => { if (frame.current !== null) cancelAnimationFrame(frame.current); }, []);

  function keyAt(e: PointerEvent<HTMLDivElement>): string | null {
    const key = (e.target as Element).getAttribute?.("data-key");
    return key && interactive.has(key) ? key : null;
  }

  function onMove(e: PointerEvent<HTMLDivElement>) {
    const box = stage.current?.getBoundingClientRect();
    if (box && box.width > 0) {
      const x = e.clientX - box.left;
      const y = e.clientY - box.top;
      pointer.current = { x, y, tx: (x / box.width) * 2 - 1, ty: (y / box.height) * 2 - 1 };
      schedule();
    }
    const next = keyAt(e);
    if (next !== hoveredRef.current) onHover(next);
  }

  function onLeave() {
    pointer.current = { ...pointer.current, tx: 0, ty: 0 };
    schedule();
    onHover(null);
  }

  function onClick(e: React.MouseEvent<HTMLDivElement>) {
    const key = (e.target as Element).getAttribute?.("data-key");
    if (key && interactive.has(key)) onSelect(key);
  }

  const css = useMemo(() => {
    const s = `.${scope}`;
    const rules = [`${s} svg path { transition: fill 650ms ease, transform 180ms ease; transform-box: fill-box; transform-origin: center; }`];
    if (glow.length) rules.push(`${sel(s, glow)} { filter: drop-shadow(0 0 3px currentColor); color: var(--color-ink); }`);
    if (pulse.length) rules.push(`${sel(s, pulse)} { animation: asc-muscle-pulse 2.8s ease-in-out infinite; stroke: var(${READY_TOKEN}); stroke-width: 1.4px; vector-effect: non-scaling-stroke; }`);
    const live = [...interactive];
    if (live.length) rules.push(`${sel(s, live)} { cursor: pointer; }`);
    if (hovered) {
      rules.push(`${s} svg path[data-key="${hovered}"] { transform: scale(1.04); stroke: var(--color-ink); stroke-width: 1.4px; vector-effect: non-scaling-stroke; animation: none; }`);
    }
    return rules.join("\n");
  }, [scope, glow, pulse, interactive, hovered]);

  const face = (view: "front" | "back") => (
    <BodySvg view={view} layer={layer} fills={fills} defaultFill={defaultFill} border={border} style={{ width, height }} />
  );

  return (
    <div
      ref={stage}
      className={`${scope} relative select-none`}
      style={{ width, perspective: "900px" }}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
      onClick={onClick}
      aria-hidden="true"
      data-testid="muscle-figure"
      data-side={side}
      data-layer={layer}
    >
      <style>{css}</style>
      <div
        ref={tilt}
        className="relative will-change-transform"
        style={{
          transformStyle: "preserve-3d",
          transform: reduce ? "none" : `rotateY(calc(var(--tx, 0) * ${MAX_TILT_DEG}deg)) rotateX(calc(var(--ty, 0) * ${-MAX_TILT_DEG}deg))`,
          transition: "transform 160ms ease-out",
        }}
      >
        <div
          className="relative"
          data-testid="muscle-flip"
          style={{
            width,
            height,
            transformStyle: "preserve-3d",
            transform: side === "back" ? "rotateY(180deg)" : "none",
            transition: reduce ? "none" : "transform 700ms cubic-bezier(0.25, 0.8, 0.25, 1)",
          }}
        >
          <div className="absolute inset-0" style={{ backfaceVisibility: "hidden", pointerEvents: side === "front" ? "auto" : "none" }}>
            {face("front")}
          </div>
          <div className="absolute inset-0" style={{ backfaceVisibility: "hidden", transform: "rotateY(180deg)", pointerEvents: side === "back" ? "auto" : "none" }}>
            {face("back")}
          </div>
        </div>
      </div>
      <div
        className="pointer-events-none mx-auto -mt-2 h-4 w-2/3 rounded-[50%]"
        style={{ background: "radial-gradient(closest-side, rgba(0,0,0,0.35), transparent)", transform: "translateX(calc(var(--tx, 0) * -10px))" }}
      />
      {hovered && tooltip && (
        <div ref={tip} className="pointer-events-none absolute left-0 top-0 z-10 w-52" style={{ transform: `translate3d(${pointer.current.x + 14}px, ${pointer.current.y + 14}px, 0)` }}>
          <div className="pop-in origin-top-left rounded-lg border border-line-2 bg-panel p-3 text-xs shadow-xl">{tooltip}</div>
        </div>
      )}
    </div>
  );
}
