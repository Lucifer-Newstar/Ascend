import type { Plan, ProgramSummary } from "@ascend/shared";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { expectNoAxeViolations } from "../test/axe";
import { ProgramCard, planTarget } from "./ProgramCard";
import { ToastProvider } from "./Toast";

vi.mock("../api/client", () => ({
  api: { currentPlan: vi.fn(), programs: vi.fn(), choosePlan: vi.fn(), leavePlan: vi.fn(), planWorkout: vi.fn(), saveProgram: vi.fn(), followProgram: vi.fn() },
}));

const day = (key: string, name: string, weekday: number) => ({
  key, name, focus: "Heavy press and row", weekday,
  items: [
    { exercise_id: 1, exercise: "Barbell Bench Press", sets: 4, rep_low: 5, rep_high: 8, target_rpe: 8, rest_s: 180, target: "4 × 6 @ 62.5 kg, RPE 8", done_sets: 2 },
    { exercise_id: 2, exercise: "Barbell Row", sets: 4, rep_low: 6, rep_high: 10, target_rpe: 8, rest_s: 150, target: null, done_sets: 0 },
  ],
});

const plan: Plan = {
  id: 3, source: "program", algo_version: "programs-v1", program_key: "upper_lower_4", name: "Upper / lower, 4 days",
  started_on: "2026-10-12", days_per_week: 4, days: [day("upper_a", "Upper A", 0)], next: day("upper_a", "Upper A", 0),
  sessions_done: 3, this_week_done: 1, last_trained: "2026-10-17", deload_week: false, recent: [],
  reason: "you last trained Lower B on 2026-10-17, so Upper A is next",
  why: { formula: "next = the day after the last program day you trained", inputs: { sessions_done: 3 } },
};

const catalog: ProgramSummary[] = [
  { key: "full_body_3", name: "Full body, 3 days", summary: "Three whole-body sessions.", level: "beginner", equipment: "gym", days_per_week: 3, fits_equipment: true, days: [day("a1", "Full body A", 0)] },
  { key: "upper_lower_4", name: "Upper / lower, 4 days", summary: "Each muscle twice.", level: "intermediate", equipment: "gym", days_per_week: 4, fits_equipment: false, days: [day("upper_a", "Upper A", 0)] },
];

const renderCard = (onPick = vi.fn()) => render(<ToastProvider><ProgramCard onPick={onPick} /></ToastProvider>);

describe("ProgramCard", () => {
  beforeEach(() => {
    vi.mocked(api.currentPlan).mockResolvedValue(plan);
    vi.mocked(api.programs).mockResolvedValue(catalog);
    vi.mocked(api.choosePlan).mockResolvedValue(plan);
    vi.mocked(api.leavePlan).mockResolvedValue(undefined);
  });

  it("shows the next session with targets and sets done, and opens an exercise", async () => {
    const onPick = vi.fn();
    const { container } = renderCard(onPick);
    const list = await screen.findByRole("list", { name: "Upper A exercises" });
    expect(list).toHaveTextContent("4 × 6 @ 62.5 kg, RPE 8");
    expect(list).toHaveTextContent("4 × 6–10"); // no target yet: the program's own zone
    expect(within(list).getByLabelText("2 of 4 sets done")).toBeInTheDocument();
    expect(screen.getByText(/so Upper A is next/)).toBeInTheDocument();
    await userEvent.click(within(list).getByRole("button", { name: /Barbell Row/ }));
    expect(onPick).toHaveBeenCalledWith(2, undefined); // the item's section rides along when the plan names one
    await expectNoAxeViolations(container);
  });

  it("offers the catalog when no program is followed, and follows one", async () => {
    vi.mocked(api.currentPlan).mockResolvedValueOnce(null);
    renderCard();
    expect(await screen.findByRole("region", { name: "Follow a program" })).toBeInTheDocument();
    expect(screen.queryByText("Needs equipment you didn't list at setup.")).not.toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: /Explore all \(1 need other kit\)/ }));
    expect(await screen.findByText("Needs equipment you didn't list at setup.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Follow Full body, 3 days" }));
    expect(api.choosePlan).toHaveBeenCalledWith("full_body_3");
    expect(await screen.findByRole("list", { name: "Upper A exercises" })).toBeInTheDocument();
  });

  it("changes or stops the program from the card", async () => {
    renderCard();
    await userEvent.click(await screen.findByRole("button", { name: "Change" }));
    expect(await screen.findByRole("button", { name: "Follow Upper / lower, 4 days" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Stop following a program" }));
    expect(api.leavePlan).toHaveBeenCalled();
  });

  it("filters programs by section, tags Expert, and generates one for the section", async () => {
    vi.mocked(api.currentPlan).mockResolvedValue(null);
    vi.mocked(api.programs).mockResolvedValue([
      ...catalog,
      { key: "boxing_basics_3", name: "Boxing Basics, 3 days", summary: "Solo boxing.", level: "beginner", equipment: "bodyweight", days_per_week: 3, fits_equipment: true, days: [day("d1", "Boxing A", 0)], section: "martial_arts" },
      { key: "fighter_rounds_4", name: "Fighter Rounds, 4 days", summary: "Hard rounds.", level: "expert", equipment: "bodyweight", days_per_week: 4, fits_equipment: true, days: [day("d1", "Rounds", 0)], section: "martial_arts" },
    ]);
    vi.mocked(api.planWorkout).mockResolvedValue({ draft: { name: "My Martial Arts Plan, 3 days" } } as never);
    vi.mocked(api.saveProgram).mockResolvedValue({ id: 7, name: "My Martial Arts Plan, 3 days" } as never);
    vi.mocked(api.followProgram).mockResolvedValue({ id: 7 } as never);
    renderCard();
    await userEvent.click(await screen.findByRole("button", { name: "Martial arts" }));
    expect(screen.queryByText("Full body, 3 days")).toBeNull();
    expect(screen.getByText("Boxing Basics, 3 days")).toBeInTheDocument();
    expect(screen.getByText("Expert")).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("generate-program"));
    expect(api.planWorkout).toHaveBeenCalledWith(expect.objectContaining({ section: "martial_arts" }));
    expect(api.followProgram).toHaveBeenCalledWith(7);
  });

  it("doses time-based moves in minutes", () => {
    const it_ = { exercise_id: 1, exercise: "Running", sets: 1, rep_low: 25, rep_high: 35, target_rpe: 7, rest_s: 0, measure: "time" } as never;
    expect(planTarget(it_)).toBe("25–35 min");
    expect(planTarget({ ...(it_ as object), sets: 3, rep_low: 3, rep_high: 3 } as never)).toBe("3 × 3 min");
  });
});
