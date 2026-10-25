import type { WeekPlan } from "@ascend/shared";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { clearApiCache } from "../lib/useApi";
import { expectNoAxeViolations } from "../test/axe";
import { ToastProvider } from "./Toast";
import { WeekPlanPanel, nextMonday } from "./WeekPlan";

vi.mock("../api/client", () => ({ api: { week: vi.fn(), planWeek: vi.fn() } }));

const day = (i: number, over: Partial<WeekPlan["days"][number]> = {}) => ({
  day: `2026-10-${String(26 + i).padStart(2, "0")}`, weekday: i, planned: false, done: false, session: null, today: false, past: false, ...over,
});

const week: WeekPlan = {
  week_start: "2026-10-26",
  days: [
    day(0, { planned: true, done: true, past: true }),
    day(1, { past: true }),
    day(2, { planned: true, past: true }),
    day(3, { planned: true, today: true, session: "Pull" }),
    day(4),
    day(5, { planned: true, session: "Legs" }),
    day(6),
  ],
  planned: 4, done: 1, custom: false, source: "you", algo_version: "schedule-v1",
};

function renderPanel() {
  return render(<ToastProvider><WeekPlanPanel /></ToastProvider>);
}

describe("WeekPlanPanel (v1.4)", () => {
  beforeEach(() => {
    clearApiCache();
    vi.mocked(api.week).mockResolvedValue(week);
    vi.mocked(api.planWeek).mockResolvedValue({ ...week, week_start: "2026-11-02", planned: 3, custom: true });
  });

  it("shows planned vs done, rest as rest and the coming sessions", async () => {
    const { container } = renderPanel();
    expect(await screen.findByTestId("week-count")).toHaveTextContent("1 of 4 planned sessions done");
    expect(screen.getByTestId("week-day-0")).toHaveAccessibleName("Monday: Done");
    expect(screen.getByTestId("week-day-1")).toHaveAccessibleName("Tuesday: Rest");
    expect(screen.getByTestId("week-day-2")).toHaveAccessibleName("Wednesday: Not logged");
    expect(screen.getByTestId("week-day-3")).toHaveAccessibleName("Thursday: Pull");
    expect(screen.getByTestId("week-day-5")).toHaveAccessibleName("Saturday: Legs");
    expect(screen.queryByText(/missed/i)).toBeNull();
    await expectNoAxeViolations(container);
  });

  it("plans next week from this week's days", async () => {
    renderPanel();
    await userEvent.click(await screen.findByRole("button", { name: "Plan next week" }));
    const box = screen.getByTestId("plan-next-week");
    expect(within(box).getByRole("button", { name: "Next Monday" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(within(box).getByRole("button", { name: "Next Monday" }));
    await userEvent.click(within(box).getByRole("button", { name: "Plan 3 days" }));
    expect(api.planWeek).toHaveBeenCalledWith("2026-11-02", [2, 3, 5]);
    expect(await screen.findByText("Next week: 3 training days planned")).toBeInTheDocument();
  });

  it("finds the next Monday across a month end", () => {
    expect(nextMonday("2026-10-26")).toBe("2026-11-02");
    expect(nextMonday("2026-12-28")).toBe("2027-01-04");
  });
});
