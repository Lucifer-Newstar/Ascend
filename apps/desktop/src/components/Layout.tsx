import { useEffect, useRef, type JSX, type ReactNode } from "react";

import { IconBowl, IconChart, IconChat, IconDashboard, IconDumbbell, IconHistory, IconLibrary, IconPlanner, IconProfile, IconSettings, IconSkill } from "./Icons";
import { PAGE_KEYS } from "../lib/shortcuts";
import { ThemeAmbience } from "./ThemeAmbience";
import { TrainerToggle } from "./Trainer";

export type Page = "dashboard" | "chat" | "workout" | "library" | "skills" | "progress" | "diet" | "planner" | "profile" | "history" | "settings";

const NAV: { id: Page; label: string; icon: (p: { width?: number }) => JSX.Element }[] = [
  { id: "dashboard", label: "Today", icon: IconDashboard },
  { id: "chat", label: "Chat", icon: IconChat },
  { id: "workout", label: "Train", icon: IconDumbbell },
  { id: "library", label: "Exercises", icon: IconLibrary },
  { id: "skills", label: "Skills", icon: IconSkill },
  { id: "progress", label: "Progress", icon: IconChart },
  { id: "diet", label: "Fuel", icon: IconBowl },
  { id: "planner", label: "Planner", icon: IconPlanner },
  { id: "profile", label: "Profile", icon: IconProfile },
  { id: "history", label: "History", icon: IconHistory },
  { id: "settings", label: "Settings", icon: IconSettings },
];

/** Nav groups: a thin divider after these items (order and Ctrl+1…0 stay as before). */
const GROUP_ENDS = new Set<Page>(["skills", "planner", "history"]);

export function Layout({ page, onNavigate, children, title, subtitle, status, onlineResearch = false, trainer }: {
  page: Page;
  onNavigate: (p: Page) => void;
  title: string;
  subtitle?: string;
  /** Shown in the header (the level/XP chip). */
  status?: ReactNode;
  /** Settings -> Online research is on: the app may contact wger.de and Wikipedia. */
  onlineResearch?: boolean;
  /** The trainer chat opener (defaults to the trainer voice switch). */
  trainer?: ReactNode;
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
      <aside className="flex w-[232px] shrink-0 flex-col border-r border-line bg-sidebar">
        <div className="flex items-center gap-2.5 px-5 pb-6 pt-6">
          <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden>
            <path d="M16 3 29 28H3L16 3Z" fill="none" stroke="var(--color-accent)" strokeWidth="2.4" strokeLinejoin="round" />
            <path d="M16 13 22 25H10l6-12Z" fill="var(--color-accent)" opacity=".35" />
          </svg>
          <span className="font-display text-xl font-bold tracking-[0.2em] text-ink">ASCEND</span>
        </div>
        <nav className="flex-1 px-3" aria-label="Main">
          <ul className="space-y-0.5">
          {NAV.map(({ id, label, icon: Icon }) => {
            const active = page === id;
            // Ctrl+1…0 follow PAGE_KEYS (Profile has no shortcut, so the others keep theirs).
            const at = PAGE_KEYS.indexOf(id);
            const key = at < 0 ? null : at === 9 ? 0 : at + 1;
            return (
              <li key={id} className={GROUP_ENDS.has(id) ? "mb-2 border-b border-line pb-2" : undefined}>
              <button type="button" onClick={() => onNavigate(id)} aria-current={active ? "page" : undefined} data-tour={`nav-${id}`}
                title={key === null ? label : `${label} (Ctrl+${key})`} aria-keyshortcuts={key === null ? undefined : `Control+${key}`}
                className={`group relative flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors duration-150 ${active ? "bg-accent/10 font-medium text-accent" : "text-muted hover:bg-panel-2 hover:text-ink"}`}>
                {active && <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r bg-accent" />}
                <Icon width={18} />
                <span className="flex-1 truncate text-left">{label}</span>
                <kbd aria-hidden="true" className={`font-sans text-[10px] ${active ? "text-accent" : "text-faint opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"}`}>{key === null ? "" : `Ctrl ${key}`}</kbd>
              </button>
              </li>
            );
          })}
          </ul>
        </nav>
        <div className="px-5 py-5 text-[11px] leading-relaxed text-faint">
          {onlineResearch ? "Online research on · only exercise names leave this PC" : "Offline · data stays on this PC"}
        </div>
      </aside>
      <div className="relative flex min-w-0 flex-1 flex-col">
        <ThemeAmbience />
        <header className="relative z-[1] flex h-[76px] shrink-0 items-center justify-between gap-4 border-b border-line px-8">
          <div className="min-w-0">
            <h1 ref={heading} tabIndex={-1} className="text-display-l truncate text-ink outline-none">{title}</h1>
            <p className="text-small text-muted">{subtitle ?? today}</p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
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
          {status && <span data-tour="xp">{status}</span>}
          {trainer ?? <TrainerToggle />}
          </div>
        </header>
        {/* tabIndex 0: a page with no controls (e.g. a long History) must still scroll from the keyboard. */}
        <main ref={main} id="main" data-tour="main" tabIndex={0} className="relative z-[1] min-h-0 flex-1 overflow-y-auto px-8 py-6 outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent">{children}</main>
      </div>
    </div>
  );
}
