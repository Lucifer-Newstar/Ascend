/**
 * The muscle figure as a small 3D card: one body (front or back) that
 *  - tilts a few degrees towards the cursor (perspective + rotateX/Y on a
 *    compositor layer; CSS variables are written from a requestAnimationFrame,
 *    so moving the mouse never re-renders React),
 *  - flips front/back as a card rotate (rotateY 180deg, backface hidden),
 *  - shades each muscle with an SVG lighting filter (soft "pillow" depth), glows
 *    fatigued or heavily trained muscles, and lets recovered ones breathe,
 *  - lifts the hovered muscle (scale on its own box) and shows a tooltip.
 *
 * Body artwork: react-muscle-highlighter (MIT). Colours change with a CSS fill
 * transition, so switching range or view blends instead of snapping.
 * The figure is aria-hidden: the lists beside it carry the same information for
 * keyboard and screen-reader users.
 */
import { useCallback, useEffect, useId, useMemo, useRef, type PointerEvent, type ReactNode } from "react";
import Body, { type ExtendedBodyPart } from "react-muscle-highlighter";

import { useReducedMotion } from "../lib/motion";

export const MAX_TILT_DEG = 5;

export interface MuscleFigureProps {
  parts: ExtendedBodyPart[];
  side: "front" | "back";
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

const sel = (scope: string, slugs: string[]) => slugs.map((s) => `${scope} path[id="${s}"]`).join(",\n");

export function MuscleFigure(props: MuscleFigureProps) {
  const { parts, side, glow, pulse, interactive, hovered, onHover, onSelect, border, defaultFill, scale = 1.05, tooltip } = props;
  const reduce = useReducedMotion();
  const scope = `mm${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const stage = useRef<HTMLDivElement>(null);
  const tilt = useRef<HTMLDivElement>(null);
  const tip = useRef<HTMLDivElement>(null);
  const frame = useRef(0);
  const pointer = useRef({ x: 0, y: 0, tx: 0, ty: 0 });
  const hoveredRef = useRef(hovered);
  hoveredRef.current = hovered;
  const width = 200 * scale;
  const height = 400 * scale;

  const paint = useCallback(() => {
    frame.current = 0;
    const { x, y, tx, ty } = pointer.current;
    if (tilt.current) {
      tilt.current.style.setProperty("--tx", reduce ? "0" : tx.toFixed(3));
      tilt.current.style.setProperty("--ty", reduce ? "0" : ty.toFixed(3));
    }
    if (tip.current) tip.current.style.transform = `translate3d(${x + 14}px, ${y + 14}px, 0)`;
  }, [reduce]);

  const schedule = useCallback(() => {
    if (frame.current) return;
    if (typeof requestAnimationFrame !== "function") return paint();
    frame.current = requestAnimationFrame(paint);
  }, [paint]);

  useEffect(() => () => {
    if (frame.current) cancelAnimationFrame(frame.current);
  }, []);

  function onMove(e: PointerEvent<HTMLDivElement>) {
    const box = stage.current?.getBoundingClientRect();
    if (box && box.width > 0) {
      const x = e.clientX - box.left;
      const y = e.clientY - box.top;
      // -1..1 from the centre; tilt the top-left corner away when the cursor is there.
      pointer.current = { x, y, tx: (x / box.width) * 2 - 1, ty: (y / box.height) * 2 - 1 };
      schedule();
    }
    const id = (e.target as Element).getAttribute?.("id");
    const next = id && interactive.has(id) ? id : null;
    if (next !== hoveredRef.current) onHover(next);
  }

  function onLeave() {
    pointer.current = { ...pointer.current, tx: 0, ty: 0 };
    schedule();
    onHover(null);
  }

  const css = useMemo(() => {
    const s = `.${scope}`;
    const rules = [
      `${s} svg path { transition: fill 650ms ease, transform 180ms ease; transform-box: fill-box; transform-origin: center; }`,
      `${s} svg path[id] { filter: url(#${scope}-shade); }`,
    ];
    if (glow.length) rules.push(`${sel(s, glow)} { filter: url(#${scope}-glow); }`);
    if (pulse.length) rules.push(`${sel(s, pulse)} { animation: asc-muscle-pulse 2.8s ease-in-out infinite; }`);
    const live = [...interactive];
    if (live.length) rules.push(`${sel(s, live)} { cursor: pointer; }`);
    if (hovered) {
      rules.push(
        `${s} svg path[id="${hovered}"] { transform: scale(1.045); filter: url(#${scope}-glow); stroke: var(--color-ink); stroke-width: 1.4px; vector-effect: non-scaling-stroke; animation: none; }`,
      );
    }
    return rules.join("\n");
  }, [scope, glow, pulse, interactive, hovered]);

