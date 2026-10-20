import type { Checkin, DeloadAdvice } from "@ascend/shared";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { CheckinCard } from "./CheckinCard";
import { DeloadCard, WeeklyReviewCard } from "./PlanCards";
import { ToastProvider } from "./Toast";

vi.mock("../api/client", () => ({
  api: { checkinToday: vi.fn(), checkin: vi.fn(), deload: vi.fn(), startDeload: vi.fn(), weeklyReview: vi.fn() },
}));

const wrap = (ui: React.ReactElement) => render(<ToastProvider>{ui}</ToastProvider>);

const red: Checkin = {
  day: "2026-10-20", sleep: 1, energy: 2, soreness: "a_lot", mood: 2, readiness: 11, band: "red",
  quest_adjustment: "Today's training quest is swapped for 15 minutes of mobility.", algo_version: "readiness-v1",
};

describe("CheckinCard", () => {
  beforeEach(() => vi.mocked(api.checkinToday).mockResolvedValue(null));

  it("sends the answers and shows the readiness", async () => {
    const saved = vi.fn();
    vi.mocked(api.checkin).mockResolvedValue(red);
    wrap(<CheckinCard refreshKey={0} onSaved={saved} />);
    const form = await screen.findByRole("form", { name: "Morning check-in" });
    await userEvent.click(screen.getAllByLabelText("1")[0]); // sleep
    await userEvent.click(screen.getByLabelText("A lot"));
    vi.mocked(api.checkinToday).mockResolvedValue(red);
    await userEvent.click(screen.getByRole("button", { name: "Save check-in" }));
    expect(api.checkin).toHaveBeenCalledWith({ sleep: 1, energy: 3, soreness: "a_lot", mood: 3 });
    await waitFor(() => expect(saved).toHaveBeenCalled());
    expect(await screen.findByLabelText("Readiness 11 of 100")).toBeInTheDocument();
    expect(form).not.toBeInTheDocument();
  });
});

describe("DeloadCard", () => {
  const advice: DeloadAdvice = {
    recommended: true, kind: "reactive", training_weeks: 3, guidance: "Halve your sets this week.", deload_week: null,
    algo_version: "deload-v2",
    signals: [
      { code: "LOW_READINESS", active: true, detail: "3 check-ins, average readiness 38" },
      { code: "HEAVY_SORENESS", active: false, detail: "very sore on 0 of the last 7 check-ins" },
    ],
  };

  it("explains a reactive deload and starts it", async () => {
    vi.mocked(api.deload).mockResolvedValue(advice);
    vi.mocked(api.startDeload).mockResolvedValue({ ...advice, kind: "active", deload_week: "2026-10-19" });
    wrap(<DeloadCard refreshKey={0} />);
    expect(await screen.findByText("Your recovery signals suggest an easier week.")).toBeInTheDocument();
    expect(screen.getByText("Active:")).toBeInTheDocument();
    vi.mocked(api.deload).mockResolvedValue({ ...advice, kind: "active", deload_week: "2026-10-19" });
    await userEvent.click(screen.getByRole("button", { name: "Start deload week" }));
    expect(api.startDeload).toHaveBeenCalled();
    expect(await screen.findByText(/Deload week in progress/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start deload week" })).toBeNull();
  });
});

describe("WeeklyReviewCard", () => {
  it("says so when there is nothing to change", async () => {
    vi.mocked(api.weeklyReview).mockResolvedValue({
      week_start: "2026-10-14", week_end: "2026-10-20", sessions_done: 3, sessions_planned: 3, findings: [], top: [],
      summary: "", summary_source: "template", algo_version: "review-v1",
    });
    wrap(<WeeklyReviewCard refreshKey={0} />);
    expect(await screen.findByText(/Nothing to change/)).toBeInTheDocument();
    expect(screen.getByText("3/3")).toBeInTheDocument();
  });
});
