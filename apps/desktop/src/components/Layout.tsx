import { useEffect, useRef, type ReactNode } from "react";

import { IconBowl, IconChart, IconChat, IconDashboard, IconDatabase, IconDumbbell, IconHistory, IconLibrary, IconSettings, IconSkill } from "./Icons";

export type Page = "dashboard" | "workout" | "library" | "skills" | "progress" | "diet" | "coach" | "history" | "data" | "settings";

const NAV: { id: Page; label: string; icon: (p: { width?: number }) => JSX.Element }[] = [
  { id: "dashboard", label: "Dashboard", icon: IconDashboard },
  { id: "workout", label: "Training", icon: IconDumbbell },
  { id: "library", label: "Exercises", icon: IconLibrary },
  { id: "skills", label: "Skills", icon: IconSkill },
  { id: "progress", label: "Progress", icon: IconChart },
  { id: "diet", label: "Diet", icon: IconBowl },
  { id: "coach", label: "Coach", icon: IconChat },
  { id: "history", label: "History", icon: IconHistory },
  { id: "data", label: "Import & export", icon: IconDatabase },
  { id: "settings", label: "Settings", icon: IconSettings },
];

export function Layout({ page, onNavigate, aiEnabled, onToggleAi, children, title, subtitle, status, onlineResearch = false }: {
  page: Page;
  onNavigate: (p: Page) => void;
  aiEnabled: boolean | null;
  onToggleAi: () => void;
  title: string;
  subtitle?: string;
  /** Shown in the header beside the AI switch (the level/XP chip). */
  status?: ReactNode;
  /** Settings -> Online research is on: the app may contact wger.de and Wikipedia. */
  onlineResearch?: boolean;
  children: ReactNode;
}) {
  const today = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
  const heading = useRef<HTMLHeadingElement>(null);
  const main = useRef<HTMLElement>(null);
  const shownPage = useRef(page);

  // A page change moves focus to the new page's heading (screen readers announce it,
  // keyboard users continue from the top) and updates the window title. Comparing with
  // the page last shown (not a first-render flag) keeps the first load unfocused even
  // when React runs effects twice (StrictMode in development).
  useEffect(() => {
    document.title = `${title} · ASCEND`;
    if (shownPage.current === page) return;
    shownPage.current = page;
    heading.current?.focus();
    // The scroll container is shared by every page: start the new page at its top
    // instead of the previous page's scroll offset.
    if (main.current) main.current.scrollTop = 0;
  }, [page, title]);

  return (
    <div className="flex h-full">
      <a href="#main" className="skip-link" onClick={(e) => { e.preventDefault(); heading.current?.focus(); }}>
        Skip to content
      </a>
      <aside className="flex w-[216px] shrink-0 flex-col border-r border-line bg-sidebar">
        <div className="flex items-center gap-2.5 px-5 pb-6 pt-6">
          <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden>
            <path d="M16 3 29 28H3L16 3Z" fill="none" stroke="var(--color-accent)" strokeWidth="2.4" strokeLinejoin="round" />
            <path d="M16 13 22 25H10l6-12Z" fill="var(--color-accent)" opacity=".35" />
          </svg>
          <span className="font-display text-xl font-bold tracking-[0.2em] text-ink">ASCEND</span>
        </div>
        <nav className="flex-1 space-y-0.5 px-3" aria-label="Main">
          {NAV.map(({ id, label, icon: Icon }, i) => {
            const active = page === id;
            return (
              <button key={id} type="button" onClick={() => onNavigate(id)} aria-current={active ? "page" : undefined}
                title={`${label} (Ctrl+${i + 1})`} aria-keyshortcuts={`Control+${i + 1}`}
                className={`relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${active ? "bg-accent/10 text-accent" : "text-muted hover:bg-panel-2 hover:text-ink"}`}>
                {active && <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r bg-accent" />}
                <Icon width={18} />
                {label}
              </button>
            );
          })}
        </nav>
        <div className="px-5 py-5 text-[11px] leading-relaxed text-faint">
          {onlineResearch ? "Online research on · only exercise names leave this PC" : "Offline · data stays on this PC"}
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[68px] shrink-0 items-center justify-between border-b border-line px-8">
          <div>
            <h1 ref={heading} tabIndex={-1} className="text-lg font-semibold text-ink outline-none">{title}</h1>
            <p className="text-xs text-muted">{subtitle ?? today}</p>
          </div>
          <div className="flex items-center gap-3">
          {onlineResearch && (
            <button type="button" onClick={() => onNavigate("settings")}
              className="flex items-center gap-2 rounded-full border border-warn/60 px-3 py-1.5 text-xs text-warn hover:bg-warn/10"
              title="Exercise names you add may be looked up on wger.de and Wikipedia. Click to change in Settings.">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <circle cx="12" cy="12" r="9" />
                <path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3Z" />
              </svg>
              Online research on
            </button>
          )}
          {status}
          <button type="button" onClick={onToggleAi} disabled={aiEnabled === null} role="switch" aria-checked={Boolean(aiEnabled)}
            className="flex items-center gap-2.5 rounded-full border border-line-2 py-1.5 pl-3 pr-1.5 text-xs text-muted hover:border-accent/50"
            title="When off, the coach uses rule-based tips only. Everything else works the same.">
            AI coach
            <span className={`flex h-5 w-9 items-center rounded-full p-0.5 transition-colors ${aiEnabled ? "bg-accent" : "bg-line-2"}`}>
              <span className={`h-4 w-4 rounded-full bg-white transition-transform ${aiEnabled ? "translate-x-4" : ""}`} />
            </span>
          </button>
          </div>
        </header>
        {/* tabIndex 0: a page with no controls (e.g. a long History) must still scroll from the keyboard. */}
        <main ref={main} id="main" tabIndex={0} className="min-h-0 flex-1 overflow-y-auto px-8 py-6 outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent">{children}</main>
      </div>
    </div>
  );
}
