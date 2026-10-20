/**
 * Skill-tree canvas: every tree of a family drawn as nodes and edges on one pannable,
 * zoomable surface (transform only, so it stays on the compositor).
 *
 * - Nodes show their state with colour, an icon and text: mastered (check), next step
 *   (a % ring, glowing), locked (lock, dimmed). Never colour alone.
 * - Keyboard: one node is in the tab order; arrow keys move along the edges (←/→) and
 *   between trees (↑/↓), Home jumps to the current step, Enter or a click selects it.
 * - Mouse: wheel zooms around the pointer, dragging the background pans, and
 *   "Centre on current" brings the next step into view.
 */
import type { SkillDetail, SkillStep } from "@ascend/shared";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";

import { IconCheck, IconLock } from "./Icons";

export const NODE_W = 150;
export const NODE_H = 46;
const COL_GAP = 40;
const ROW_GAP = 18;
const LABEL_W = 150;
const PAD = 24;

export interface PlacedNode {
  id: string; // `${tree}/${step}`
  tree: string;
  treeName: string;
  step: SkillStep;
  col: number;
  row: number; // global row on the canvas
  x: number;
  y: number;
}

export interface PlacedEdge {
  from: string;
  to: string;
  done: boolean;
}

export interface TreeLayout {
  nodes: PlacedNode[];
  edges: PlacedEdge[];
  labels: { tree: string; name: string; y: number }[];
  width: number;
  height: number;
}

/**
 * Pure layout: a step's column is one more than the deepest step it requires (entry
 * steps sit in column 0). Steps sharing a column within a tree (branches) stack into
 * extra rows. Trees are stacked top to bottom in the given order.
 */
export function layoutTrees(trees: Pick<SkillDetail, "key" | "name" | "steps">[]): TreeLayout {
  const nodes: PlacedNode[] = [];
  const edges: PlacedEdge[] = [];
  const labels: TreeLayout["labels"] = [];
  let row = 0;
  let maxCol = 0;
  for (const t of trees) {
    const col = new Map<string, number>();
    const reqs = (s: SkillStep, i: number) => (s.requires.length ? s.requires : i > 0 ? [t.steps[i - 1].key] : []);
    t.steps.forEach((s, i) => {
      const r = reqs(s, i).filter((k) => col.has(k));
      col.set(s.key, r.length ? Math.max(...r.map((k) => col.get(k) ?? 0)) + 1 : 0);
    });
    const usedRows = new Map<number, number>(); // column -> rows used in this tree
    let treeRows = 1;
    const startRow = row;
    t.steps.forEach((s, i) => {
      const c = col.get(s.key) ?? 0;
      const sub = usedRows.get(c) ?? 0;
      usedRows.set(c, sub + 1);
      treeRows = Math.max(treeRows, sub + 1);
      maxCol = Math.max(maxCol, c);
      nodes.push({
        id: `${t.key}/${s.key}`,
        tree: t.key,
        treeName: t.name,
        step: s,
        col: c,
        row: startRow + sub,
        x: PAD + LABEL_W + c * (NODE_W + COL_GAP),
        y: PAD + (startRow + sub) * (NODE_H + ROW_GAP),
      });
      for (const r of reqs(s, i)) {
        const from = t.steps.find((x) => x.key === r);
        if (from) edges.push({ from: `${t.key}/${r}`, to: `${t.key}/${s.key}`, done: from.status === "unlocked" && s.status === "unlocked" });
      }
    });
    labels.push({ tree: t.key, name: t.name, y: PAD + startRow * (NODE_H + ROW_GAP) });
    row += treeRows;
    row += 0.5; // breathing room between trees
  }
  return {
    nodes,
    edges,
    labels,
    width: PAD * 2 + LABEL_W + (maxCol + 1) * NODE_W + maxCol * COL_GAP,
    height: PAD * 2 + Math.ceil(row) * (NODE_H + ROW_GAP),
  };
}

