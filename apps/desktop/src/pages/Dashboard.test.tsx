import type { CoachReply, Dashboard, QuestItem, Stats, WeeklyReview } from "@ascend/shared";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { buildInsights } from "../components/Insights";
import { minutesToMidnight, QuestWindow, timeLeftLabel } from "../components/QuestWindow";
import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { clearApiCache } from "../lib/useApi";
import { axeViolations } from "../test/axe";
import { DashboardPage } from "./Dashboard";

vi.mock("../api/client", () => ({
  api: {
    dashboard: vi.fn(), stats: vi.fn(), coachTip: vi.fn(), weeklyReview: vi.fn(), completeQuest: vi.fn(),
    checkinToday: vi.fn(), checkin: vi.fn(), deload: vi.fn(), startDeload: vi.fn(), muscleActivity: vi.fn(), updateSettings: vi.fn(),
    boss: vi.fn(() => Promise.reject(new Error("not needed"))), titles: vi.fn(() => Promise.resolve([])), profile: vi.fn(() => Promise.resolve({ name: "Navin" })),
  },
}));

const item = (over: Partial<QuestItem>): QuestItem => ({
  id: 1, day: "2026-10-20", kind: "training", code: "c", title: "Pull-ups 5 × 6", detail: "", metric: "hard_sets", target: 5, progress: 3, xp: 40, completed_at: null, ...over,
});

const ring = (value: number, target: number) => ({ value, target, label: "", is_estimate: false });
const dashboard: Dashboard = {
  date: "2026-10-20",
  has_profile: true,
  rings: { tasks: ring(1, 3), kcal_in: ring(1200, 2600), kcal_out: ring(100, 350) },
  nutrition: { kcal: 1200, protein_g: 60, carbs_g: 150, fat_g: 40 },
  game: {
    xp: { total: 900, today: 30, level: 7, xp_into_level: 300, xp_for_next: 1000, rank: "D", rank_title: "Initiate", daily_cap: 600, formula_version: "xp-v1" },
    streak: { current: 4, best: 9, freezes_held: 1, freezes_used: 0, active_today: true },
    calm: { current: 0, best: 0, active_today: false },
    quest: [item({}), item({ id: 2, kind: "recovery", title: "Take a 10-minute walk", detail: "Easy pace", metric: "manual", target: 1, progress: 0, xp: 15 })],
  },
  muscles: [],
} as unknown as Dashboard;

const stats: Stats = {
  version: "stats-v1",
  window_days: 28,
  stats: [
    { key: "str", label: "Strength", value: 41, formula: "Better of: strength skill-tree steps unlocked, or best e1RM ÷ body weight (2.0× = 100)", inputs: { best_e1rm_kg_90d: 100, bodyweight_kg: 70, relative_e1rm: 1.43 } },
    { key: "agi", label: "Agility", value: 33, formula: "Skill-tree steps unlocked", inputs: { skill_steps_unlocked: 4, skill_steps_total: 12 } },
    { key: "end", label: "Endurance", value: 27, formula: "Cardio minutes", inputs: { cardio_minutes: 162 } },
    { key: "vit", label: "Vitality", value: 58, formula: "Check-ins", inputs: { checkin_days: 14 } },
    { key: "int", label: "Discipline", value: 64, formula: "Meals and quests", inputs: { meal_days: 20 } },
  ],
};

const tip: CoachReply = { source: "rules", text: "Train legs today.", tip_code: "under_quads", model: null, fallback_reason: "ai_disabled" };

function renderPage(onNavigate = vi.fn()) {
  return render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, reduce_motion: true }} save={vi.fn()}>
      <ToastProvider>
        <DashboardPage refreshKey={0} onOpenChat={vi.fn()} onNavigate={onNavigate} />
      </ToastProvider>
    </PrefsProvider>,
  );
}

