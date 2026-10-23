import type { StreakInfo } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { StreakReasonCard, dayName } from "./StreakReason";
import { ToastProvider } from "./Toast";

vi.mock("../api/client", () => ({ api: { streakReason: vi.fn() } }));

const due: StreakInfo = { current: 6, best: 6, excused: 0, active_today: false, reason_due: "2026-10-21" };

function renderCard(s: StreakInfo, onSaved = vi.fn()) {
  render(
    <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()}>
      <ToastProvider><StreakReasonCard streak={s} onSaved={onSaved} /></ToastProvider>
    </PrefsProvider>,
  );
  return onSaved;
}

describe("missed-day reason", () => {
  it("names the day", () => {
    expect(dayName("2026-10-21")).toBe("Wednesday");
  });

  it("shows nothing when no day is waiting for a reason", () => {
    renderCard({ ...due, reason_due: null });
    expect(screen.queryByTestId("streak-reason")).not.toBeInTheDocument();
  });

  it("asks why and keeps the streak with a quick pick", async () => {
    vi.mocked(api.streakReason).mockResolvedValue({ ...due, excused: 1, reason_due: null });
    const onSaved = renderCard(due);
    expect(screen.getByText(/You missed Wednesday/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sick" }));
    expect(api.streakReason).toHaveBeenCalledWith("2026-10-21", "Sick");
    expect(onSaved).toHaveBeenCalled();
  });

  it("takes a reason in your own words", async () => {
    vi.mocked(api.streakReason).mockResolvedValue({ ...due, excused: 1, reason_due: null });
    renderCard(due);
    await userEvent.type(screen.getByLabelText("Your reason"), "power cut all evening");
    await userEvent.click(screen.getByRole("button", { name: "Keep my streak" }));
    expect(api.streakReason).toHaveBeenLastCalledWith("2026-10-21", "power cut all evening");
  });
});
