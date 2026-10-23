import { lazy, Suspense, useCallback, useEffect, useState } from "react";

import type { ChatAction, EraseResult, Settings } from "@ascend/shared";

import { api } from "./api/client";
import { Layout, type Page } from "./components/Layout";
import { ErrorState, Loading } from "./components/States";
import { SystemEvents } from "./components/SystemEvents";
import { FirstRunCard } from "./components/FirstRun";
import { ToastProvider, useToast } from "./components/Toast";
import { TourOverlay } from "./components/Tour";
import { TrainerChat, TrainerChatButton } from "./components/TrainerChat";
import { XpStatus } from "./components/XpChip";
import { PrefsProvider, usePrefs } from "./lib/prefs";
import { isChatKey, usePageShortcuts } from "./lib/shortcuts";
import { tourFor, type Tour } from "./lib/tours";
import { trainerById } from "./lib/trainer";
import { useApi } from "./lib/useApi";
import { DashboardPage } from "./pages/Dashboard";

// The Dashboard is the first screen, so it ships in the main chunk; every other page
// (and first-run onboarding) is its own chunk, loaded from disk the first time it opens.
const DietPage = lazy(() => import("./pages/Diet").then((m) => ({ default: m.DietPage })));
const SkillsPage = lazy(() => import("./pages/Skills").then((m) => ({ default: m.SkillsPage })));
const LibraryPage = lazy(() => import("./pages/Library").then((m) => ({ default: m.LibraryPage })));
const HistoryPage = lazy(() => import("./pages/History").then((m) => ({ default: m.HistoryPage })));
const PlannerPage = lazy(() => import("./pages/Planner").then((m) => ({ default: m.PlannerPage })));
const ProfilePage = lazy(() => import("./pages/Profile").then((m) => ({ default: m.ProfilePage })));
const ProgressPage = lazy(() => import("./pages/Progress").then((m) => ({ default: m.ProgressPage })));
const Onboarding = lazy(() => import("./pages/Onboarding").then((m) => ({ default: m.Onboarding })));
const SettingsPage = lazy(() => import("./pages/Settings").then((m) => ({ default: m.SettingsPage })));
const WorkoutPage = lazy(() => import("./pages/Workout").then((m) => ({ default: m.WorkoutPage })));

const TITLES: Record<Page, string> = {
  dashboard: "Today",
  workout: "Train",
  library: "Exercises",
  skills: "Skills",
  progress: "Progress",
  diet: "Fuel",
  planner: "Planner",
  profile: "Profile",
  history: "History",
  settings: "Settings",
};

/**
 * In Electron the window opens while the sidecar is still starting (migrations
 * run first), so poll its status before the first API call. Browser dev mode
 * has no bridge and skips this.
 */
async function waitForEngine(timeoutMs = 30_000): Promise<void> {
  if (!window.ascend) return;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const status = await window.ascend.sidecarStatus();
    if (status.state === "ready") return;
    if (status.state === "failed") throw new Error(`The local engine failed to start: ${status.lastError ?? "unknown error"}`);
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error("The local engine took too long to start.");
}

export function pageFromHash(hash: string): Page {
  // "#skills/front_lever" opens the Skills page; the page reads the rest itself.
  const fromHash = hash.replace("#", "").split("/")[0];
  // v1.2: the 1.1 "Import & export" page is Settings > Data & backups now.
  if (fromHash === "data") return "settings";
  return fromHash in TITLES ? (fromHash as Page) : "dashboard";
}

const initialPage = (): Page => pageFromHash(window.location.hash);

