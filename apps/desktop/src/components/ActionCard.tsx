/**
 * The confirm card for an in-app action (actions-v1). The chat, the command bar and the
 * local AI can only PROPOSE an action from the shared allowlist; nothing runs until you
 * press Confirm here (a destructive one also needs its word typed). A done action offers
 * Undo where the action can be undone. Every step is in the audit log (Settings).
 */
import type { ActionProposal } from "@ascend/shared";
import { useState } from "react";

import { api } from "../api/client";

export function ActionCard({ initial, onDone }: { initial: ActionProposal; onDone?: (a: ActionProposal) => void }) {
  const [a, setA] = useState(initial);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(step: () => Promise<ActionProposal>) {
    setBusy(true);
    setError(null);
    try {
      const next = await step();
      setA(next);
      onDone?.(next);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const needsWord = Boolean(a.confirm_word);
  const wordOk = !needsWord || typed.trim().toLowerCase() === a.confirm_word;
  return (
    <div className="mt-2 rounded-lg border border-accent/40 bg-panel p-3" data-testid="action-card" data-status={a.status}>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-accent">{a.status === "proposed" ? "Confirm action" : a.label}</p>
      {a.status === "proposed" && <p className="text-sm font-semibold text-ink">{a.label}</p>}
      <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs text-ink">
        {a.summary.map((line) => <li key={line}>{line}</li>)}
      </ul>
      {a.status === "proposed" && (
        <>
          {needsWord && (
            <label className="mt-2 block text-xs text-muted">
              Type <b className="text-ink">{a.confirm_word}</b> to confirm
              <input className="input mt-1 w-full" value={typed} onChange={(e) => setTyped(e.target.value)} aria-label={`Type ${a.confirm_word} to confirm`} />
            </label>
          )}
          <div className="mt-2 flex gap-2">
            <button type="button" className="btn-primary px-3 py-1 text-xs" disabled={busy || !wordOk}
              onClick={() => void run(() => api.confirmAction(a.id, needsWord ? typed.trim() : null))}>Confirm</button>
            <button type="button" className="btn-ghost px-3 py-1 text-xs" disabled={busy} onClick={() => void run(() => api.cancelAction(a.id))}>Cancel</button>
          </div>
        </>
      )}
      {a.status === "executed" && (
        <div className="mt-2 flex items-center gap-2 text-xs text-good">
          <span role="status">Done.</span>
          {a.undoable && <button type="button" className="btn-ghost px-2 py-0.5 text-xs" disabled={busy} onClick={() => void run(() => api.undoAction(a.id))}>Undo</button>}
        </div>
      )}
      {a.status === "undone" && <p role="status" className="mt-2 text-xs text-muted">Undone.</p>}
      {a.status === "cancelled" && <p role="status" className="mt-2 text-xs text-muted">Cancelled. Nothing changed.</p>}
      {a.status === "failed" && <p role="alert" className="mt-2 text-xs text-bad">{a.error ?? "That didn't work."}</p>}
      {error && <p role="alert" className="mt-2 text-xs text-bad">{error}</p>}
    </div>
  );
}
