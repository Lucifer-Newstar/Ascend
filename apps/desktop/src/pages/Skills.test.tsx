import type { SkillDetail, SkillSummary } from "@ascend/shared";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { axeViolations } from "../test/axe";
import { skillKeyFromHash, SkillsPage } from "./Skills";

vi.mock("../api/client", () => ({ api: { skills: vi.fn(), skill: vi.fn(), trainSkill: vi.fn() } }));

const summary = (over: Partial<SkillSummary> = {}): SkillSummary => ({
  key: "front_lever", name: "Front lever", family: "levers", summary: "Horizontal under the bar, face up.", stretch: false,
  current_step: "tuck", current_step_name: "Tuck front lever", next_step: "adv_tuck", next_step_name: "Advanced tuck",
  pct_to_next: 56, steps_unlocked: 1, steps_total: 5, acquired: false, last_trained: "2026-10-19T07:30:00", sessions_28d: 5, rusty: false,
  ...over,
});

const detail = (over: Partial<SkillDetail> = {}): SkillDetail => ({
  ...summary(),
  steps: [
    { key: "tuck", name: "Tuck front lever", exercise: "Tuck Front Lever", exercise_id: 7, measure: "hold", status: "unlocked", pct: 100,
      unlocked_at: "2026-10-17T07:30:00", criteria: [], requires: [], xp: 60, uncertain: false, note: "" },
    { key: "adv_tuck", name: "Advanced tuck", exercise: "Advanced Tuck Front Lever", exercise_id: 8, measure: "hold", status: "next", pct: 56,
      unlocked_at: null, requires: ["tuck"], xp: 80, uncertain: false, note: "",
      criteria: [{ text: "3×15 s Tuck Front Lever", exercise: "Tuck Front Lever", exercise_id: 7, sets: 3, target: 15, unit: "s", added_kg: 0,
        per_side: false, best_value: 10, best_score: 0.62, sessions_met: 0, sessions_needed: 2, pct: 56, met: false, ignored_sets: 1 }] },
    { key: "straddle", name: "Straddle", exercise: "Straddle Front Lever", exercise_id: 9, measure: "hold", status: "locked", pct: 0,
      unlocked_at: null, requires: ["adv_tuck"], xp: 150, uncertain: true, note: "", criteria: [] },
  ],
  feeders: [{ exercise_id: 1, name: "Pull-up", measure: "reps", sets_28d: 12 }],
  eta: { days: 14.5, date: "2026-11-04", reason: "estimate from your recent trend", is_estimate: true },
  sources: [{ key: "OG", title: "Overcoming Gravity", url: "https://stevenlow.org/overcoming-gravity/" }],
  engine_version: "skills-v1",
  ...over,
});

const renderPage = (onNavigate = vi.fn()) =>
  render(<ToastProvider><SkillsPage onNavigate={onNavigate} onChanged={vi.fn()} /></ToastProvider>);

beforeEach(() => {
  vi.mocked(api.skills).mockReset().mockResolvedValue([
    summary(),
    summary({ key: "planche", name: "Planche", family: "push", stretch: true, current_step: null, current_step_name: null, pct_to_next: 0, steps_unlocked: 0, sessions_28d: 0 }),
  ]);
  vi.mocked(api.skill).mockReset().mockResolvedValue(detail());
  vi.mocked(api.trainSkill).mockReset().mockResolvedValue({ skill_key: "front_lever", added: 2, already_planned: 0, items: [], message: "Added 2 Front lever items to today's quest." });
  window.location.hash = "skills";
  sessionStorage.clear();
});

describe("skillKeyFromHash", () => {
  it("reads the tree from #skills/<key>", () => {
    expect(skillKeyFromHash("#skills/front_lever")).toBe("front_lever");
    expect(skillKeyFromHash("#skills")).toBeNull();
    expect(skillKeyFromHash("#library/front_lever")).toBeNull();
  });
});

describe("SkillsPage", () => {
  it("lists trees with the current step, % to next and badges, and filters by family", async () => {
    const { container } = renderPage();
    const list = await screen.findByRole("list", { name: "Skill trees" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("Tuck front lever")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: /Front lever: progress to Advanced tuck/ })).toHaveAttribute("aria-valuenow", "56");
    expect(screen.getByText("Stretch goal")).toBeInTheDocument();
    expect(screen.getByText("Not started")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Levers" }));
    expect(within(list).getAllByRole("listitem")).toHaveLength(1);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("opens a tree with steps, criteria, an estimate labelled as such, feeders and sources", async () => {
    const { container } = renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Front lever/ }));
    expect(window.location.hash).toBe("#skills/front_lever");
    expect(await screen.findByText("Next: Advanced tuck")).toBeInTheDocument();
    expect(screen.getByText(/best 10 s · 0 of 2 sessions/)).toBeInTheDocument();
    expect(screen.getByText(/1 implausibly long hold not counted/)).toBeInTheDocument();
    expect(screen.getByText(/Estimate: about 15 days/)).toBeInTheDocument();
    expect(screen.getByText(/A projection, not a promise/)).toBeInTheDocument();
    expect(screen.getByText("uncertain")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overcoming Gravity" })).toHaveAttribute("href", "https://stevenlow.org/overcoming-gravity/");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("says why there is no estimate yet", async () => {
    vi.mocked(api.skill).mockResolvedValue(detail({ eta: { days: null, date: null, reason: "not enough data yet: log X", is_estimate: true } }));
    window.location.hash = "skills/front_lever";
    renderPage();
    expect(await screen.findByText("No time estimate yet.")).toBeInTheDocument();
    expect(screen.getByText(/Not enough data yet: log X/)).toBeInTheDocument();
  });

  it("train adds to today's quest and Log opens the logger on the exercise to practise", async () => {
    const onNavigate = vi.fn();
    window.location.hash = "skills/front_lever";
    renderPage(onNavigate);
    await userEvent.click(await screen.findByRole("button", { name: "Train this skill" }));
    expect(api.trainSkill).toHaveBeenCalledWith("front_lever");
    expect(await screen.findByText("Added 2 Front lever items to today's quest.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Log Tuck Front Lever" }));
    expect(onNavigate).toHaveBeenCalledWith("workout");
    expect(JSON.parse(sessionStorage.getItem("ascend.pendingExercise")!)).toEqual({ id: 7, section: "calisthenics" });
  });
});
