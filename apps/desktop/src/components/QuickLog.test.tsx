import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { mealTypeFor, NotLoggedBanner, QuickLogCard } from "./QuickLog";
import { RoughBadge } from "./RoughBadge";

vi.mock("../api/client", () => ({
  api: {
    exercises: vi.fn(),
    foods: vi.fn(),
    activeWorkout: vi.fn(),
    startWorkout: vi.fn(),
    logSet: vi.fn(),
    logMeal: vi.fn(),
    logWeight: vi.fn(),
  },
}));

function renderCard(onLogged = vi.fn(), units: "metric" | "imperial" = "metric") {
  const r = render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, units }} save={vi.fn()}>
      <QuickLogCard onLogged={onLogged} />
    </PrefsProvider>,
  );
  return { ...r, onLogged };
}

describe("Quick log", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.exercises).mockResolvedValue([{ id: 7, name: "Bench Press", section: "gym", measure: "reps" }] as never);
    vi.mocked(api.foods).mockResolvedValue([{ id: 3, name: "Banana", portion_label: "1 medium", portion_g: 118, kcal: 105, protein_g: 1.3, carbs_g: 27, fat_g: 0.4 }] as never);
    vi.mocked(api.activeWorkout).mockResolvedValue(null);
    vi.mocked(api.startWorkout).mockResolvedValue({ id: 41 } as never);
    vi.mocked(api.logSet).mockResolvedValue({} as never);
    vi.mocked(api.logMeal).mockResolvedValue({ meal: {}, xp_awarded: 5 });
    vi.mocked(api.logWeight).mockResolvedValue({} as never);
  });

  it("logs one set into a new workout when none is open", async () => {
    const { onLogged, container } = renderCard();
    await userEvent.type(screen.getByLabelText("Exercise"), "Bench Press");
    await waitFor(() => expect(api.exercises).toHaveBeenCalled());
    await waitFor(() => expect(container.querySelector('option[value="Bench Press"]')).not.toBeNull());
    await userEvent.type(screen.getByLabelText("Load (kg)"), "60");
    await userEvent.type(screen.getByLabelText("Reps"), "8");
    await userEvent.click(screen.getByRole("button", { name: "Log" }));
    await waitFor(() => expect(api.logSet).toHaveBeenCalledWith(41, { exercise_id: 7, weight_kg: 60, reps: 8 }));
    expect(api.startWorkout).toHaveBeenCalledWith("gym");
    expect(onLogged).toHaveBeenCalledWith("Set: Bench Press");
    expect(screen.getByRole("status")).toHaveTextContent("counts for your streak");
    await expectNoAxeViolations(container);
  });

  it("logs a meal for the time of day and a weigh-in in the user's units", async () => {
    const { container } = renderCard(vi.fn(), "imperial");
    await userEvent.click(screen.getByText("Meal"));
    await userEvent.type(screen.getByLabelText("Food"), "Banana");
    await waitFor(() => expect(container.querySelector('option[value="Banana"]')).not.toBeNull());
    await userEvent.click(screen.getByRole("button", { name: "Log" }));
    await waitFor(() => expect(api.logMeal).toHaveBeenCalledWith(mealTypeFor(new Date().getHours()), [{ food_id: 3, portions: 1 }]));
    await userEvent.click(screen.getByText("Weigh-in"));
    await userEvent.type(screen.getByLabelText("Weight (lb)"), "154");
    await userEvent.click(screen.getByRole("button", { name: "Log" }));
    await waitFor(() => expect(api.logWeight).toHaveBeenCalled());
    expect(vi.mocked(api.logWeight).mock.calls[0][0]).toBeCloseTo(69.85, 1);
  });

  it("asks for a pick from the list instead of guessing", async () => {
    renderCard();
    await userEvent.type(screen.getByLabelText("Exercise"), "Something odd");
    await userEvent.click(screen.getByRole("button", { name: "Log" }));
    expect(await screen.findByText("Pick an exercise from the list.")).toBeInTheDocument();
    expect(api.logSet).not.toHaveBeenCalled();
  });

  it("maps the hour to a meal", () => {
    expect([mealTypeFor(8), mealTypeFor(13), mealTypeFor(19), mealTypeFor(23)]).toEqual(["breakfast", "lunch", "dinner", "snack"]);
  });

  it("banner points at Quick log", async () => {
    const open = vi.fn();
    render(<NotLoggedBanner onOpen={open} />);
    expect(screen.getByTestId("not-logged-banner")).toHaveTextContent("You haven't logged anything today.");
    await userEvent.click(screen.getByRole("button", { name: "Quick log →" }));
    expect(open).toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Not today" }));
    expect(screen.queryByTestId("not-logged-banner")).toBeNull();
    localStorage.clear();
  });
});

describe("RoughBadge", () => {
  it("shows only below the threshold, with the count", () => {
    const { rerender } = render(<RoughBadge n={5} unit="days" enough={14} />);
    expect(screen.getByTestId("rough-badge")).toHaveTextContent("rough · based on 5 days");
    rerender(<RoughBadge n={1} unit="days" enough={14} />);
    expect(screen.getByTestId("rough-badge")).toHaveTextContent("based on 1 day");
    rerender(<RoughBadge n={20} unit="days" enough={14} />);
    expect(screen.queryByTestId("rough-badge")).toBeNull();
  });
});