describe("Today (Hunter HQ)", () => {
  beforeEach(() => {
    clearApiCache();
    vi.mocked(api.dashboard).mockResolvedValue(dashboard);
    vi.mocked(api.stats).mockResolvedValue(stats);
    vi.mocked(api.coachTip).mockResolvedValue(tip);
    vi.mocked(api.weeklyReview).mockRejectedValue(new Error("none"));
    vi.mocked(api.checkinToday).mockResolvedValue(null);
    vi.mocked(api.deload).mockResolvedValue({ recommended: false, kind: "none", training_weeks: 1, signals: [], guidance: null, deload_week: null, algo_version: "d" });
    vi.mocked(api.muscleActivity).mockResolvedValue([]);
  });

  it("leads with the Daily Quest window and the Status panel, and starts the session", async () => {
    const nav = vi.fn();
    const { container } = renderPage(nav);
    const quest = await screen.findByRole("region", { name: "Daily quest" });
    expect(quest).toHaveTextContent(/Time left \d+ h \d+ m|Time left \d+ m/);
    expect(quest).toHaveTextContent("0/2 complete · Reward 55 XP");
    // Training tasks tick themselves; only the manual walk has a box to tick.
    expect(within(quest).getByRole("button", { name: "Pull-ups 5 × 6: completes automatically" })).toBeDisabled();
    expect(within(quest).getByRole("button", { name: 'Mark "Take a 10-minute walk" done' })).toBeEnabled();
    await userEvent.click(within(quest).getByRole("button", { name: "Start today's session" }));
    expect(nav).toHaveBeenCalledWith("workout");
    const status = screen.getByTestId("status-panel");
    expect(within(status).getByRole("img", { name: "Rank D, Initiate" })).toBeInTheDocument();
    expect(within(status).getAllByRole("button", { name: /^Why is/ })).toHaveLength(5);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("explains every stat with its formula and inputs", async () => {
    renderPage();
    const why = await screen.findByRole("button", { name: "Why is Strength 41?" });
    await userEvent.click(why);
    expect(why).toHaveAttribute("aria-expanded", "true");
    const panel = document.getElementById(why.getAttribute("aria-controls")!)!;
    expect(panel).toHaveTextContent("Strength: Better of: strength skill-tree steps unlocked");
    expect(panel).toHaveTextContent("Body weight (kg)70");
  });

  it("shows the morning check-in after the quest and status, not first", async () => {
    renderPage();
    const quest = await screen.findByRole("region", { name: "Daily quest" });
    const checkin = await screen.findByRole("form", { name: "Morning check-in" });
    expect(quest.compareDocumentPosition(checkin) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});

describe("Quest window helpers", () => {
  it("counts down to local midnight", () => {
    expect(minutesToMidnight(new Date(2026, 9, 20, 17, 48, 0))).toBe(372);
    expect(timeLeftLabel(372)).toBe("6 h 12 m");
    expect(timeLeftLabel(9)).toBe("9 m");
  });

  it("shows a cleared quest without the start button", () => {
    render(
      <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()}>
        <QuestWindow items={[item({ completed_at: "2026-10-20T10:00:00", progress: 5 })]} onComplete={vi.fn()} onStart={vi.fn()} />
      </PrefsProvider>,
    );
    expect(screen.getByText("Cleared")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start today's session" })).toBeNull();
  });
});

describe("Insights", () => {
  it("keeps at most three, each with where it came from", () => {
    const review = {
      week_start: "2026-10-12", week_end: "2026-10-18", sessions_done: 3, sessions_planned: 3, summary: "", summary_source: "template", algo_version: "review-v1", findings: [],
      top: [1, 2, 3].map((n) => ({ code: `f${n}`, severity: 1, title: `Finding ${n}`, detail: `Detail ${n}.`, proposal: null, numbers: {} })),
    } as WeeklyReview;
    const list = buildInsights(tip, review);
    expect(list).toHaveLength(3);
    expect(list[0].why).toContain('Rule "under_quads"');
    expect(list[1].why).toContain("Detail 1.");
  });
});
