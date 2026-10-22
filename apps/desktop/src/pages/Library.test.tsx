import type { Exercise, ExerciseDetail } from "@ascend/shared";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { axeViolations } from "../test/axe";
import { takePendingExercise } from "../lib/pending";
import { EMPTY_FILTERS, filterExercises, LibraryPage } from "./Library";

vi.mock("../api/client", () => ({ api: { exercises: vi.fn(), exercise: vi.fn() } }));

const ex = (over: Partial<Exercise>): Exercise => ({
  id: 1, name: "Pull-up", equipment: "bodyweight", section: "calisthenics", met: null, time_based: false,
  muscles: [{ muscle: "latissimus_dorsi", weight: 1 }, { muscle: "biceps_long", weight: 0.5 }], measure: "reps", difficulty: "intermediate",
  image: "exercises/pullups.webp", source: "ascend", is_custom: false, aliases: ["pullups"], ...over,
});

const LIST = [
  ex({}),
  ex({ id: 2, name: "Barbell Bench Press", equipment: "barbell", section: "gym", muscles: [{ muscle: "pec_major_sternal", weight: 1 }], difficulty: "intermediate", aliases: [] }),
  ex({ id: 3, name: "Tuck Front Lever", measure: "hold", difficulty: "intermediate", image: null, aliases: ["tuck fl"] }),
  ex({ id: 4, name: "Running", section: "cardio", time_based: true, met: 9.8, equipment: "none", muscles: [{ muscle: "gastrocnemius", weight: 1 }], difficulty: "beginner", aliases: [] }),
  ex({ id: 5, name: "My Ring Row", is_custom: true, source: "custom", aliases: [] }),
];

describe("filterExercises", () => {
  it("searches names and aliases, ignoring hyphens and plurals", () => {
    expect(filterExercises(LIST, { ...EMPTY_FILTERS, q: "pullups" }).map((e) => e.id)).toEqual([1]);
    expect(filterExercises(LIST, { ...EMPTY_FILTERS, q: "front lev" }).map((e) => e.id)).toEqual([3]);
    expect(filterExercises(LIST, { ...EMPTY_FILTERS, q: "tuck fl" }).map((e) => e.id)).toEqual([3]);
  });

  it("filters by type, muscle, equipment, difficulty and custom", () => {
    expect(filterExercises(LIST, { ...EMPTY_FILTERS, type: "strength" }).map((e) => e.id)).toEqual([2]);
    expect(filterExercises(LIST, { ...EMPTY_FILTERS, type: "cardio" }).map((e) => e.id)).toEqual([4]);
    expect(filterExercises(LIST, { ...EMPTY_FILTERS, muscle: "latissimus_dorsi" }).map((e) => e.id)).toEqual([1, 3, 5]);
    expect(filterExercises(LIST, { ...EMPTY_FILTERS, equipment: "barbell" }).map((e) => e.id)).toEqual([2]);
    expect(filterExercises(LIST, { ...EMPTY_FILTERS, difficulty: "beginner" }).map((e) => e.id)).toEqual([4]);
    expect(filterExercises(LIST, { ...EMPTY_FILTERS, customOnly: true }).map((e) => e.id)).toEqual([5]);
  });
});

describe("LibraryPage", () => {
  beforeEach(() => {
    vi.mocked(api.exercises).mockResolvedValue(LIST);
    sessionStorage.clear();
  });

  it("lists exercises, narrows them and has no axe violations", async () => {
    const { container } = render(<LibraryPage onNavigate={vi.fn()} refreshKey={0} />);
    const grid = await screen.findByRole("list", { name: "Exercises" });
    expect(within(grid).getAllByRole("listitem")).toHaveLength(5);
    await userEvent.click(screen.getByRole("radio", { name: "Cardio" }));
    expect(within(grid).getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByRole("status")).toHaveTextContent("1 of 5 exercises");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("opens the detail and hands the exercise to the logger", async () => {
    const detail: ExerciseDetail = {
      ...LIST[0], instructions: ["Hang from a bar.", "Pull until the chin clears it."], mechanic: "compound", rep_low: 6, rep_high: 12,
      field_sources: { muscles: "library", instructions: "library" }, attribution: [], source_ref: "Pullups", created_at: null,
      skills: [{ skill_key: "muscle_up", skill_name: "Muscle-up", step_name: "Pull-up", role: "step" }], sets_logged: 3,
    };
    vi.mocked(api.exercise).mockResolvedValue(detail);
    const nav = vi.fn();
    render(<LibraryPage onNavigate={nav} refreshKey={0} />);
    await userEvent.click(await screen.findByRole("button", { name: /Pull-up/ }));
    expect(await screen.findByRole("heading", { name: "Pull-up" })).toBeInTheDocument();
    expect(screen.getByText("Pull until the chin clears it.")).toBeInTheDocument();
    expect(screen.getByText(/Muscle-up · step: Pull-up/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Log it" }));
    expect(nav).toHaveBeenCalledWith("workout");
    expect(takePendingExercise()).toEqual({ id: 1, section: "calisthenics" });
    expect(takePendingExercise()).toBeNull(); // one use
  });
});