  const common = {
    data: parts,
    scale,
    border,
    defaultFill,
    onBodyPartPress: (part: ExtendedBodyPart) => {
      if (part.slug && interactive.has(part.slug)) onSelect(part.slug);
    },
  };

  return (
    <div
      ref={stage}
      className={`${scope} relative select-none`}
      style={{ width, perspective: "900px" }}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
      aria-hidden="true"
      data-testid="muscle-figure"
      data-side={side}
    >
      <style>{css}</style>
      <FigureFilters scope={scope} />
      <div
        ref={tilt}
        className="relative will-change-transform"
        style={{
          transformStyle: "preserve-3d",
          transform: `rotateY(calc(var(--tx, 0) * ${MAX_TILT_DEG}deg)) rotateX(calc(var(--ty, 0) * ${-MAX_TILT_DEG}deg))`,
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
            transition: "transform 700ms cubic-bezier(0.25, 0.8, 0.25, 1)",
          }}
        >
          <div className="absolute inset-0" style={{ backfaceVisibility: "hidden", pointerEvents: side === "front" ? "auto" : "none" }}>
            <Body {...common} side="front" />
          </div>
          <div
            className="absolute inset-0"
            style={{ backfaceVisibility: "hidden", transform: "rotateY(180deg)", pointerEvents: side === "back" ? "auto" : "none" }}
          >
            <Body {...common} side="back" />
          </div>
        </div>
      </div>
      {/* Floor shadow: drifts opposite the tilt, so the figure seems to stand above the card. */}
      <div
        className="pointer-events-none mx-auto -mt-3 h-4 w-2/3 rounded-[50%]"
        style={{
          background: "radial-gradient(closest-side, rgba(0,0,0,0.35), transparent)",
          transform: `translateX(calc(var(--tx, 0) * -10px))`,
          transition: "transform 160ms ease-out",
        }}
      />
      {hovered && tooltip && (
        <div ref={tip} className="pointer-events-none absolute left-0 top-0 z-10 w-52" style={{ transform: `translate3d(${pointer.current.x + 14}px, ${pointer.current.y + 14}px, 0)` }}>
          <div className="pop-in origin-top-left rounded-lg border border-line-2 bg-panel p-3 text-xs shadow-xl">{tooltip}</div>
        </div>
      )}
    </div>
  );
}

/**
 * Lighting filters, in the artwork's user units (the figure is 724 units wide).
 * shade: diffuse light from the top-left darkens each muscle's far edge and a
 * soft specular highlight sits on its near edge, which reads as gentle depth.
 * glow: the same, plus a blurred halo in the muscle's own colour.
 */
function FigureFilters({ scope }: { scope: string }) {
  const lit = (
    <>
      <feGaussianBlur in="SourceAlpha" stdDeviation="7" result="bump" />
      <feDiffuseLighting in="bump" surfaceScale="5" diffuseConstant="1.18" lightingColor="#ffffff" result="diffuse">
        <feDistantLight azimuth="225" elevation="58" />
      </feDiffuseLighting>
      <feComposite in="SourceGraphic" in2="diffuse" operator="arithmetic" k1="1" k2="0" k3="0" k4="0" result="shaded" />
      <feSpecularLighting in="bump" surfaceScale="5" specularConstant="0.7" specularExponent="20" lightingColor="#ffffff" result="spec">
        <feDistantLight azimuth="225" elevation="40" />
      </feSpecularLighting>
      <feComposite in="spec" in2="SourceAlpha" operator="in" result="specIn" />
      <feComposite in="specIn" in2="shaded" operator="arithmetic" k1="0" k2="0.32" k3="1" k4="0" result="litRaw" />
      <feComposite in="litRaw" in2="SourceAlpha" operator="in" result="lit" />
    </>
  );
  return (
    <svg width="0" height="0" className="absolute" focusable="false">
      <defs>
        <filter id={`${scope}-shade`} x="-5%" y="-5%" width="110%" height="110%" colorInterpolationFilters="sRGB">
          {lit}
        </filter>
        <filter id={`${scope}-glow`} x="-40%" y="-40%" width="180%" height="180%" colorInterpolationFilters="sRGB">
          {lit}
          <feGaussianBlur in="SourceGraphic" stdDeviation="12" result="halo" />
          <feColorMatrix in="halo" type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 0.8 0" result="haloSoft" />
          <feMerge>
            <feMergeNode in="haloSoft" />
            <feMergeNode in="lit" />
          </feMerge>
        </filter>
      </defs>
    </svg>
  );
}
