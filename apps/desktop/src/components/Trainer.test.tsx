import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CoachReply, WeeklyReview } from "@ascend/shared";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { moodFor, numbersIn, trainerLine } from "../lib/trainer";
import { expectNoAxeViolations } from "../test/axe";
import { InsightsCard } from "./Insights";
import { TrainerToggle } from "./Trainer";

const tip = { text: "Bench 62.5 kg × 6 next time: you beat 60 kg × 8 at RPE 8.", tip_code: "raised", source: "rules" } as unknown as CoachReply;
const review = {
  week_start: "2026-10-13", week_end: "2026-10-19", algo_version: "review-1",
  top: [{ code: "over_volume", title: "Lats got 24 sets this week, above the 10–20 band.", detail: "24 effective sets.", proposal: null }],
} as unknown as WeeklyReview;

function renderCard(trainer: boolean, save = vi.fn(async (p) => ({ ...DEFAULT_SETTINGS, trainer, ...p }))) {
  return render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, trainer }} save={save}>
      <TrainerToggle />
      <InsightsCard tip={tip} review={review} onOpenCoach={() => {}} />
    </PrefsProvider>,
  );
}

describe("trainer voice", () => {
  it("keeps every engine number and stays within 40 words", () => {
    for (const mood of ["neutral", "proud", "warning", "hyped"] as const) {
      const line = trainerLine("k", tip.text, mood);
      expect(numbersIn(line)).toEqual(numbersIn(tip.text));
      expect(line).toContain("Hunter");
      expect(line.split(/\s+/).length).toBeLessThanOrEqual(40);
    }
    expect(trainerLine("same", "x", "proud")).toBe(trainerLine("same", "x", "proud"));
  });

  it("picks the expression from the insight kind", () => {
    expect(moodFor("deload_advised")).toBe("warning");
    expect(moodFor("over_volume")).toBe("warning");
    expect(moodFor("new_pr")).toBe("proud");
    expect(moodFor("rank_up")).toBe("hyped");
    expect(moodFor("weekly_summary")).toBe("neutral");
  });

  it("speaks the insights with the trainer on, and Why? stays one tap away", async () => {
    const { container } = renderCard(true);
    expect(screen.getByRole("heading", { name: "Iskra's briefing" })).toBeInTheDocument();
    expect(screen.getAllByTestId("trainer-says")).toHaveLength(2);
    expect(screen.getByAltText(/Instructor Iskra Vey, stern/)).toBeInTheDocument();
    expect(screen.getByText(/Hunter.*Lats got 24 sets this week/)).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: "Why?" })[1]);
    expect(screen.getByText(/24 effective sets/)).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });

  it("plain mode shows the same facts without the persona, and the toggle saves", async () => {
    const save = vi.fn(async (p) => ({ ...DEFAULT_SETTINGS, ...p }));
    renderCard(false, save);
    expect(screen.getByRole("heading", { name: "Insights" })).toBeInTheDocument();
    expect(screen.queryByTestId("trainer-says")).toBeNull();
    expect(screen.getByText(tip.text)).toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: "Trainer" });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(toggle);
    expect(save).toHaveBeenCalledWith({ trainer: true });
    await waitFor(() => expect(screen.getByRole("heading", { name: "Iskra's briefing" })).toBeInTheDocument());
  });
});
