/**
 * Unlocks (v1.4): every skill step, boss clear, rank and cosmetic you have unlocked, with
 * the date it first appeared, newest first. Any of them replays its unlock scene. Opened
 * from Profile (Achievements > All unlocks); it has no nav entry of its own.
 */
import type { UnlockEntry, UnlockKind } from "@ascend/shared";
import { useState } from "react";

import { api } from "../api/client";
import { PageGrid, Panel } from "../components/Page";
import { Segmented } from "../components/Segmented";
import { KIND_LABEL, SceneArt, UnlockScene } from "../components/UnlockScene";
import { useOptionalPrefs } from "../lib/prefs";
import { useApi } from "../lib/useApi";

type Filter = "all" | UnlockKind;
const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "boss", label: "Bosses" },
  { value: "rank", label: "Ranks" },
  { value: "cosmetic", label: "Cosmetics" },
  { value: "skill", label: "Skills" },
];

const day = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

export function UnlocksPage({ refreshKey = 0, onBack }: { refreshKey?: number; onBack?: () => void }) {
  const log = useApi(api.unlocks, [refreshKey]);
  const prefs = useOptionalPrefs();
  const [filter, setFilter] = useState<Filter>("all");
  const [replay, setReplay] = useState<UnlockEntry | null>(null);
  const rows = (log.data ?? []).filter((u) => filter === "all" || u.kind === filter);
  return (
    <PageGrid label="Unlocks">
      <Panel id="unlocks" index={0} className="col-span-12" title="Achievements and unlocks"
        hint="Everything you have unlocked, with the day it first appeared. Replay any of them."
        action={onBack && <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={onBack}>Back to Profile</button>}
        loading={log.loading && !log.data} error={!log.data ? log.error ?? null : null} onRetry={log.reload}>
        <Segmented label="Show" value={filter} options={FILTERS} onChange={setFilter} />
        {rows.length === 0 ? (
          <p className="mt-4 text-sm text-muted">Nothing here yet. Your first boss win, rank or new cosmetic shows up here.</p>
        ) : (
          <ul className="mt-4 grid gap-2 md:grid-cols-2" aria-label="Unlocks">
            {rows.map((u) => (
              <li key={u.key} className="flex items-center gap-3 rounded-lg border border-line-2 p-2" data-testid="unlock-row">
                <span className="grid h-14 w-14 shrink-0 place-items-center" aria-hidden="true"><SceneArt entry={u} look={prefs?.settings.avatar ?? "male"} size={52} /></span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink">{u.title}</p>
                  <p className="text-[11px] text-muted">{KIND_LABEL[u.kind]} · {u.seeded ? `by ${day(u.at)}` : day(u.at)}</p>
                  {u.detail && <p className="truncate text-[11px] text-faint">{u.detail}</p>}
                </div>
                <button type="button" className="btn-ghost shrink-0 px-2 py-1 text-xs" onClick={() => setReplay(u)} aria-label={`Replay: ${u.title}`}>Replay</button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      {replay && <UnlockScene key={replay.key} entries={[replay]} onDone={() => setReplay(null)} look={prefs?.settings.avatar ?? "male"} />}
    </PageGrid>
  );
}
