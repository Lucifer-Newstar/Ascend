/**
 * Theme handling: the user's preference (dark | light | system) is stored by the
 * sidecar; this module resolves it and applies it as <html data-theme="...">,
 * which switches the CSS tokens in index.css.
 */
export type ThemePref = "dark" | "light" | "system";
export type Theme = "dark" | "light";

export function resolveTheme(pref: ThemePref, systemPrefersLight: boolean): Theme {
  if (pref === "system") return systemPrefersLight ? "light" : "dark";
  return pref;
}

export function systemPrefersLight(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: light)").matches
    : false;
}

export function applyTheme(theme: Theme, root: HTMLElement = document.documentElement): void {
  root.dataset.theme = theme;
}

/** Current value of a CSS custom property, for libraries that need literal colours. */
export function cssVar(name: string, fallback = ""): string {
  if (typeof document === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}
