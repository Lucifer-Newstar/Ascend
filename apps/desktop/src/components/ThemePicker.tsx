/**
 * Theme picker (v1.2, Settings > Appearance & sound): every theme as a card with its
 * landing art (the 1.1 Light and Dark looks as colour swatches). Locked themes show what
 * earns them; an unlock is kept for good. Background art can be dimmed or turned off.
 */
import type { BackgroundArt, Settings, ThemeInfo, ThemePref } from "@ascend/shared";

import { api } from "../api/client";
import { Segmented } from "./Segmented";
import { usePrefs } from "../lib/prefs";
import { themeArt } from "../lib/themeArt";
import { isAppTheme } from "../lib/theme";
import { useApi } from "../lib/useApi";

const SWATCH: Record<string, string> = {
  dark: "linear-gradient(135deg, #070b13 0 55%, #18253d 55% 100%)",
  light: "linear-gradient(135deg, #f3f6fb 0 55%, #dde6f2 55% 100%)",
};

export function ThemePicker({ onSave }: { onSave: (patch: Partial<Settings>, message: string) => void | Promise<void> }) {
  const { settings } = usePrefs();
  const themes = useApi(api.themes, []);
  const current: ThemePref = settings.theme;
  const followsSystem = current === "system";
  const chosen = (t: ThemeInfo) => current === t.key || (followsSystem && (t.key === "dark" || t.key === "light"));

  return (
    <div className="space-y-4">
      {themes.error && !themes.data && <p className="text-xs text-bad">The themes could not be loaded. {themes.error}</p>}
      <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Themes">
        {(themes.data ?? []).map((t) => {
          const art = isAppTheme(t.key) ? themeArt(t.key, "landing") : null;
          const on = chosen(t);
          return (
            <li key={t.key}>
              <button type="button" disabled={!t.unlocked} aria-pressed={on} data-testid={`theme-${t.key}`}
                onClick={() => void onSave({ theme: t.key }, `Theme: ${t.name}`)}
                className={`group w-full overflow-hidden rounded-lg border bg-panel-2 text-left transition-colors duration-150 ${on ? "border-accent ring-2 ring-accent/40" : "border-line hover:border-accent/60"} disabled:cursor-not-allowed`}>
                <span className="relative block aspect-[16/9] w-full" style={art ? { backgroundImage: `url("${art}")`, backgroundSize: "cover", backgroundPosition: "center" } : { background: SWATCH[t.key] }}>
                  {!t.unlocked && (
                    <span className="absolute inset-0 flex items-center justify-center bg-black/65 text-xs font-medium text-white">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden className="mr-1.5">
                        <rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" />
                      </svg>
                      Locked
                    </span>
                  )}
                </span>
                <span className="block p-2.5">
                  <span className="block text-sm font-semibold text-ink">{t.name}{on && <span className="ml-1.5 text-xs font-normal text-accent">· in use</span>}</span>
                  <span className="block text-xs text-muted">{t.unlocked ? t.tagline : t.requirement}</span>
                  {!t.unlocked && t.progress && <span className="block text-[11px] text-faint">{t.progress}</span>}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {(current === "dark" || current === "light" || followsSystem) && (
        <label className="flex items-center justify-between gap-4">
          <span className="text-sm text-ink">
            Follow Windows
            <br />
            <span className="text-xs text-muted">Switch between Light and Dark with your Windows setting.</span>
          </span>
          <input type="checkbox" className="h-5 w-5 shrink-0 accent-accent" checked={followsSystem}
            onChange={(e) => void onSave({ theme: e.target.checked ? "system" : "dark" }, e.target.checked ? "Theme: follows Windows" : "Theme: Dark")} />
        </label>
      )}
      {isAppTheme(current) && (
        <div className="flex items-center justify-between gap-4">
          <span className="text-sm text-ink">
            Background art
            <br />
            <span className="text-xs text-muted">The theme&apos;s picture behind the pages. Cards always stay solid.</span>
          </span>
          <Segmented<BackgroundArt>
            label="Background art"
            value={settings.background_art ?? "on"}
            options={[{ value: "on", label: "On" }, { value: "dim", label: "Dim" }, { value: "off", label: "Off" }]}
            onChange={(background_art) => void onSave({ background_art }, `Background art: ${background_art}`)}
          />
        </div>
      )}
    </div>
  );
}
