import type { Settings } from "@ascend/shared";
import { useState } from "react";

import { api } from "../api/client";
import { IconDatabase } from "../components/Icons";
import { Segmented } from "../components/Segmented";
import { LoadingLayout, SkeletonCard } from "../components/Skeleton";
import { ErrorState } from "../components/States";
import { useToast } from "../components/Toast";
import { kcal } from "../lib/format";
import { usePrefs } from "../lib/prefs";
import { isOffline, useApi } from "../lib/useApi";
import { ProfileForm } from "./Onboarding";

const SHORTCUTS: [string, string][] = [
  ["Ctrl+1 … Ctrl+9, Ctrl+0", "Open a page, in sidebar order"],
  ["Tab / Shift+Tab", "Move between controls; the first Tab offers “Skip to content”"],
  ["Alt+← / Alt+→", "Back / forward between pages"],
  ["Enter", "Log the set or confirm the form you are in"],
  ["Esc", "Close an open detail panel"],
];

export function SettingsPage({ onToggleAi, onChanged, onOpenData }: { onToggleAi: () => void; onChanged: () => void; onOpenData: () => void }) {
  const profile = useApi(api.profile, []);
  const toast = useToast();
  const { settings, update } = usePrefs();
  const aiEnabled = settings.ai_enabled;

  async function save(patch: Partial<Settings>, message: string) {
    try {
      await update(patch);
      toast(message, "info");
      onChanged();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  if (profile.loading && !profile.data) {
    return (
      <LoadingLayout label="Loading settings…">
        <div className="grid max-w-5xl gap-5 lg:grid-cols-2">{[6, 3, 4, 2].map((n, i) => <SkeletonCard key={i} lines={n} />)}</div>
      </LoadingLayout>
    );
  }
  if (!profile.data) return <ErrorState message={profile.error ?? "No profile"} onRetry={profile.reload} offline={isOffline(profile.status)} />;
  const p = profile.data;

  return (
    <div className="grid max-w-5xl grid-cols-12 gap-5">
      <section className="card col-span-12 p-5 lg:col-span-7">
        <h2 className="card-title mb-4">Profile & targets</h2>
        <ProfileForm initial={p} submitLabel="Save profile" onSaved={() => { toast("Profile saved", "info"); profile.reload(); onChanged(); }} />
        <p className="mt-4 text-xs text-muted">
          Current estimate: BMR {kcal(p.energy.bmr)} · TDEE {kcal(p.energy.tdee)} · target {kcal(p.energy.kcal_target)} kcal ·
          protein {p.energy.protein_target_g} g <span className="text-faint">({p.energy.formula_version}, estimate)</span>
        </p>
      </section>
      <div className="col-span-12 space-y-5 lg:col-span-5">
        <section className="card p-5">
          <h2 className="card-title mb-3">AI coach</h2>
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">Use local AI (Ollama · qwen3:4b)<br /><span className="text-xs text-muted">Off = rule-based tips only. Nothing leaves this PC either way.</span></span>
            <input type="checkbox" className="h-5 w-5 accent-accent" checked={Boolean(aiEnabled)} onChange={onToggleAi} />
          </label>
        </section>
        <OnlineResearch enabled={Boolean(settings.online_lookup)} onChange={(on) => save({ online_lookup: on }, on ? "Online research: on" : "Online research: off")} />
        <section className="card space-y-4 p-5" aria-labelledby="appearance-title">
          <h2 id="appearance-title" className="card-title">Appearance</h2>
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">Theme</span>
            <Segmented
              label="Theme"
              value={settings.theme}
              options={[{ value: "dark", label: "Dark" }, { value: "light", label: "Light" }, { value: "system", label: "System" }]}
              onChange={(theme) => save({ theme }, `Theme: ${theme}`)}
            />
          </div>
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">
              Reduce motion
              <br />
              <span className="text-xs text-muted">No tilt, flips, count-ups or celebrations. Your Windows animation setting is always honoured.</span>
            </span>
            <input
              type="checkbox"
              className="h-5 w-5 shrink-0 accent-accent"
              checked={Boolean(settings.reduce_motion)}
              onChange={(e) => save({ reduce_motion: e.target.checked }, e.target.checked ? "Reduce motion: on" : "Reduce motion: off")}
            />
          </label>
        </section>
        <section className="card space-y-4 p-5" aria-labelledby="units-title">
          <h2 id="units-title" className="card-title">Units & training</h2>
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">Units</span>
            <Segmented
              label="Units"
              value={settings.units}
              options={[{ value: "metric", label: "kg · cm · km" }, { value: "imperial", label: "lb · in · mi" }]}
              onChange={(units) => save({ units }, units === "metric" ? "Units: metric" : "Units: imperial")}
            />
          </div>
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">
              Training days per week
              <br />
              <span className="text-xs text-muted">Used by the weekly review to judge adherence.</span>
            </span>
            <select
              className="input w-20"
              value={settings.sessions_per_week}
              onChange={(e) => save({ sessions_per_week: Number(e.target.value) }, "Training days saved")}
            >
              {[1, 2, 3, 4, 5, 6, 7].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
        </section>
        <section className="card p-5">
          <h2 className="card-title mb-2">Your data</h2>
          <p className="mb-3 text-sm text-muted">Import history from Strong or Hevy, or export everything you logged.</p>
          <button type="button" className="btn-ghost" onClick={onOpenData}><IconDatabase width={16} height={16} /> Open Import & export</button>
        </section>
        <section className="card p-5" aria-labelledby="keys-title">
          <h2 id="keys-title" className="card-title mb-3">Keyboard shortcuts</h2>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-xs">
            {SHORTCUTS.map(([keys, what]) => (
              <div key={keys} className="contents">
                <dt><kbd className="chip font-mono">{keys}</kbd></dt>
                <dd className="text-muted">{what}</dd>
              </div>
            ))}
          </dl>
        </section>
        <section className="card p-5 text-xs leading-relaxed text-muted">
          <h2 className="card-title mb-2">About</h2>
          ASCEND {__APP_VERSION__} · MIT licence · © the ASCEND team.<br />
          Muscle map artwork: react-muscle-highlighter (MIT).<br />
          Food values: approximate, IFCT 2017 / INDB-style.<br />
          TDEE (Mifflin-St Jeor), e1RM (Epley) and burn (MET) are estimates.
        </section>
      </div>
    </div>
  );
}

/**
 * The one feature that contacts the internet. Turning it on needs an explicit "Allow"
 * after reading what is sent; turning it off is one click. Every lookup is logged here.
 */
export function OnlineResearch({ enabled, onChange }: { enabled: boolean; onChange: (on: boolean) => void }) {
  const [asking, setAsking] = useState(false);
  return (
    <section className="card p-5" aria-labelledby="online-title">
      <h2 id="online-title" className="card-title mb-3">Online research</h2>
      <label className="flex items-center justify-between gap-4">
        <span className="text-sm text-ink">
          Research exercises you add on wger.de and Wikipedia
          <br />
          <span className="text-xs text-muted">Off by default. When off, ASCEND makes no internet requests at all; you can still allow a single lookup while adding an exercise.</span>
        </span>
        <input
          type="checkbox"
          className="h-5 w-5 shrink-0 accent-accent"
          checked={enabled || asking}
          onChange={(e) => (e.target.checked ? setAsking(true) : (setAsking(false), onChange(false)))}
        />
      </label>
      {asking && !enabled && (
        <div className="mt-3 rounded-lg border border-line-2 bg-panel-2 p-3 text-xs text-muted" role="group" aria-label="Allow online research?">
          <p className="text-ink">Allow online research?</p>
          <p className="mt-1">
            When the offline details of an exercise you add are not enough (or you ask), ASCEND sends <strong className="text-ink">only the exercise name</strong> to
            wger.de (an open exercise database) and Wikipedia, then shows a research report with a link for every value. You confirm before anything is saved.
            Nothing else about you or your training leaves this PC.
          </p>
          <div className="mt-3 flex gap-2">
            <button type="button" className="btn btn-primary px-3 py-1.5 text-xs" onClick={() => { setAsking(false); onChange(true); }}>Allow</button>
            <button type="button" className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setAsking(false)}>Cancel</button>
          </div>
        </div>
      )}
      <LookupLog />
    </section>
  );
}

const OUTCOME_TEXT: Record<string, string> = {
  ok: "found", not_found: "nothing found", offline: "no connection", timeout: "timed out", rate_limited: "rate limited", error: "failed",
};

/** The local log of online lookups: when, what, where, outcome. Clearable. */
export function LookupLog() {
  const log = useApi(() => api.onlineLog(50), []);
  const toast = useToast();
  async function clear() {
    try {
      await api.clearOnlineLog();
      log.reload();
      toast("Lookup log cleared", "info");
    } catch (err) {
      toast((err as Error).message, "error");
    }
  }
  const rows = log.data ?? [];
  return (
    <div className="mt-4 border-t border-line pt-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-xs uppercase tracking-wider text-faint">Lookup log (stored on this PC)</h3>
        <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={clear} disabled={rows.length === 0}>Clear log</button>
      </div>
      {log.error && !log.data ? (
        <p className="mt-2 text-xs text-muted">The log could not be loaded.</p>
      ) : rows.length === 0 ? (
        <p className="mt-2 text-xs text-muted">{log.loading ? "Loading…" : "No online lookups yet."}</p>
      ) : (
        <div className="mt-2 max-h-56 overflow-y-auto">
          <table className="w-full text-left text-xs">
            <caption className="sr-only">Online lookups, newest first</caption>
            <thead className="text-faint">
              <tr>
                <th scope="col" className="py-1 pr-3 font-normal">When</th>
                <th scope="col" className="py-1 pr-3 font-normal">Looked up</th>
                <th scope="col" className="py-1 pr-3 font-normal">Sources</th>
                <th scope="col" className="py-1 font-normal">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-line">
                  <td className="py-1.5 pr-3 text-muted">{new Date(r.at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}</td>
                  <td className="py-1.5 pr-3 text-ink">“{r.query}”{r.consent === "once" && <span className="text-faint"> · once</span>}</td>
                  <td className="py-1.5 pr-3 text-muted">
                    {[...new Set(r.sources.map((x) => (x.source === "wger" ? "wger.de" : "Wikipedia")))].join(", ")}
                    <span className="text-faint"> · {r.sources.filter((x) => x.status !== "skipped").length} requests</span>
                  </td>
                  <td className="py-1.5 text-muted">{OUTCOME_TEXT[r.outcome] ?? r.outcome}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
