import { useEffect } from "react";

import type { Page } from "../components/Layout";

/** Ctrl+1 … Ctrl+9 open the pages in sidebar order (the same keys browsers use for tabs). */
export const PAGE_KEYS: Page[] = ["dashboard", "workout", "library", "progress", "diet", "coach", "history", "data", "settings"];

export function pageForKey(e: Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "altKey" | "shiftKey">): Page | null {
  if (!(e.ctrlKey || e.metaKey) || e.altKey || e.shiftKey) return null;
  const n = Number(e.key);
  if (!Number.isInteger(n) || n < 1 || n > PAGE_KEYS.length) return null;
  return PAGE_KEYS[n - 1];
}

export function usePageShortcuts(navigate: (p: Page) => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const page = pageForKey(e);
      if (!page) return;
      e.preventDefault();
      navigate(page);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);
}
