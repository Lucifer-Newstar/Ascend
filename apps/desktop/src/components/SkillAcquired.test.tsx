import type { SkillUnlock } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { axeViolations } from "../test/axe";
import { SkillAcquired } from "./SkillAcquired";

const unlock = (over: Partial<SkillUnlock> = {}): SkillUnlock => ({
  id: 1, skill_key: "muscle_up", skill_name: "Muscle-up", step_key: "c2b", step_name: "Chest-to-bar pull-up",
  unlocked_at: "2026-10-20T18:00:00", xp: 80, final: false, next_step_name: "Muscle-up negative", source: "log", ...over,
});

function renderIt(unlocks: SkillUnlock[], reduce = false) {
  const onClose = vi.fn();
  const onView = vi.fn();
  const utils = render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, reduce_motion: reduce }} save={vi.fn()}>
      <SkillAcquired unlocks={unlocks} onClose={onClose} onView={onView} />
    </PrefsProvider>,
  );
  return { ...utils, onClose, onView };
}

describe("SkillAcquired", () => {
  it("announces the step, XP and what is next, with focus on Continue", async () => {
    const { container, onClose, onView } = renderIt([unlock(), unlock({ id: 2, skill_key: "front_lever", skill_name: "Front lever", step_name: "Tuck front lever", xp: 60 })]);
    const dialog = screen.getByRole("dialog", { name: "Chest-to-bar pull-up" });
    expect(dialog).toHaveAccessibleDescription(/Muscle-up · \+140 XP\. Next up: Muscle-up negative\./);
    expect(screen.getByText("Skill acquired")).toBeInTheDocument();
    expect(screen.getByText(/Also unlocked:/)).toHaveTextContent("Tuck front lever (Front lever)");
    expect(screen.getByRole("button", { name: "Continue" })).toHaveFocus();
    expect(screen.getByTestId("confetti")).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
    await userEvent.click(screen.getByRole("button", { name: "View tree" }));
    expect(onView).toHaveBeenCalledWith("muscle_up");
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("respects Reduce motion: no pop, glow or confetti", () => {
    renderIt([unlock({ final: true, next_step_name: null })], true);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("data-motion", "reduced");
    expect(dialog.getAttribute("style") ?? "").not.toContain("animation");
    expect(screen.queryByTestId("confetti")).toBeNull();
    expect(screen.getByText("Skill acquired · tree complete")).toBeInTheDocument();
  });
});
