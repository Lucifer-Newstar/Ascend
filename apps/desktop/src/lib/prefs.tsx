/**
 * User preferences (theme, units, AI, sessions per week, reduce motion) loaded once at boot
 * and shared through context. Changes are saved to the sidecar first, then
 * applied, so the UI never shows a preference that was not stored.
 */
import type { Settings } from "@ascend/shared";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api } from "../api/client";
import { applyMotionPreference, applyTheme, resolveTheme, systemPrefersLight } from "./theme";

interface PrefsValue {
  settings: Settings;
  update: (patch: Partial<Settings>) => Promise<Settings>;
}

const PrefsContext = createContext<PrefsValue | null>(null);

export const DEFAULT_SETTINGS: Settings = { ai_enabled: true, units: "metric", theme: "dark", sessions_per_week: 3, reduce_motion: false, online_lookup: false, trainer: true };

export function PrefsProvider({
  initial,
  children,
  save = api.updateSettings,
}: {
  initial: Settings;
  children: ReactNode;
  save?: (patch: Partial<Settings>) => Promise<Settings>;
}) {
  const [settings, setSettings] = useState<Settings>(initial);

  const update = useCallback(
    async (patch: Partial<Settings>) => {
      const next = await save(patch);
      setSettings(next);
      return next;
    },
    [save],
  );

  // Apply the theme now and whenever the OS switches while "system" is chosen.
  useEffect(() => {
    applyTheme(resolveTheme(settings.theme, systemPrefersLight()));
    if (settings.theme !== "system" || typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    const onChange = () => applyTheme(resolveTheme("system", mq.matches));
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [settings.theme]);

  useEffect(() => applyMotionPreference(Boolean(settings.reduce_motion)), [settings.reduce_motion]);

  const value = useMemo(() => ({ settings, update }), [settings, update]);
  return <PrefsContext.Provider value={value}>{children}</PrefsContext.Provider>;
}

/** The resolved theme ("dark" | "light"), for components that need literal colours. */
export function usePrefsTheme(): "dark" | "light" {
  const prefs = useContext(PrefsContext);
  return resolveTheme(prefs?.settings.theme ?? "dark", systemPrefersLight());
}

/** Prefs when inside <PrefsProvider>, else null (for components that also render standalone). */
export function useOptionalPrefs(): PrefsValue | null {
  return useContext(PrefsContext);
}

export function usePrefs(): PrefsValue {
  const ctx = useContext(PrefsContext);
  if (!ctx) throw new Error("usePrefs must be used inside <PrefsProvider>");
  return ctx;
}