export default function App() {
  const [page, setPage] = useState<Page>(initialPage);
  const [hasProfile, setHasProfile] = useState<boolean | null>(null);
  const [freshStart, setFreshStart] = useState(false);
  const [bootError, setBootError] = useState<string | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const bump = useCallback(() => setRefreshKey((k) => k + 1), []);

  const boot = useCallback(() => {
    setBootError(null);
    waitForEngine()
      .then(() => Promise.all([api.dashboard(), api.settings()]))
      .then(([d, s]) => {
        setHasProfile(d.has_profile);
        setSettings(s);
      })
      .catch((e: Error) => setBootError(e.message));
  }, []);

  useEffect(boot, [boot]);

  // Follow the hash, so Back/Forward (mouse buttons, Alt+Left/Right) and #links switch pages too.
  useEffect(() => {
    const onHash = () => setPage(pageFromHash(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = useCallback((p: Page) => {
    window.location.hash = p;
    setPage(p);
  }, []);

  if (bootError) return <ErrorState message={bootError} onRetry={boot} />;
  if (hasProfile === null || settings === null) return <Loading label="Starting the local engine…" />;

  return (
    <PrefsProvider initial={settings}>
      <ToastProvider>
        {!hasProfile ? (
          <Suspense fallback={<Loading label="Loading…" />}>
            <Onboarding onDone={() => { setFreshStart(true); setHasProfile(true); bump(); }} />
          </Suspense>
        ) : (
          <Shell page={page} navigate={navigate} refreshKey={refreshKey} bump={bump} freshStart={freshStart}
            onErased={() => { setFreshStart(false); setHasProfile(false); bump(); }} />
        )}
      </ToastProvider>
    </PrefsProvider>
  );
}

function Shell({ page, navigate, refreshKey, bump, onErased, freshStart = false }: {
  page: Page; navigate: (p: Page) => void; refreshKey: number; bump: () => void; onErased: () => void;
  /** Onboarding just finished: go straight into the app tour (one first-run flow, no second welcome). */
  freshStart?: boolean;
}) {
  const { settings, update } = usePrefs();
  const toast = useToast();
  // Trainer: chat drawer, guided tours, the one-time 1.1 welcome and the watcher's unread count.
  const [chatOpen, setChatOpen] = useState(false);
  const [tour, setTour] = useState<Tour | null>(null);
  const trainerState = useApi(api.trainerState, [refreshKey]);
  const feed = useApi(api.trainerFeed, [refreshKey, chatOpen]);
  const [welcomeDone, setWelcomeDone] = useState(freshStart);
  const markOnboarded = () => {
    setWelcomeDone(true);
    void api.updateTrainerState({ onboarded: true }).catch(() => undefined);
  };
  const startTour = useCallback((target: string | null) => {
    const t = tourFor(target);
    if (!t) return;
    setChatOpen(false);
    if (t.page) navigate(t.page);
    // Let the page render its elements before the spotlight measures them.
    window.setTimeout(() => setTour(t), 60);
  }, [navigate]);
  // One first-run flow: onboarding (profile, baseline, trainer) then the 5-step app tour.
  useEffect(() => {
    if (!freshStart) return;
    void api.updateTrainerState({ onboarded: true }).catch(() => undefined);
    // Start after this render settles (the tour opens the Today page first).
    const id = window.setTimeout(() => startTour("app"), 0);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const onChatAction = (a: ChatAction) => {
    if (a.kind === "navigate" && a.target && a.target in TITLES) {
      navigate(a.target as Page);
    } else if (a.kind === "tour") {
      startTour(a.target);
    } else if (a.kind === "planner") {
      setChatOpen(false);
      navigate("planner");
    } else if (a.kind === "trainer_picker") {
      setChatOpen(false);
      navigate("settings");
      window.setTimeout(() => document.getElementById("trainer")?.scrollIntoView?.({ block: "start" }), 80);
    }
  };
  const erased = (r: EraseResult) => {
    toast(r.safety_backup ? "Your data was erased. A backup was saved first." : "Your data was erased.", "info");
    onErased();
  };
  usePageShortcuts(navigate);
  // v1.2: one box. Ctrl+K (Cmd+K on a Mac) opens the trainer chat from anywhere; it answers
  // questions, opens pages and logs plain lines ("10 pushups", "2 idli for breakfast").
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!isChatKey(e)) return;
      e.preventDefault();
      setChatOpen((o) => !o);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const toggleAi = async () => {
    await update({ ai_enabled: !settings.ai_enabled });
    bump();
  };
  // Level, rank, streak and quest state: the top bar and the System notices share one fetch.
  const game = useApi(api.game, [refreshKey]);
  return (
    <Layout page={page} onNavigate={navigate} title={TITLES[page]}
      onlineResearch={Boolean(settings.online_lookup)} status={<XpStatus game={game.data ?? undefined} />}

      trainer={<TrainerChatButton icon={trainerById(settings.trainer_id).icon} name={trainerById(settings.trainer_id).name} unread={chatOpen ? 0 : feed.data?.unread ?? 0} onOpen={() => setChatOpen((o) => !o)} />}>
      <TrainerChat open={chatOpen} onClose={() => setChatOpen(false)} onAction={onChatAction}
        supports={["navigate", "tour", "trainer_picker", "planner"]} onActionDone={bump} />
      {tour && <TourOverlay tour={tour} onDone={() => { void api.updateTrainerState({ tour_done: tour.id }).catch(() => undefined); setTour(null); }} />}
      {trainerState.data && !trainerState.data.onboarded && !welcomeDone && !tour && (
        <FirstRunCard state={trainerState.data} onDone={markOnboarded} onTour={() => { markOnboarded(); startTour("app"); }} onErased={erased} />
      )}
      <SystemEvents game={game.data ?? undefined} notices={api.notices} />
      {/* Keyed by page so each switch replays the short fade/rise (page-enter, opacity + transform). */}
      <div key={page} className="page-enter">
      <Suspense fallback={<Loading label={`Loading ${TITLES[page]}…`} />}>
      {page === "dashboard" && <DashboardPage refreshKey={refreshKey} onChanged={bump} onNavigate={navigate} onOpenChat={() => setChatOpen(true)} />}
      {page === "workout" && <WorkoutPage onChanged={bump} />}
      {page === "library" && <LibraryPage onNavigate={navigate} refreshKey={refreshKey} />}
      {page === "skills" && <SkillsPage onNavigate={navigate} onChanged={bump} />}
      {page === "progress" && <ProgressPage refreshKey={refreshKey} onChanged={bump} />}
      {page === "diet" && <DietPage onChanged={bump} />}
      {page === "planner" && <PlannerPage onChanged={bump} />}
      {page === "profile" && <ProfilePage refreshKey={refreshKey} />}
      {page === "history" && <HistoryPage refreshKey={refreshKey} onNavigate={navigate} />}
      {page === "settings" && <SettingsPage onToggleAi={toggleAi} onChanged={bump} onOpenHistory={() => navigate("history")} onErased={erased} />}
      </Suspense>
      </div>
    </Layout>
  );
}