/** The node an arrow key moves to, following edges first, then neighbouring trees. */
export function neighbour(layout: TreeLayout, id: string, key: string): string | null {
  const here = layout.nodes.find((n) => n.id === id);
  if (!here) return null;
  if (key === "ArrowRight") {
    const out = layout.edges.filter((e) => e.from === id).map((e) => layout.nodes.find((n) => n.id === e.to)!);
    return out.sort((a, b) => a.row - b.row)[0]?.id ?? null;
  }
  if (key === "ArrowLeft") {
    const into = layout.edges.filter((e) => e.to === id).map((e) => layout.nodes.find((n) => n.id === e.from)!);
    return into.sort((a, b) => a.row - b.row)[0]?.id ?? null;
  }
  if (key === "ArrowDown" || key === "ArrowUp") {
    const down = key === "ArrowDown";
    const candidates = layout.nodes.filter((n) => (down ? n.row > here.row : n.row < here.row));
    if (!candidates.length) return null;
    const rowTarget = down ? Math.min(...candidates.map((n) => n.row)) : Math.max(...candidates.map((n) => n.row));
    const inRow = candidates.filter((n) => n.row === rowTarget);
    return inRow.sort((a, b) => Math.abs(a.col - here.col) - Math.abs(b.col - here.col))[0].id;
  }
  return null;
}

export function stateLabel(step: SkillStep): string {
  if (step.status === "unlocked") return "mastered";
  if (step.status === "next") return step.pct > 0 ? `in progress, ${Math.round(step.pct)}%` : "available";
  return "locked";
}

function Ring({ pct }: { pct: number }) {
  const r = 11;
  const c = 2 * Math.PI * r;
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true" className="shrink-0 -rotate-90">
      <circle cx="14" cy="14" r={r} fill="none" stroke="var(--color-line-2)" strokeWidth="3" />
      <circle cx="14" cy="14" r={r} fill="none" stroke="var(--color-accent)" strokeWidth="3" strokeLinecap="round"
        strokeDasharray={`${(Math.max(0, Math.min(100, pct)) / 100) * c} ${c}`} />
    </svg>
  );
}

