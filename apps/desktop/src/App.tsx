import { useCallback, useEffect, useState } from "react";

import { api } from "./api/client";
import { Layout, type Page } from "./components/Layout";
import { ErrorState, Loading } from "./components/States";
import { ToastProvider } from "./components/Toast";
import { CoachPage } from "./pages/Coach";
import { DashboardPage } from "./pages/Dashboard";
import { DietPage } from "./pages/Diet";
import { HistoryPage } from "./pages/History";
import { Onboarding } from "./pages/Onboarding";
import { SettingsPage } from "./pages/Settings";
import { WorkoutPage } from "./pages/Workout";

const TITLES: Record<Page, string> = {
  dashboard: "Dashboard",
  workout: "Workout logger",
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
  const [aiEnabled, setAiEnabled] = useState<boolean | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const bump = useCallback(() => setRefreshKey((k) => k + 1), []);

  const boot = useCallback(() => {
    setBootError(null);
    waitForEngine()
      .then(() => Promise.all([api.dashboard(), api.settings()]))
      .then(([d, s]) => {
        setHasProfile(d.has_profile);
        setAiEnabled(s.ai_enabled);
      })
      .catch((e: Error) => setBootError(e.message));
  }, []);

  useEffect(boot, [boot]);

  const navigate = (p: Page) => {
    window.location.hash = p;
    setPage(p);
  };

  const toggleAi = async () => {
    if (aiEnabled === null) return;
    const next = await api.setAi(!aiEnabled);
    setAiEnabled(next.ai_enabled);
    bump();
  };

  if (bootError) return <ErrorState message={bootError} onRetry={boot} />;
  if (hasProfile === null) return <Loading label="Starting the local engine…" />;

  return (
    <ToastProvider>
      {!hasProfile ? (
        <Onboarding onDone={() => { setHasProfile(true); bump(); }} />
      ) : (
        <Layout page={page} onNavigate={navigate} aiEnabled={aiEnabled} onToggleAi={toggleAi} title={TITLES[page]}>
          {page === "dashboard" && <DashboardPage refreshKey={refreshKey} onOpenCoach={() => navigate("coach")} />}
          {page === "workout" && <WorkoutPage onChanged={bump} />}
          {page === "diet" && <DietPage onChanged={bump} />}
          {page === "coach" && <CoachPage aiEnabled={aiEnabled} refreshKey={refreshKey} />}
          {page === "history" && <HistoryPage refreshKey={refreshKey} />}
          {page === "settings" && <SettingsPage aiEnabled={aiEnabled} onToggleAi={toggleAi} onChanged={bump} />}
        </Layout>
      )}
    </ToastProvider>
  );
}
