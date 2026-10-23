/**
 * Settings (12-column grid): a sticky section index (3 columns) beside the settings cards
 * (9 columns): profile and targets, AI setup, online research, appearance, units, your data,
 * start fresh, shortcuts and about.
 */
import type { EraseResult, Settings } from "@ascend/shared";
import { useState, type CSSProperties } from "react";

import { api } from "../api/client";
import { AiSetupPanel } from "../components/AiSetupPanel";
import { BackupsPanel } from "../components/BackupsPanel";
import { EraseDataPanel } from "../components/EraseData";
import { IconDatabase } from "../components/Icons";
import { PageGrid } from "../components/Page";
import { Segmented } from "../components/Segmented";
import { TodaysNumbers } from "../components/TodaysNumbers";
import { TrainerPicker, TrainerPortrait, useTrainer } from "../components/Trainer";
import { LoadingLayout, SkeletonCard } from "../components/Skeleton";
import { ErrorState } from "../components/States";
import { useToast } from "../components/Toast";
import { kcal } from "../lib/format";
import { usePrefs } from "../lib/prefs";
import { play, setSoundPrefs, soundPrefs, type SoundPrefs } from "../lib/sound";
import { isOffline, useApi } from "../lib/useApi";
import { ProfileForm } from "./Onboarding";

const stagger = (i: number): CSSProperties => ({ ["--i" as string]: i }) as CSSProperties;

const SHORTCUTS: [string, string][] = [
  ["Ctrl+K", "Command bar: log a set (\"bench 80x5 @8\"), a hold, a meal or your weight, open a page, or ask your trainer"],
  ["Ctrl+1 … Ctrl+9, Ctrl+0", "Open a page, in sidebar order"],
  ["Tab / Shift+Tab", "Move between controls; the first Tab offers “Skip to content”"],
  ["Alt+← / Alt+→", "Back / forward between pages"],
  ["Enter", "Log the set or confirm the form you are in"],
  ["Esc", "Close an open detail panel"],
];

