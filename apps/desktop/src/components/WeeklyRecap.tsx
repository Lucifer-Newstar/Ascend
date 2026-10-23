/**
 * Weekly recap (v1.2, item 13) on Progress: the week in numbers and a "Play recap" button
 * that plays a short video drawn on this PC (see lib/recap.ts). "Save video" records it as
 * a WebM file through the save dialog. Body-neutral: no weight or body numbers.
 */
import type { WeekRecap } from "@ascend/shared";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { api } from "../api/client";
import { useReducedMotion } from "../lib/motion";
import { canRecord, drawFrame, readPalette, recapLength, recapSlides, recordRecap, saveVideo, weekLabel, RECAP_H, RECAP_W } from "../lib/recap";
import { useApi } from "../lib/useApi";
import { Panel } from "./Page";
import { Segmented } from "./Segmented";
import { useToast } from "./Toast";
import { useTrainer } from "./Trainer";

const DAY_MS = 86_400_000;

function lastWeekIso(): string {
  return new Date(Date.now() - 7 * DAY_MS).toISOString().slice(0, 10);
}

export function WeeklyRecapPanel({ refreshKey = 0, index = 4 }: { refreshKey?: number; index?: number }) {
  const [which, setWhich] = useState<"this" | "last">("this");
  const r = useApi(() => (which === "this" ? api.recap() : api.recap(lastWeekIso())), [refreshKey, which]);
  const [playing, setPlaying] = useState(false);
  const d = r.data;
  return (
    <Panel id="recap" index={index} className="col-span-12" title="Weekly recap"
      hint="A short video of your week, made on this PC. Sessions, records, your boss and your streak."
      action={<Segmented label="Which week" value={which} onChange={(v) => setWhich(v as "this" | "last")}
        options={[{ value: "this", label: "This week" }, { value: "last", label: "Last week" }]} />}
      loading={r.loading && !d} error={!d ? r.error ?? null : null} onRetry={r.reload}>
      {d && (
        <div className="flex flex-wrap items-center gap-4" data-testid="recap-summary">
          <div className="min-w-0 flex-1">
            <div className="text-sm text-muted">{weekLabel(d)}{d.complete ? "" : " · so far"}</div>
            <p className="mt-1 text-ink">{d.headline}</p>
            <p className="mt-1 text-xs text-muted">
              {d.sessions} {d.sessions === 1 ? "session" : "sessions"} · {d.sets} sets · {d.prs.length} {d.prs.length === 1 ? "record" : "records"} · {d.streak}-day streak
            </p>
          </div>
          <button type="button" className="btn-primary" onClick={() => setPlaying(true)}>Play recap</button>
        </div>
      )}
      {d && playing && <RecapPlayer recap={d} onClose={() => setPlaying(false)} />}
    </Panel>
  );
}

export function RecapPlayer({ recap, onClose }: { recap: WeekRecap; onClose: () => void }) {
  const trainer = useTrainer();
  const reduced = useReducedMotion();
  const toast = useToast();
  const canvas = useRef<HTMLCanvasElement>(null);
  const [run, setRun] = useState(0);
  const [saving, setSaving] = useState(false);
  const slides = recapSlides(recap, trainer.name);
  const total = recapLength(slides);

  useEffect(() => {
    const ctx = canvas.current?.getContext?.("2d") ?? null;
    if (!ctx) return;
    const palette = readPalette();
    let raf = 0;
    const start = performance.now();
    const tick = () => {
      const t = performance.now() - start;
      drawFrame(ctx, slides, t, palette, reduced);
      if (t < total) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // slides are derived from recap and trainer; run restarts the playback
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run, recap, trainer.name, reduced, total]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function save() {
    setSaving(true);
    try {
      const off = document.createElement("canvas");
      const blob = await recordRecap(off, slides, readPalette());
      if (await saveVideo(`ascend-recap-${recap.week_start}.webm`, blob)) toast("Recap video saved", "info");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not save the video", "error");
    } finally {
      setSaving(false);
    }
  }

  const recordable = canRecord();
  // A portal, so a parent card's transform can't pin the full-screen player inside it.
  return createPortal(
    <div role="dialog" aria-modal="true" aria-labelledby="recap-player-title" data-testid="recap-player"
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg p-6">
      <div className="w-full max-w-4xl space-y-3 rounded-xl border border-line bg-panel p-4">
        <div className="flex items-center justify-between gap-3">
          <h2 id="recap-player-title" className="card-title">Your week · {weekLabel(recap)}</h2>
          <button type="button" className="btn-ghost" onClick={onClose}>Close</button>
        </div>
        <canvas ref={canvas} width={RECAP_W} height={RECAP_H} className="aspect-video w-full rounded-lg border border-line"
          role="img" aria-label={slides.map((s) => `${s.kicker}: ${s.count !== undefined ? `${s.count} ${s.unit ?? ""}` : s.big}. ${s.lines.join(" ")}`).join(" ")} />
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className="btn-ghost" onClick={() => setRun((n) => n + 1)}>Replay</button>
          <button type="button" className="btn-primary" disabled={!recordable || saving} onClick={() => void save()}
            title={recordable ? undefined : "Video recording isn't available here"}>
            {saving ? "Recording…" : "Save video"}
          </button>
          <span className="text-xs text-muted">About {Math.round(total / 1000)} seconds. Made on this PC; nothing is uploaded.</span>
        </div>
      </div>
    </div>,
    document.body,
  );
}
