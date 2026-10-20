import { lazy, Suspense, useCallback, useEffect, useState } from "react";

import type { Settings } from "@ascend/shared";

import { api } from "./api/client";
import { Layout, type Page } from "./components/Layout";
import { ErrorState, Loading } from "./components/States";
import { ToastProvider } from "./components/Toast";
import { XpChip } from "./components/XpChip";
import { PrefsProvider, usePrefs } from "./lib/prefs";
import { usePageShortcuts } from "./lib/shortcuts";
import { DashboardPage } from "./pages/Dashboard";

// The Dashboard is the first screen, so it ships in the main chunk; every other page
// (and first-run onboarding) is its own chunk, loaded from disk the first time it opens.
const CoachPage = lazy(() => import("./pages/Coach").then((m) => ({ default: m.CoachPage })));
const DataPage = lazy(() => import("./pages/Data").then((m) => ({ default: m.DataPage })));
const DietPage = lazy(() => import("./pages/Diet").then((m) => ({ default: m.DietPage })));
const LibraryPage = lazy(() => import("./pages/Library").then((m) => ({ default: m.LibraryPage })));
const HistoryPage = lazy(() => import("./pages/History").then((m) => ({ default: m.HistoryPage })));
const ProgressPage = lazy(() => import("./pages/Progress").then((m) => ({ default: m.ProgressPage })));
const Onboarding = lazy(() => import("./pages/Onboarding").then((m) => ({ default: m.Onboarding })));
const SettingsPage = lazy(() => import("./pages/Settings").then((m) => ({ default: m.SettingsPage })));
const WorkoutPage = lazy(() => import("./pages/Workout").then((m) => ({ default: m.WorkoutPage })));

const TITLES: Record<Page, string> = {
  dashboard: "Dashboard",
  workout: "Training",
  library: "Exercises",
  progress: "Progress",
  diet: "Diet",
  coach: "Coach",
  history: "History",
  data: "Import & export",
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
  const fromHash = hash.replace("#", "") as Page;
  return fromHash in TITLES ? fromHash : "dashboard";
}

const initialPage = (): Page => pageFromHash(window.location.hash);

export default function App() {
  const [page, setPage] = useState<Page>(initialPage);
  const [hasProfile, setHasProfile] = useState<boolean | null>(null);
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
            <Onboarding onDone={() => { setHasProfile(true); bump(); }} />
          </Suspense>
        ) : (
          <Shell page={page} navigate={navigate} refreshKey={refreshKey} bump={bump} />
        )}
      </ToastProvider>
    </PrefsProvider>
  );
}

function Shell({ page, navigate, refreshKey, bump }: { page: Page; navigate: (p: Page) => void; refreshKey: number; bump: () => void }) {
  const { settings, update } = usePrefs();
  usePageShortcuts(navigate);
  const toggleAi = async () => {
    await update({ ai_enabled: !settings.ai_enabled });
    bump();
  };
  const aiEnabled = settings.ai_enabled;
  return (
    <Layout page={page} onNavigate={navigate} aiEnabled={aiEnabled} onToggleAi={toggleAi} title={TITLES[page]}
      status={<XpChip refreshKey={refreshKey} />}>
      {/* Keyed by page so each switch replays the short fade/rise (page-enter, opacity + transform). */}
      <div key={page} className="page-enter">
      <Suspense fallback={<Loading label={`Loading ${TITLES[page]}…`} />}>
      {page === "dashboard" && <DashboardPage refreshKey={refreshKey} onChanged={bump} onNavigate={navigate} onOpenCoach={() => navigate("coach")} />}
      {page === "workout" && <WorkoutPage onChanged={bump} />}
      {page === "library" && <LibraryPage onNavigate={navigate} refreshKey={refreshKey} />}
      {page === "progress" && <ProgressPage refreshKey={refreshKey} onChanged={bump} />}
      {page === "diet" && <DietPage onChanged={bump} />}
      {page === "coach" && <CoachPage aiEnabled={aiEnabled} refreshKey={refreshKey} />}
      {page === "history" && <HistoryPage refreshKey={refreshKey} onNavigate={navigate} />}
      {page === "data" && <DataPage onChanged={bump} onOpenHistory={() => navigate("history")} />}
      {page === "settings" && <SettingsPage onToggleAi={toggleAi} onChanged={bump} onOpenData={() => navigate("data")} />}
      </Suspense>
      </div>
    </Layout>
  );
}