export function SettingsPage({ onToggleAi, onChanged, onOpenData, onErased }: { onToggleAi: () => void; onChanged: () => void; onOpenData: () => void; onErased?: (r: EraseResult) => void }) {
  const profile = useApi(api.profile, []);
  // Fuel uses the adaptive weekly target once tdee-v1 has set one (ADR-0018); say so here too.
  const tdee = useApi(() => api.tdee(7), [profile.data]);
  const toast = useToast();
  const { settings, update } = usePrefs();
  const trainer = useTrainer();
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
        <div className="grid grid-cols-12 gap-5">
          <SkeletonCard className="col-span-12 xl:col-span-3" lines={6} />
          <div className="col-span-12 grid gap-5 lg:grid-cols-2 xl:col-span-9">{[6, 3, 4, 2].map((n, i) => <SkeletonCard key={i} lines={n} />)}</div>
        </div>
      </LoadingLayout>
    );
  }
  if (!profile.data) return <ErrorState message={profile.error ?? "No profile"} onRetry={profile.reload} offline={isOffline(profile.status)} />;
  const p = profile.data;

  return (
    <PageGrid label="Settings">
      <SettingsNav />
      <div className="col-span-12 grid grid-cols-12 content-start gap-5 xl:col-span-9">
      <section className="card rise-in col-span-12 self-start p-5 2xl:col-span-7" style={stagger(1)} aria-labelledby="profile-title">
        <h2 id="profile-title" className="card-title mb-4">Profile & targets</h2>
        <ProfileForm initial={p} submitLabel="Save profile" onSaved={() => { toast("Profile saved", "info"); profile.reload(); onChanged(); }} />
        <p className="mt-4 text-xs text-muted">
          Current estimate: BMR {kcal(p.energy.bmr)} · TDEE {kcal(p.energy.tdee)} · target {kcal(p.energy.kcal_target)} kcal ·
          protein {p.energy.protein_target_g} g <span>({p.energy.formula_version}, estimate)</span>
          {tdee.data?.target_source === "adaptive" && (
            <> · this week's adaptive target {kcal(tdee.data.target_kcal)} kcal ({tdee.data.algo_version}, from your weigh-ins and meals; see Fuel)</>
          )}
        </p>
      </section>
      <div className="col-span-12 space-y-5 md:col-span-6 2xl:col-span-5">
        <AiSetupPanel aiEnabled={Boolean(aiEnabled)} onToggleAi={onToggleAi} onChanged={onChanged} />
        <OnlineResearch enabled={Boolean(settings.online_lookup)} onChange={(on) => save({ online_lookup: on }, on ? "Online research: on" : "Online research: off")} />
        <section className="card rise-in space-y-4 p-5" style={stagger(3)} aria-labelledby="appearance-title">
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
          <label className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-3 text-sm text-ink">
              <TrainerPortrait mood="neutral" size={40} />
              <span>
                Trainer
                <br />
                <span className="text-xs text-muted">{trainer.name} speaks your insights. Off shows the same facts in plain System style.</span>
              </span>
            </span>
            <input
              type="checkbox"
              className="h-5 w-5 shrink-0 accent-accent"
              checked={settings.trainer !== false}
              onChange={(e) => save({ trainer: e.target.checked }, e.target.checked ? "Trainer: on" : "Trainer: off (plain mode)")}
            />
          </label>
          <SoundSettings />
        </section>
      </div>
      <div className="col-span-12 space-y-5 md:col-span-6 2xl:col-span-7">
        <section className="card rise-in space-y-4 p-5" style={stagger(4)} aria-labelledby="trainer-title" id="trainer">
          <h2 id="trainer-title" className="card-title">Your trainer</h2>
          <p className="text-xs text-muted">One trainer speaks at a time. They all read the same numbers; only the voice and the portrait change.</p>
          <TrainerPicker onPicked={(t) => { toast(`${t.name} is your trainer now`, "info"); onChanged(); }} />
        </section>
        <section className="card rise-in space-y-4 p-5" style={stagger(4)} aria-labelledby="privacy-title" id="privacy">
          <h2 id="privacy-title" className="card-title">Privacy & photos</h2>
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">
              Hide calories
              <br />
              <span className="text-xs text-muted">Hides calorie numbers across the app. Targets still work underneath; protein stays visible.</span>
            </span>
            <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={Boolean(settings.hide_calories)}
              onChange={(e) => save({ hide_calories: e.target.checked }, e.target.checked ? "Calories hidden" : "Calories shown")} />
          </label>
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">
              Progress photo feedback (local AI)
              <br />
              <span className="text-xs text-muted">Off by default. Compares two of your photos with a vision model on this PC. Never estimates body fat or weight, never comments on looks. Not available under 18.</span>
            </span>
            <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={Boolean(settings.photo_feedback)} data-testid="photo-feedback-toggle"
              disabled={p.age < 18}
              onChange={(e) => save({ photo_feedback: e.target.checked }, e.target.checked ? "Photo feedback: on" : "Photo feedback: off")} />
          </label>
          {p.age < 18 && <p className="text-xs text-muted" data-testid="photo-feedback-minor">Photo feedback is off for under-18s.</p>}
        </section>
        <section className="card rise-in space-y-4 p-5" style={stagger(4)} aria-labelledby="units-title">
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
        <section className="card rise-in p-5" style={stagger(5)} aria-labelledby="data-title">
          <h2 id="data-title" className="card-title mb-2">Your data</h2>
          <p className="mb-3 text-sm text-muted">Import history from Strong or Hevy, or export everything you logged.</p>
          <button type="button" className="btn-ghost" onClick={onOpenData}><IconDatabase width={16} height={16} /> Open Import & export</button>
        </section>
        {onErased && <EraseDataPanel onErased={onErased} />}
        <section className="card rise-in p-5" style={stagger(5)} aria-labelledby="numbers-title" id="todays-numbers">
          <h2 id="numbers-title" tabIndex={-1} className="card-title mb-1 outline-none">Today&apos;s numbers</h2>
          <p className="mb-3 text-sm text-muted">Every number on Today, the engine that computed it and the data behind it. Numbers marked rough rest on too little data so far.</p>
          <NumbersToggle />
        </section>
        <BackupsPanel style={stagger(6)} />
        <section className="card rise-in p-5" style={stagger(6)} aria-labelledby="keys-title">
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
        <section className="card rise-in p-5 text-xs leading-relaxed text-muted" style={stagger(7)} aria-labelledby="about-title">
          <h2 id="about-title" className="card-title mb-2">About</h2>
          ASCEND {__APP_VERSION__} · MIT licence · © the ASCEND team.<br />
          Muscle map: ASCEND's own anatomical artwork (54 muscles and heads).<br />
          Trainer: Instructor Iskra Vey, an original character made for ASCEND (see ART_PROVENANCE.md).<br />
          Food values: approximate, IFCT 2017 / INDB-style.<br />
          TDEE (Mifflin-St Jeor), e1RM (Epley) and burn (MET) are estimates.
        </section>
      </div>
      </div>
    </PageGrid>
  );
}

