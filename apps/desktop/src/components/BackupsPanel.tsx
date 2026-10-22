/**
 * Settings → Backups: the snapshots in the backups folder (daily, safety and manual), their
 * sizes, "Back up now" and a confirmed "Restore". The sidecar backs the current data up
 * before restoring, then reopens the database; the window reloads to read it fresh.
 */
import type { BackupInfo } from "@ascend/shared";
import { useState, type CSSProperties } from "react";

import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import { ErrorState } from "./States";
import { useToast } from "./Toast";

const REASON: Record<string, string> = {
  manual: "Manual",
  daily: "Daily",
  "pre-migration": "Before update",
  "pre-restore": "Before restore",
};

function size(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function when(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function BackupsPanel({ style }: { style?: CSSProperties }) {
  const { data, error, reload } = useApi(() => api.backups(), []);
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<BackupInfo | null>(null);

  async function backupNow() {
    setBusy(true);
    try {
      await api.backupNow();
      toast("Backup saved");
      reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Backup failed", "error");
    } finally {
      setBusy(false);
    }
  }

  async function restore(b: BackupInfo) {
    setBusy(true);
    try {
      await api.restoreBackup(b.path);
      toast("Restored. Reloading…");
      window.setTimeout(() => window.location.reload(), 600);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Restore failed", "error");
      setBusy(false);
      setConfirm(null);
    }
  }

  const list = data ?? [];
  const total = list.reduce((n, b) => n + b.size_bytes, 0);
  return (
    <section className="card rise-in p-5" style={style} aria-labelledby="backups-title">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 id="backups-title" className="card-title">Backups</h2>
        <button type="button" className="btn-ghost" onClick={backupNow} disabled={busy}>Back up now</button>
      </div>
      <p className="mb-3 text-sm text-muted">
        A copy of your data is saved once a day while ASCEND runs (the last 14 are kept), and before every app update or restore.
      </p>
      {error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : list.length === 0 ? (
        <p className="text-sm text-muted">{data ? "No backups yet." : "Loading…"}</p>
      ) : (
        <>
          <ul className="max-h-64 divide-y divide-line overflow-auto rounded-md border border-line" aria-label="Backups">
            {list.map((b) => (
              <li key={b.path} className="flex items-center gap-3 px-3 py-2 text-sm">
                <span className="w-32 shrink-0 text-ink">{when(b.created_at)}</span>
                <span className="chip">{REASON[b.reason] ?? b.reason}</span>
                <span className="flex-1 text-right tabular-nums text-muted">{size(b.size_bytes)}</span>
                <button type="button" className="btn-ghost px-2 py-1 text-xs" disabled={busy} onClick={() => setConfirm(b)}
                  aria-label={`Restore the backup from ${when(b.created_at)}`}>
                  Restore
                </button>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-faint">{list.length} backups · {size(total)} in total</p>
        </>
      )}
      {confirm && (
        <div role="alertdialog" aria-labelledby="restore-q" className="mt-3 rounded-md border border-warn/50 bg-panel-2 p-3 text-sm">
          <p id="restore-q" className="text-ink">
            Replace your current data with the backup from {when(confirm.created_at)}? Your current data is backed up first, so you can undo this.
          </p>
          <div className="mt-2 flex gap-2">
            <button type="button" className="btn-primary" disabled={busy} onClick={() => restore(confirm)}>Restore</button>
            <button type="button" className="btn-ghost" disabled={busy} onClick={() => setConfirm(null)}>Cancel</button>
          </div>
        </div>
      )}
    </section>
  );
}
