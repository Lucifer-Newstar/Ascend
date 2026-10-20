import { useCallback, useEffect, useState } from "react";

import type { Settings } from "@ascend/shared";

import { api } from "./api/client";
import { Layout, type Page } from "./components/Layout";
import { ErrorState, Loading } from "./components/States";
import { ToastProvider } from "./components/Toast";
import { PrefsProvider, usePrefs } from "./lib/prefs";
import { CoachPage } from "./pages/Coach";
import { DashboardPage } from "./pages/Dashboard";
import { DietPage } from "./pages/Diet";
import { HistoryPage } from "./pages/History";
import { Onboarding } from "./pages/Onboarding";
import { SettingsPage } from "./pages/Settings";
import { WorkoutPage } from "./pages/Workout";

const TITLES: Record<Page, string> = {
  dashboard: "Dashboard",
  workout: "Training",
  diet: "Diet",
  coach: "Coach",
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

function initialPage(): Page {
  const fromHash = window.location.hash.replace("#", "") as Page;
  return fromHash in TITLES ? fromHash : "dashboard";
}

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

  const navigate = (p: Page) => {
    window.location.hash = p;
    setPage(p);
  };

  if (bootError) return <ErrorState message={bootError} onRetry={boot} />;
  if (hasProfile === null || settings === null) return <Loading label="Starting the local engine…" />;

  return (
    <PrefsProvider initial={settings}>
      <ToastProvider>
        {!hasProfile ? (
          <Onboarding onDone={() => { setHasProfile(true); bump(); }} />
        ) : (
          <Shell page={page} navigate={navigate} refreshKey={refreshKey} bump={bump} />
        )}
      </ToastProvider>
    </PrefsProvider>
  );
}

function Shell({ page, navigate, refreshKey, bump }: { page: Page; navigate: (p: Page) => void; refreshKey: number; bump: () => void }) {
  const { settings, update } = usePrefs();
  const toggleAi = async () => {
    await update({ ai_enabled: !settings.ai_enabled });
    bump();
  };
  const aiEnabled = settings.ai_enabled;
  return (
    <Layout page={page} onNavigate={navigate} aiEnabled={aiEnabled} onToggleAi={toggleAi} title={TITLES[page]}>
      {page === "dashboard" && <DashboardPage refreshKey={refreshKey} onOpenCoach={() => navigate("coach")} />}
      {page === "workout" && <WorkoutPage onChanged={bump} />}
      {page === "diet" && <DietPage onChanged={bump} />}
      {page === "coach" && <CoachPage aiEnabled={aiEnabled} refreshKey={refreshKey} />}
      {page === "history" && <HistoryPage refreshKey={refreshKey} />}
      {page === "settings" && <SettingsPage onToggleAi={toggleAi} onChanged={bump} />}
    </Layout>
  );
}
