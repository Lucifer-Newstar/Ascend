import type { ShortSession } from "@ascend/shared";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { readShort } from "../lib/shortSession";
import { clearApiCache } from "../lib/useApi";
import { ToastProvider } from "./Toast";
import { TodayWorkout } from "./TodayWorkout";

vi.mock("../api/client", () => ({ api: { currentPlan: vi.fn(), shortSession: vi.fn() } }));

const short: ShortSession = {
  session: "Push A", minutes: 9, algo_version: "schedule-v1",
  note: "A 9-minute version of Push A: the first moves at two sets each. It counts for your streak like any session; the full session stays next.",
  items: [
    { exercise_id: 3, exercise: "Push-up", sets: 2, rep_low: 8, rep_high: 12, rest_s: 45, measure: "reps", section: "calisthenics" },
    { exercise_id: 4, exercise: "Plank", sets: 2, rep_low: 20, rep_high: 30, rest_s: 45, measure: "hold", section: "calisthenics" },
  ],
};

describe("TodayWorkout: the 10-minute version (v1.4)", () => {
  beforeEach(() => {
    clearApiCache();
    window.sessionStorage.clear();
    vi.mocked(api.currentPlan).mockResolvedValue({
      name: "Starter", next: { key: "a", name: "Push A", focus: "Push", weekday: 0, items: [
        { exercise_id: 3, exercise: "Push-up", sets: 3, rep_low: 8, rep_high: 12, target_rpe: 7, rest_s: 90, measure: "reps" },
      ] },
    } as never);
    vi.mocked(api.shortSession).mockResolvedValue(short);
  });

  it("offers a short version, shows it and starts it on Train", async () => {
    const nav = vi.fn();
    render(<ToastProvider><TodayWorkout onNavigate={nav} /></ToastProvider>);
    await userEvent.click(await screen.findByRole("button", { name: "Short on time? 10-minute version" }));
    const box = await screen.findByTestId("short-session");
    expect(box).toHaveTextContent("9-minute version");
    expect(within(box).getByText("Push-up")).toBeInTheDocument();
    expect(box).toHaveTextContent("2 × 8–12 · rest 45 s");
    expect(box).toHaveTextContent("2 × 20–30 s · rest 45 s");
    expect(box).toHaveTextContent("counts for your streak");
    await userEvent.click(screen.getByRole("button", { name: "Start 9-minute session" }));
    expect(nav).toHaveBeenCalledWith("workout");
    expect(readShort()?.session).toBe("Push A");
  });

  it("goes back to the full session", async () => {
    render(<ToastProvider><TodayWorkout onNavigate={vi.fn()} /></ToastProvider>);
    await userEvent.click(await screen.findByRole("button", { name: "Short on time? 10-minute version" }));
    await userEvent.click(await screen.findByRole("button", { name: "Full session instead" }));
    expect(screen.queryByTestId("short-session")).toBeNull();
    expect(screen.getByRole("button", { name: "Start workout" })).toBeInTheDocument();
  });
});
