/**
 * Settings (v1.2): six sections, one at a time, chosen from the index on the left:
 * Profile, Trainer, Appearance & sound, Units, Data & backups and Advanced. The 1.1
 * "Import & export" page lives in Data & backups now; Today's numbers and online
 * research moved to Advanced. "#settings/data" opens a section directly.
 */
import type { EraseResult, Settings } from "@ascend/shared";
import { useEffect, useState, type CSSProperties } from "react";

import { api } from "../api/client";
import { AiSetupPanel } from "../components/AiSetupPanel";
import { BackupsPanel } from "../components/BackupsPanel";
import { EraseDataPanel } from "../components/EraseData";
import { PageGrid } from "../components/Page";
import { PhotoSafety } from "../components/PhotoSafety";
import { ScheduleEditor } from "../components/ScheduleEditor";
import { Segmented } from "../components/Segmented";
import { ThemePicker } from "../components/ThemePicker";
import { TodaysNumbers } from "../components/TodaysNumbers";
import { TrainerPicker, TrainerPortrait, useTrainer } from "../components/Trainer";
import { LoadingLayout, SkeletonCard } from "../components/Skeleton";
import { ErrorState } from "../components/States";
import { useToast } from "../components/Toast";
import { kcal } from "../lib/format";
import { usePrefs } from "../lib/prefs";
import { play, setSoundPrefs, soundPrefs, type SoundPrefs } from "../lib/sound";
import { isOffline, useApi } from "../lib/useApi";
import { DataPage } from "./Data";
import { ProfileForm } from "./Onboarding";

const stagger = (i: number): CSSProperties => ({ ["--i" as string]: i }) as CSSProperties;

export type SettingsSection = "profile" | "trainer" | "appearance" | "units" | "data" | "advanced";

export const SECTIONS: [SettingsSection, string][] = [
  ["profile", "Profile"],
  ["trainer", "Trainer"],
  ["appearance", "Appearance & sound"],
  ["units", "Units"],
  ["data", "Data & backups"],
  ["advanced", "Advanced"],
];

const SHORTCUTS: [string, string][] = [
  ["Ctrl+K", "Open the trainer chat: ask anything or log a set (\"10 pushups\"), a meal or your weight"],
  ["Ctrl+1 … Ctrl+9, Ctrl+0", "Open a page, in sidebar order"],
  ["Tab / Shift+Tab", "Move between controls; the first Tab offers “Skip to content”"],
  ["Alt+← / Alt+→", "Back / forward between pages"],
  ["Enter", "Log the set or confirm the form you are in"],
  ["Esc", "Close an open panel or the full-screen timer"],
];

export function sectionFromHash(hash: string): SettingsSection {
  const part = hash.replace("#", "").split("/")[1] as SettingsSection | undefined;
  return SECTIONS.some(([id]) => id === part) ? (part as SettingsSection) : "profile";
}

