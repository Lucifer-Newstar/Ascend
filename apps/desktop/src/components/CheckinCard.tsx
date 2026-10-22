/**
 * Morning check-in (about 20 seconds): sleep, energy, soreness, mood. The sidecar turns
 * it into a readiness score and resizes today's training quest (amber: one set fewer,
 * red: mobility instead), so the dashboard reloads after a save.
 */
import type { Checkin, CheckinIn, Soreness } from "@ascend/shared";
import { useState } from "react";

import { api } from "../api/client";
import { ErrorState } from "./States";
import { useApi } from "../lib/useApi";
import { Segmented } from "./Segmented";
import { useToast } from "./Toast";

const SCALE = ["1", "2", "3", "4", "5"] as const;
type Five = (typeof SCALE)[number];
const BAND_CLASS: Record<Checkin["band"], string> = {
  green: "border-good/40 text-good",
  amber: "border-warn/40 text-warn",
  red: "border-bad/40 text-bad",
};

export function CheckinCard({ refreshKey, onSaved }: { refreshKey: number; onSaved: () => void }) {
  const today = useApi(api.checkinToday, [refreshKey]);
  const [editing, setEditing] = useState(false);

  if (today.loading && today.data === undefined) return null;
  if (today.error) return <ErrorState compact message={today.error} onRetry={today.reload} />;
  const done = today.data;
  if (done && !editing) return <CheckinSummary c={done} onRedo={() => setEditing(true)} />;
  return (
    <CheckinForm
      initial={done ?? undefined}
      onSaved={() => {
        setEditing(false);
        today.reload();
        onSaved();
      }}
    />
  );
}

function CheckinSummary({ c, onRedo }: { c: Checkin; onRedo: () => void }) {
  return (
    <div className="flex items-center gap-4">
      <div className={`grid h-14 w-14 shrink-0 place-items-center rounded-full border-2 font-display text-xl font-bold ${BAND_CLASS[c.band]}`} aria-label={`Readiness ${c.readiness} of 100`}>
        {c.readiness}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm text-ink">Readiness {c.band === "green" ? "good" : c.band === "amber" ? "so-so" : "low"} today</div>
        <div className="text-xs text-muted">{c.quest_adjustment}</div>
      </div>
      <button type="button" className="text-xs text-faint hover:text-ink" onClick={onRedo}>Redo</button>
    </div>
  );
}

function CheckinForm({ initial, onSaved }: { initial?: CheckinIn; onSaved: () => void }) {
  const [sleep, setSleep] = useState<Five>(String(initial?.sleep ?? 3) as Five);
  const [energy, setEnergy] = useState<Five>(String(initial?.energy ?? 3) as Five);
  const [mood, setMood] = useState<Five>(String(initial?.mood ?? 3) as Five);
  const [soreness, setSoreness] = useState<Soreness>(initial?.soreness ?? "none");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const five = SCALE.map((v) => ({ value: v, label: v }));

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const c = await api.checkin({ sleep: Number(sleep), energy: Number(energy), soreness, mood: Number(mood) });
      toast(`Readiness ${c.readiness} · ${c.quest_adjustment}`, "info");
      onSaved();
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={save} className="space-y-2.5" aria-label="Morning check-in">
      <Row label="Sleep quality"><Segmented label="Sleep quality" value={sleep} onChange={setSleep} options={five} /></Row>
      <Row label="Energy"><Segmented label="Energy" value={energy} onChange={setEnergy} options={five} /></Row>
      <Row label="Soreness">
        <Segmented label="Soreness" value={soreness} onChange={setSoreness}
          options={[{ value: "none", label: "None" }, { value: "some", label: "Some" }, { value: "a_lot", label: "A lot" }]} />
      </Row>
      <Row label="Mood"><Segmented label="Mood" value={mood} onChange={setMood} options={five} /></Row>
      <div className="flex items-center justify-between pt-1">
        <span className="text-[11px] text-faint">1 = poor · 5 = great</span>
        <button type="submit" className="btn-primary" disabled={busy}>Save check-in</button>
      </div>
    </form>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-muted">{label}</span>
      {children}
    </div>
  );
}
