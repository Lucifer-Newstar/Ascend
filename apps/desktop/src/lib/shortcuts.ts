import { useEffect } from "react";

import type { Page } from "../components/Layout";

/** Ctrl+1 … Ctrl+9, then Ctrl+0, open the pages in sidebar order (like browser tabs). */
export const PAGE_KEYS: Page[] = ["dashboard", "workout", "library", "skills", "progress", "diet", "planner", "profile", "history", "settings"];

export function pageForKey(e: Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "altKey" | "shiftKey">): Page | null {
  if (!(e.ctrlKey || e.metaKey) || e.altKey || e.shiftKey) return null;
  if (!/^[0-9]$/.test(e.key)) return null;
  const index = e.key === "0" ? 9 : Number(e.key) - 1;
  return PAGE_KEYS[index] ?? null;
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
