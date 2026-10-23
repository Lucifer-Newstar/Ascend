import { fireEvent, render, screen } from "@testing-library/react";
import type { WeekRecap } from "@ascend/shared";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { drawFrame, recapLength, recapSlides, slideAt, SLIDE_MS, type Palette } from "../lib/recap";
import { WeeklyRecapPanel } from "./WeeklyRecap";

const week: WeekRecap = {
  week_start: "2026-10-19", week_end: "2026-10-25", complete: true,
  sessions: 4, active_days: 4, sets: 42, active_minutes: 185.5, volume_kg: 5200, xp: 820,
  prs: [{ exercise: "Pull-up", weight_kg: 0, reps: 9, image: null }, { exercise: "Barbell Squat", weight_kg: 60, reps: 5, image: null }],
  sections: [{ section: "calisthenics", sets: 30 }, { section: "gym", sets: 12 }],
  best_day: { day: "2026-10-21", sets: 14 },
  boss: { name: "Iron Golem", title: "Golem Breaker", tier: "E", defeated: true },
  streak: 9, excused_days: 1, meal_days: 6, checkins: 5,
  level: 14, rank: "D", rank_title: "Striver", last_week_sessions: 3, last_week_sets: 30,
  headline: "You beat Iron Golem this week. That is what showing up looks like.", version: "recap-v1",
};

const BODY = /weight|body ?fat|bmi|slim|kg lost/i;

describe("recap slides", () => {
  it("covers the week in six slides and stays body-neutral", () => {
    const slides = recapSlides(week, "Iskra");
    expect(slides.map((s) => s.key)).toEqual(["intro", "training", "records", "boss", "habits", "rank"]);
    expect(slides[1].count).toBe(4);
    expect(slides[1].lines.join(" ")).toContain("Calisthenics");
    expect(slides[2].lines).toEqual(["Pull-up · 9 reps", "Barbell Squat · 60 kg × 5"]);
    expect(slides[3].lines[0]).toContain("Golem Breaker");
    expect(slides[4].lines.join(" ")).toContain("1 missed day kept with a reason");
    expect(slides[5].lines[1]).toContain("Iskra");
    for (const s of slides) expect([s.kicker, s.big, s.unit ?? "", ...s.lines].join(" ")).not.toMatch(BODY);
  });

  it("drops the boss slide when there was no boss and says so kindly with no records", () => {
    const slides = recapSlides({ ...week, boss: null, prs: [] }, "Vera");
    expect(slides.map((s) => s.key)).not.toContain("boss");
    expect(slides.find((s) => s.key === "records")?.big).toBe("No new records");
  });

  it("knows which slide is on screen and draws on a solid panel", () => {
    const slides = recapSlides(week, "Iskra");
    expect(recapLength(slides)).toBe(6 * SLIDE_MS);
    expect(slideAt(slides, SLIDE_MS * 2 + 10)).toEqual({ index: 2, local: 10 });
    expect(slideAt(slides, 1e9).index).toBe(5);
    const calls: string[] = [];
    const ctx = new Proxy({} as Record<string, unknown>, {
      get: (t, k: string) => (k in t ? t[k] : k === "measureText" ? () => ({ width: 10 }) : k === "createLinearGradient" ? () => ({ addColorStop: () => {} }) : () => calls.push(k)),
      set: (t, k: string, v) => ((t[k] = v), true),
    }) as unknown as CanvasRenderingContext2D;
    ctx.font = "700 88px Rajdhani, sans-serif";
    const p: Palette = { bg: "#000", panel: "#111", ink: "#fff", muted: "#ccc", accent: "#70f", line: "#333" };
    drawFrame(ctx, slides, 100, p, true);
    expect(calls).toContain("fillText");
    expect(calls).toContain("rect");
  });
});

describe("WeeklyRecapPanel", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows the week and opens the player", async () => {
    vi.spyOn(api, "recap").mockResolvedValue(week);
    render(<WeeklyRecapPanel />);
    expect(await screen.findByText(week.headline)).toBeInTheDocument();
    expect(screen.getByTestId("recap-summary")).toHaveTextContent("4 sessions · 42 sets · 2 records · 9-day streak");
    fireEvent.click(screen.getByRole("button", { name: "Play recap" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Your week");
    expect(screen.getByRole("img").getAttribute("aria-label")).toContain("Iron Golem");
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("asks for last week with a date in it", async () => {
    const spy = vi.spyOn(api, "recap").mockResolvedValue(week);
    render(<WeeklyRecapPanel />);
    await screen.findByText(week.headline);
    fireEvent.click(screen.getByRole("radio", { name: "Last week" }));
    await vi.waitFor(() => expect(spy).toHaveBeenLastCalledWith(expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/)));
  });
});