export function SettingsPage({ onToggleAi, onChanged, onOpenHistory, onErased }: {
  onToggleAi: () => void; onChanged: () => void; onOpenHistory?: () => void; onErased?: (r: EraseResult) => void;
}) {
  const profile = useApi(api.profile, []);
  // Fuel uses the adaptive weekly target once tdee-v1 has set one (ADR-0018); say so here too.
  const tdee = useApi(() => api.tdee(7), [profile.data]);
  const toast = useToast();
  const { settings, update } = usePrefs();
  const trainer = useTrainer();
  const aiEnabled = settings.ai_enabled;
  const [section, setSection] = useState<SettingsSection>(() => sectionFromHash(window.location.hash));
  useEffect(() => {
    const onHash = () => setSection(sectionFromHash(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const open = (s: SettingsSection) => {
    setSection(s);
    window.history.replaceState(null, "", `#settings/${s}`);
  };

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
          <div className="col-span-12 grid gap-5 xl:col-span-9">{[6, 3].map((n, i) => <SkeletonCard key={i} lines={n} />)}</div>
        </div>
      </LoadingLayout>
    );
  }
  if (!profile.data) return <ErrorState message={profile.error ?? "No profile"} onRetry={profile.reload} offline={isOffline(profile.status)} />;
  const p = profile.data;
  const title = SECTIONS.find(([id]) => id === section)?.[1] ?? "Profile";

  return (
    <PageGrid label="Settings">
      <SettingsNav current={section} onOpen={open} />
      <div className="col-span-12 space-y-5 xl:col-span-9" role="region" aria-label={title} data-testid={`settings-${section}`}>
      {section === "profile" && (
        <>
          <section className="card rise-in p-5" style={stagger(1)} aria-labelledby="profile-title">
            <h2 id="profile-title" className="card-title mb-4">Your body & goal</h2>
            <ProfileForm initial={p} submitLabel="Save profile" onSaved={() => { toast("Profile saved", "info"); profile.reload(); onChanged(); }} />
            <p className="mt-4 text-sm text-muted">
              Daily target: {kcal(p.energy.kcal_target)} kcal and {p.energy.protein_target_g} g protein (an estimate).
              {tdee.data?.target_source === "adaptive" && <> This week it follows your weigh-ins and meals: {kcal(tdee.data.target_kcal)} kcal.</>}
            </p>
            <details className="mt-2 text-xs text-muted">
              <summary className="cursor-pointer text-accent">Details</summary>
              <p className="mt-1">Resting burn (BMR) {kcal(p.energy.bmr)} kcal · daily burn (TDEE) {kcal(p.energy.tdee)} kcal, from the Mifflin-St Jeor formula and your activity level.</p>
            </details>
          </section>
          <section className="card rise-in space-y-4 p-5" style={stagger(2)} aria-labelledby="privacy-title" id="privacy">
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
                Monthly photo reminder
                <br />
                <span className="text-xs text-muted">Off by default. Once a month the trainer suggests a progress photo.</span>
              </span>
              <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={Boolean(settings.photo_reminder)} data-testid="photo-reminder-toggle"
                onChange={(e) => save({ photo_reminder: e.target.checked }, e.target.checked ? "Photo reminder: on" : "Photo reminder: off")} />
            </label>
            <PhotoSafety />
          </section>
        </>
      )}
      {section === "trainer" && (
        <>
          <section className="card rise-in space-y-4 p-5" style={stagger(1)} aria-labelledby="trainer-title" id="trainer">
            <h2 id="trainer-title" className="card-title">Your trainer</h2>
            <label className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-3 text-sm text-ink">
                <TrainerPortrait mood="neutral" size={40} />
                <span>
                  Trainer voice
                  <br />
                  <span className="text-xs text-muted">{trainer.name} speaks your insights. Off shows the same facts in plain System style.</span>
                </span>
              </span>
              <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={settings.trainer !== false}
                onChange={(e) => save({ trainer: e.target.checked }, e.target.checked ? "Trainer: on" : "Trainer: off (plain mode)")} />
            </label>
            <label className="flex items-center justify-between gap-4">
              <span className="text-sm text-ink">
                Reminders
                <br />
                <span className="text-xs text-muted">One calm nudge a day for today&apos;s workout or a missed day&apos;s reason, as a desktop notification and a bubble on Today. Never on a planned rest day, only while the app is open or in the tray.</span>
              </span>
              <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={settings.reminders !== false}
                onChange={(e) => save({ reminders: e.target.checked }, e.target.checked ? "Reminders on" : "Reminders off")} />
            </label>
            <label className="flex items-center justify-between gap-4">
              <span className="text-sm text-ink">
                Evening check
                <br />
                <span className="text-xs text-muted">Off by default. One more nudge after 6 pm if today&apos;s session is not done yet. Never more than two a day.</span>
              </span>
              <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={Boolean(settings.evening_reminder)} data-testid="evening-reminder-toggle"
                disabled={settings.reminders === false}
                onChange={(e) => save({ evening_reminder: e.target.checked }, e.target.checked ? "Evening check: on" : "Evening check: off")} />
            </label>
            <label className="flex items-center justify-between gap-4">
              <span className="text-sm text-ink">
                Weigh-in nudge
                <br />
                <span className="text-xs text-muted">Off by default. The trainer mentions it when your last weigh-in is over a week old.</span>
              </span>
              <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={Boolean(settings.weigh_in_reminder)} data-testid="weigh-in-reminder-toggle"
                onChange={(e) => save({ weigh_in_reminder: e.target.checked }, e.target.checked ? "Weigh-in nudge: on" : "Weigh-in nudge: off")} />
            </label>
            <label className="flex items-center justify-between gap-4">
              <span className="text-sm text-ink">
                Keep ASCEND in the tray
                <br />
                <span className="text-xs text-muted">Off by default. Closing the window keeps ASCEND next to the clock, so the reminders still reach you. Quit from the tray icon.</span>
              </span>
              <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={Boolean(settings.tray)} data-testid="tray-toggle"
                onChange={(e) => save({ tray: e.target.checked }, e.target.checked ? "Tray: on" : "Tray: off")} />
            </label>
            <label className="flex items-center justify-between gap-4">
              <span className="text-sm text-ink">
                Start with Windows
                <br />
                <span className="text-xs text-muted">Off by default. ASCEND opens when you sign in to Windows.</span>
              </span>
              <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={Boolean(settings.start_with_windows)} data-testid="start-with-windows-toggle"
                onChange={(e) => save({ start_with_windows: e.target.checked }, e.target.checked ? "Start with Windows: on" : "Start with Windows: off")} />
            </label>
            <label className="flex items-center justify-between gap-4">
              <span className="text-sm text-ink">
                Lock screen on launch
                <br />
                <span className="text-xs text-muted">Opens on today&apos;s session: press Enter to start it. Off goes straight to Today.</span>
              </span>
              <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={settings.lock_screen !== false} data-testid="lock-screen-toggle"
                onChange={(e) => save({ lock_screen: e.target.checked }, e.target.checked ? "Lock screen: on" : "Lock screen: off")} />
            </label>
            <label className="flex items-center justify-between gap-4">
              <span className="text-sm text-ink">
                Coaching team
                <br />
                <span className="text-xs text-muted">Your main trainer runs the chat and hands a question to the specialist for it: Idris (gym and strength), Dario (calisthenics), Kai (cardio and martial arts), Tara (mobility and recovery), Vera (nutrition). Off: your main trainer answers everything.</span>
              </span>
              <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={settings.team_handoff !== false} data-testid="team-handoff-toggle"
                onChange={(e) => save({ team_handoff: e.target.checked }, e.target.checked ? "Coaching team: on" : "Coaching team: off")} />
            </label>
            <h3 className="text-sm font-semibold text-ink" id="main-trainer-title">Main trainer</h3>
            <p className="text-xs text-muted">Your main trainer runs the chat, your reminders and your cards. Everyone reads the same numbers; only the voice and the portrait change.</p>
            <TrainerPicker label="Choose your main trainer" onPicked={(t) => { toast(`${t.name} is your main trainer now`, "info"); onChanged(); }} />
          </section>
          <section className="card rise-in space-y-4 p-5" style={stagger(2)} aria-labelledby="schedule-title" id="schedule">
            <h2 id="schedule-title" className="card-title">Your training week</h2>
            <ScheduleEditor onSaved={() => onChanged()} />
          </section>
          <AiSetupPanel aiEnabled={Boolean(aiEnabled)} onToggleAi={onToggleAi} onChanged={onChanged} />
        </>
      )}
      {section === "appearance" && (
        <section className="card rise-in space-y-5 p-5" style={stagger(1)} aria-labelledby="appearance-title">
          <h2 id="appearance-title" className="card-title">Appearance & sound</h2>
          <ThemePicker onSave={save} />
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">
              Reduce motion
              <br />
              <span className="text-xs text-muted">No particles, tilt, flips, count-ups or celebrations. Your Windows animation setting is always honoured.</span>
            </span>
            <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={Boolean(settings.reduce_motion)}
              onChange={(e) => save({ reduce_motion: e.target.checked }, e.target.checked ? "Reduce motion: on" : "Reduce motion: off")} />
          </label>
          <SoundSettings />
        </section>
      )}
      {section === "units" && (
        <section className="card rise-in space-y-4 p-5" style={stagger(1)} aria-labelledby="units-title">
          <h2 id="units-title" className="card-title">Units & training</h2>
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">Units</span>
            <Segmented label="Units" value={settings.units}
              options={[{ value: "metric", label: "kg · cm · km" }, { value: "imperial", label: "lb · in · mi" }]}
              onChange={(units) => save({ units }, units === "metric" ? "Units: metric" : "Units: imperial")} />
          </div>
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">
              Training days per week
              <br />
              <span className="text-xs text-muted">Used by the weekly review to judge how your week went.</span>
            </span>
            <select className="input w-20" value={settings.sessions_per_week}
              onChange={(e) => save({ sessions_per_week: Number(e.target.value) }, "Training days saved")}>
              {[1, 2, 3, 4, 5, 6, 7].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
        </section>
      )}
      {section === "data" && (
        <>
          <DataPage onChanged={onChanged} onOpenHistory={onOpenHistory ?? (() => { window.location.hash = "history"; })} />
          <BackupsPanel style={stagger(2)} />
          {onErased && <EraseDataPanel onErased={onErased} />}
        </>
      )}
      {section === "advanced" && (
        <>
          <section className="card rise-in p-5" style={stagger(1)} aria-labelledby="numbers-title" id="todays-numbers">
            <h2 id="numbers-title" tabIndex={-1} className="card-title mb-1 outline-none">Today&apos;s numbers</h2>
            <p className="mb-3 text-sm text-muted">Every number on Today, how it was worked out and the data behind it. Numbers marked rough rest on too little data so far.</p>
            <NumbersToggle />
          </section>
          <OnlineResearch enabled={Boolean(settings.online_lookup)} onChange={(on) => save({ online_lookup: on }, on ? "Online research: on" : "Online research: off")} />
          <section className="card rise-in p-5" style={stagger(3)} aria-labelledby="keys-title">
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
          <section className="card rise-in p-5 text-xs leading-relaxed text-muted" style={stagger(4)} aria-labelledby="about-title">
            <h2 id="about-title" className="card-title mb-2">About</h2>
            ASCEND {__APP_VERSION__} · MIT licence · © the ASCEND team.<br />
            Muscle map: ASCEND&apos;s own anatomical artwork (54 muscles and heads).<br />
            Trainers, themes and bosses: original art made for ASCEND.<br />
            Food values: approximate, from IFCT 2017 and food labels.<br />
            Calorie burn, daily targets and strength estimates are estimates.
          </section>
        </>
      )}
      </div>
    </PageGrid>
  );
}

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

/** Section index (sticky on wide windows): shows one section at a time. */
function SettingsNav({ current, onOpen }: { current: SettingsSection; onOpen: (s: SettingsSection) => void }) {
  return (
    <nav className="col-span-12 xl:col-span-3" aria-label="Settings sections">
      <ul className="card rise-in flex flex-wrap gap-1 p-2 xl:sticky xl:top-0 xl:flex-col" style={stagger(0)}>
        {SECTIONS.map(([id, label]) => (
          <li key={id}>
            <button type="button" aria-current={current === id ? "page" : undefined} onClick={() => onOpen(id)}
              className={`w-full rounded-md px-3 py-1.5 text-left text-sm ${current === id ? "bg-accent/10 font-medium text-accent" : "text-muted hover:bg-panel-2 hover:text-ink"}`}>
              {label}
            </button>
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
