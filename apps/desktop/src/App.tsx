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
    api.dashboard()
      .then((d) => setHasProfile(d.has_profile))
      .catch((e: Error) => setBootError(e.message));
    api.settings().then((s) => setAiEnabled(s.ai_enabled)).catch(() => setAiEnabled(null));
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