const SECTIONS: [string, string][] = [
  ["profile-title", "Profile & targets"],
  ["ai-title", "AI setup"],
  ["online-title", "Online research"],
  ["appearance-title", "Appearance"],
  ["trainer-title", "Your trainer"],
  ["privacy-title", "Privacy & photos"],
  ["units-title", "Units & training"],
  ["data-title", "Your data"],
  ["erase-title-section", "Start fresh"],
  ["numbers-title", "Today's numbers"],
  ["backups-title", "Backups"],
  ["keys-title", "Keyboard shortcuts"],
  ["about-title", "About"],
];

/** The audit table loads on request, so opening Settings stays one quick request. */
function NumbersToggle() {
  const [open, setOpen] = useState(false);
  return open ? (
    <TodaysNumbers />
  ) : (
    <button type="button" className="btn-ghost" onClick={() => setOpen(true)} aria-expanded={false}>
      Show today&apos;s numbers
    </button>
  );
}

/** Section index (sticky on wide windows): jumps to a section and moves focus to its heading. */
function SettingsNav() {
  function go(id: string) {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView?.({ block: "start" });
    el.setAttribute("tabindex", "-1");
    el.focus({ preventScroll: true });
  }
  return (
    <nav className="col-span-12 xl:col-span-3" aria-label="Settings sections">
      <ul className="card rise-in flex flex-wrap gap-1 p-2 xl:sticky xl:top-0 xl:flex-col" style={stagger(0)}>
        {SECTIONS.map(([id, label]) => (
          <li key={id}>
            <button type="button" className="w-full rounded-md px-3 py-1.5 text-left text-sm text-muted hover:bg-panel-2 hover:text-ink" onClick={() => go(id)}>{label}</button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/**
 * The one feature that contacts the internet. Turning it on needs an explicit "Allow"
 * after reading what is sent; turning it off is one click. Every lookup is logged here.
 */
export function OnlineResearch({ enabled, onChange }: { enabled: boolean; onChange: (on: boolean) => void }) {
  const [asking, setAsking] = useState(false);
  return (
    <section className="card rise-in p-5" aria-labelledby="online-title">
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

/** Optional sound effects: off by default, kept in this browser profile. */
function SoundSettings() {
  const [prefs, setPrefs] = useState<SoundPrefs>(soundPrefs);
  const change = (p: SoundPrefs) => {
    setPrefs(p);
    setSoundPrefs(p);
  };
  return (
    <div className="space-y-2">
      <label className="flex items-center justify-between gap-4">
        <span className="text-sm text-ink">
          Sound effects
          <br />
          <span className="text-xs text-muted">Short tones for a logged set, a cleared quest, a level-up and a new skill. Off by default.</span>
        </span>
        <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={prefs.on} onChange={(e) => change({ ...prefs, on: e.target.checked })} />
      </label>
      <div className="flex items-center gap-3">
        <label htmlFor="sound-volume" className="text-xs text-muted">Volume</label>
        <input id="sound-volume" type="range" min={0} max={100} step={5} disabled={!prefs.on} className="flex-1 accent-accent"
          value={Math.round(prefs.volume * 100)} onChange={(e) => change({ ...prefs, volume: Number(e.target.value) / 100 })} />
        <span className="w-9 text-right text-xs tabular-nums text-muted">{Math.round(prefs.volume * 100)}%</span>
        <button type="button" className="btn-ghost px-2.5 py-1 text-xs" disabled={!prefs.on} onClick={() => play("levelup", prefs)}>Test</button>
      </div>
    </div>
  );
}
