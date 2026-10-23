/**
 * "Start fresh": erase the user's data after a safety backup. The exercise library and the
 * food table stay. Needs the word ERASE typed, so it can't happen by a stray click.
 */
import type { EraseResult } from "@ascend/shared";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { api } from "../api/client";

export function EraseDialog({ onClose, onErased }: { onClose: () => void; onErased: (r: EraseResult) => void }) {
  const [typed, setTyped] = useState("");
  const [keepPrefs, setKeepPrefs] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const field = useRef<HTMLInputElement>(null);
  useEffect(() => field.current?.focus(), []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, onClose]);

  async function erase() {
    setBusy(true);
    setError(null);
    try {
      onErased(await api.eraseData(keepPrefs));
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  const ok = typed.trim().toUpperCase() === "ERASE";
  // Rendered on <body>: inside an animated card the fixed overlay was clipped and the next
  // card painted over its confirm field (v1.1 audit).
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(3,7,18,0.7)] p-4" data-testid="erase-overlay">
      <div role="alertdialog" aria-modal="true" aria-labelledby="erase-title" aria-describedby="erase-body"
        className="w-full max-w-md rounded-xl border border-bad/60 bg-panel p-5 shadow-2xl">
        <h2 id="erase-title" className="text-lg font-semibold text-ink">Erase my data</h2>
        <div id="erase-body" className="mt-2 space-y-2 text-sm text-muted">
          <p>This deletes your profile, workouts, meals, weigh-ins, check-ins, XP, quests, photos and custom exercises.</p>
          <p>The exercise library and food table stay. A backup is made first, so you can undo this from Settings &gt; Backups.</p>
        </div>
        <label className="mt-4 flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" className="h-4 w-4 accent-accent" checked={keepPrefs} onChange={(e) => setKeepPrefs(e.target.checked)} />
          Keep my preferences (theme, units, AI, trainer)
        </label>
        <label className="mt-4 block text-sm text-ink" htmlFor="erase-confirm">
          Type <strong>ERASE</strong> to confirm
        </label>
        <input id="erase-confirm" ref={field} className="input mt-1 w-full" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
        {error && <p role="alert" className="mt-2 text-sm text-bad">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className="btn-ghost" onClick={onClose} disabled={busy}>Cancel</button>
          <button type="button" className="btn bg-bad text-white hover:opacity-90 disabled:opacity-50" disabled={!ok || busy} onClick={() => void erase()}>
            {busy ? "Erasing…" : "Erase my data"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

/** Settings section: start fresh. */
export function EraseDataPanel({ onErased }: { onErased: (r: EraseResult) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="card rise-in p-5" aria-labelledby="erase-title-section" data-tour="erase">
      <h2 id="erase-title-section" className="card-title mb-2">Start fresh</h2>
      <p className="mb-3 text-sm text-muted">Erase your logs and start again. A backup is made first; the exercise library and food table stay.</p>
      <button type="button" className="btn-ghost border-bad/60 text-bad hover:border-bad hover:text-bad" onClick={() => setOpen(true)}>Erase my data…</button>
      {open && <EraseDialog onClose={() => setOpen(false)} onErased={(r) => { setOpen(false); onErased(r); }} />}
    </section>
  );
}
