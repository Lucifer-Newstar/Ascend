import type { ReactNode } from "react";

import { IconBowl, IconChat, IconDashboard, IconDumbbell, IconHistory, IconSettings } from "./Icons";

export type Page = "dashboard" | "workout" | "diet" | "coach" | "history" | "settings";

const NAV: { id: Page; label: string; icon: (p: { width?: number }) => JSX.Element }[] = [
  { id: "dashboard", label: "Dashboard", icon: IconDashboard },
  { id: "workout", label: "Workout", icon: IconDumbbell },
  { id: "diet", label: "Diet", icon: IconBowl },
  { id: "coach", label: "Coach", icon: IconChat },
  { id: "history", label: "History", icon: IconHistory },
  { id: "settings", label: "Settings", icon: IconSettings },
];

export function Layout({ page, onNavigate, aiEnabled, onToggleAi, children, title, subtitle }: {
  page: Page;
  onNavigate: (p: Page) => void;
  aiEnabled: boolean | null;
  onToggleAi: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  const today = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
  return (
    <div className="flex h-full">
      <aside className="flex w-[216px] shrink-0 flex-col border-r border-line bg-[#0c111a]">
        <div className="flex items-center gap-2.5 px-5 pb-6 pt-6">
          <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden>
            <path d="M16 3 29 28H3L16 3Z" fill="none" stroke="var(--color-accent)" strokeWidth="2.4" strokeLinejoin="round" />
            <path d="M16 13 22 25H10l6-12Z" fill="var(--color-accent)" opacity=".35" />
          </svg>
          <span className="font-display text-xl font-bold tracking-[0.2em] text-ink">ASCEND</span>
        </div>
        <nav className="flex-1 space-y-0.5 px-3" aria-label="Main">
          {NAV.map(({ id, label, icon: Icon }) => {
            const active = page === id;
            return (
              <button key={id} type="button" onClick={() => onNavigate(id)} aria-current={active ? "page" : undefined}
                className={`relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${active ? "bg-accent/10 text-accent" : "text-muted hover:bg-panel-2 hover:text-ink"}`}>
                {active && <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r bg-accent" />}
                <Icon width={18} />
                {label}
              </button>
            );
          })}
        </nav>
        <div className="px-5 py-5 text-[11px] leading-relaxed text-faint">
          Offline · data stays on this PC
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[68px] shrink-0 items-center justify-between border-b border-line px-8">
          <div>
            <h1 className="text-lg font-semibold text-ink">{title}</h1>
            <p className="text-xs text-muted">{subtitle ?? today}</p>
          </div>
          <button type="button" onClick={onToggleAi} disabled={aiEnabled === null} role="switch" aria-checked={Boolean(aiEnabled)}
            className="flex items-center gap-2.5 rounded-full border border-line-2 py-1.5 pl-3 pr-1.5 text-xs text-muted hover:border-accent/50"
            title="When off, the coach uses rule-based tips only. Everything else works the same.">
            AI coach
            <span className={`flex h-5 w-9 items-center rounded-full p-0.5 transition-colors ${aiEnabled ? "bg-accent" : "bg-line-2"}`}>
              <span className={`h-4 w-4 rounded-full bg-white transition-transform ${aiEnabled ? "translate-x-4" : ""}`} />
            </span>
          </button>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto px-8 py-6">{children}</main>
      </div>
    </div>
  );
}