function Node({ n, selected, focusable, onSelect, onKey, register }: {
  n: PlacedNode;
  selected: boolean;
  focusable: boolean;
  onSelect: (id: string) => void;
  onKey: (e: KeyboardEvent<HTMLButtonElement>, id: string) => void;
  register: (id: string, el: HTMLButtonElement | null) => void;
}) {
  const s = n.step;
  const tone = s.status === "unlocked"
    ? "border-good/70 text-ink"
    : s.status === "next"
      ? "border-accent text-ink skill-node-current"
      : "border-line-2 text-muted";
  return (
    <button
      ref={(el) => register(n.id, el)}
      type="button"
      tabIndex={focusable ? 0 : -1}
      data-node={n.id}
      data-state={s.status}
      aria-pressed={selected}
      aria-label={`${s.name} (${n.treeName}), ${stateLabel(s)}`}
      onClick={() => onSelect(n.id)}
      onKeyDown={(e) => onKey(e, n.id)}
      className={`absolute flex items-center gap-2 rounded-md border bg-panel px-2 text-left text-xs transition-[transform,border-color] duration-150 hover:-translate-y-px ${tone} ${selected ? "ring-2 ring-accent ring-offset-2 ring-offset-bg" : ""}`}
      style={{ left: n.x, top: n.y, width: NODE_W, height: NODE_H }}
    >
      {s.status === "unlocked" ? (
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-good text-bg"><IconCheck width={14} aria-hidden="true" /></span>
      ) : s.status === "next" ? (
        <Ring pct={s.pct} />
      ) : (
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-line-2 text-faint"><IconLock width={12} aria-hidden="true" /></span>
      )}
      <span className="min-w-0">
        <span className="line-clamp-2 font-medium leading-tight">{s.name}</span>
        <span className="block text-[10px] leading-tight text-faint" aria-hidden="true">
          {s.status === "next" ? `${Math.round(s.pct)}%` : s.status === "unlocked" ? "Mastered" : "Locked"}
        </span>
      </span>
    </button>
  );
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export function SkillTreeCanvas({ trees, selected, onSelect, label, fitAll = false }: {
  trees: SkillDetail[];
  /** Fit the whole layout (width and height) instead of the width only. */
  fitAll?: boolean;
  selected: string | null;
  onSelect: (id: string) => void;
  label: string;
}) {
  const layout = useMemo(() => layoutTrees(trees), [trees]);
  const viewport = useRef<HTMLDivElement>(null);
  const els = useRef(new Map<string, HTMLButtonElement>());
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const [focusId, setFocusId] = useState<string | null>(null);
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);
  const current = useMemo(() => layout.nodes.find((n) => n.step.status === "next") ?? layout.nodes[0] ?? null, [layout]);
  const activeId = focusId && layout.nodes.some((n) => n.id === focusId) ? focusId : (selected ?? current?.id ?? null);

  const register = useCallback((id: string, el: HTMLButtonElement | null) => {
    if (el) els.current.set(id, el);
    else els.current.delete(id);
  }, []);

  // Fit the family to the viewport width (never above 100%) when the trees change.
  useLayoutEffect(() => {
    const vp = viewport.current;
    if (!vp || layout.width === 0) return;
    // One family fits whole (down to 50%); "All" fits the width and pans vertically.
    const k = fitAll
      ? clamp(Math.min(1, (vp.clientWidth - 8) / layout.width, (vp.clientHeight - 8) / layout.height), 0.5, 1)
      : clamp(Math.min(1, (vp.clientWidth - 8) / layout.width), 0.65, 1);
    setView({ x: Math.max(4, (vp.clientWidth - layout.width * k) / 2), y: 4, k });
  }, [layout, fitAll]);

  const centreOn = useCallback((id: string | null | undefined) => {
    const vp = viewport.current;
    const n = layout.nodes.find((x) => x.id === id);
    if (!vp || !n) return;
    setView((v) => ({ ...v, x: vp.clientWidth / 2 - (n.x + NODE_W / 2) * v.k, y: vp.clientHeight / 2 - (n.y + NODE_H / 2) * v.k }));
  }, [layout]);

  const zoomBy = useCallback((factor: number, cx?: number, cy?: number) => {
    const vp = viewport.current;
    if (!vp) return;
    const px = cx ?? vp.clientWidth / 2;
    const py = cy ?? vp.clientHeight / 2;
    setView((v) => {
      const k = clamp(v.k * factor, 0.4, 1.8);
      return { k, x: px - ((px - v.x) * k) / v.k, y: py - ((py - v.y) * k) / v.k };
    });
  }, []);

  // Wheel zoom needs a non-passive listener to keep the page from scrolling.
  useEffect(() => {
    const vp = viewport.current;
    if (!vp) return;
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && Math.abs(e.deltaY) < 1) return;
      e.preventDefault();
      const rect = vp.getBoundingClientRect();
      zoomBy(e.deltaY < 0 ? 1.1 : 1 / 1.1, e.clientX - rect.left, e.clientY - rect.top);
    };
    vp.addEventListener("wheel", onWheel, { passive: false });
    return () => vp.removeEventListener("wheel", onWheel);
  }, [zoomBy]);

  function onPointerDown(e: PointerEvent<HTMLDivElement>) {
    if ((e.target as HTMLElement).closest("button")) return;
    drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y };
    e.currentTarget.setPointerCapture?.(e.pointerId);
  }
  function onPointerMove(e: PointerEvent<HTMLDivElement>) {
    const d = drag.current;
    if (!d) return;
    setView((v) => ({ ...v, x: d.vx + e.clientX - d.x, y: d.vy + e.clientY - d.y }));
  }
  function onPointerUp() {
    drag.current = null;
  }

  function onKey(e: KeyboardEvent<HTMLButtonElement>, id: string) {
    let next: string | null = null;
    if (e.key === "Home") next = current?.id ?? null;
    else next = neighbour(layout, id, e.key);
    if (!next && !e.key.startsWith("Arrow") && e.key !== "Home") return;
    e.preventDefault();
    if (!next) return;
    setFocusId(next);
    els.current.get(next)?.focus();
    // Keep the focused node in view.
    const vp = viewport.current;
    const n = layout.nodes.find((x) => x.id === next);
    if (vp && n) {
      const sx = n.x * view.k + view.x;
      const sy = n.y * view.k + view.y;
      if (sx < 0 || sy < 0 || sx + NODE_W * view.k > vp.clientWidth || sy + NODE_H * view.k > vp.clientHeight) centreOn(next);
    }
  }

  const byId = useMemo(() => new Map(layout.nodes.map((n) => [n.id, n])), [layout]);
  return (
    <div className="flex h-[calc(100vh-330px)] min-h-[420px] flex-col">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <button type="button" className="btn-ghost px-3 py-1.5 text-xs" onClick={() => centreOn(current?.id)}>Centre on current</button>
        <span className="flex items-center rounded-md border border-line">
          <button type="button" className="px-2.5 py-1 text-sm text-muted hover:text-ink" aria-label="Zoom out" onClick={() => zoomBy(1 / 1.2)}>−</button>
          <span className="w-12 text-center text-xs tabular-nums text-muted" aria-live="polite">{Math.round(view.k * 100)}%</span>
          <button type="button" className="px-2.5 py-1 text-sm text-muted hover:text-ink" aria-label="Zoom in" onClick={() => zoomBy(1.2)}>+</button>
        </span>
        <span className="ml-auto text-[11px] text-faint">Arrows move along the tree · Home: current step · wheel zooms · drag to pan</span>
      </div>
      <div
        ref={viewport}
        role="group"
        aria-label={label}
        className="relative min-h-0 flex-1 cursor-grab touch-none overflow-hidden rounded-md border border-line bg-[radial-gradient(circle,var(--color-line)_1px,transparent_1px)] [background-size:22px_22px] active:cursor-grabbing"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        data-testid="skill-canvas"
      >
        <div className="absolute left-0 top-0 origin-top-left will-change-transform" style={{ width: layout.width, height: layout.height, transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})` }}>
          <svg width={layout.width} height={layout.height} className="absolute inset-0" aria-hidden="true">
            {layout.edges.map((e) => {
              const a = byId.get(e.from)!;
              const b = byId.get(e.to)!;
              const x1 = a.x + NODE_W;
              const y1 = a.y + NODE_H / 2;
              const x2 = b.x;
              const y2 = b.y + NODE_H / 2;
              const mx = (x1 + x2) / 2;
              return <path key={`${e.from}-${e.to}`} d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`} fill="none"
                stroke={e.done ? "var(--color-good)" : "var(--color-line-2)"} strokeWidth={e.done ? 2.5 : 2} strokeDasharray={e.done ? undefined : "5 5"} />;
            })}
          </svg>
          {layout.labels.map((l) => (
            <div key={l.tree} className="absolute font-display text-sm font-semibold uppercase tracking-[0.08em] text-muted" style={{ left: PAD, top: l.y + NODE_H / 2 - 10, width: LABEL_W - 16 }}>
              {l.name}
            </div>
          ))}
          {layout.nodes.map((n) => (
            <Node key={n.id} n={n} selected={selected === n.id} focusable={n.id === activeId} onSelect={(id) => { setFocusId(id); onSelect(id); }} onKey={onKey} register={register} />
          ))}
        </div>
      </div>
    </div>
  );
}
