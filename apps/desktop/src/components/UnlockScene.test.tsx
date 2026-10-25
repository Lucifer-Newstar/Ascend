import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";

import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { axeViolations } from "../test/axe";
import { UnlockScene } from "./UnlockScene";

const CUB = { key: "cosmetic:pet_frost_cub", kind: "cosmetic" as const, title: "Frost Cub", detail: "For your first seasonal boss." };
const RANK = { key: "rank:C", kind: "rank" as const, title: "Rank C", detail: "Level 12 reached" };

function renderIt(reduce = false) {
  const onDone = vi.fn();
  const utils = render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, reduce_motion: reduce }} save={vi.fn()}>
      <UnlockScene entries={[CUB, RANK]} onDone={onDone} />
    </PrefsProvider>,
  );
  return { ...utils, onDone };
}

describe("UnlockScene (v1.4)", () => {
  it("plays each unlock in turn as a full-screen reveal, focus on the button", async () => {
    const { container, onDone } = renderIt();
    expect(screen.getByRole("dialog", { name: "Frost Cub" })).toHaveAccessibleDescription("For your first seasonal boss.");
    expect(screen.getByText("New cosmetic")).toBeInTheDocument();
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
    expect(container.querySelector(".unlock-rays")).not.toBeNull();
    expect(screen.getByRole("button", { name: "Next" })).toHaveFocus();
    expect(await axeViolations(container)).toEqual([]);
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("dialog", { name: "Rank C" })).toBeInTheDocument();
    expect(screen.getByText("Rank up")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it("keeps still with Reduce motion on", () => {
    const { container } = renderIt(true);
    expect(screen.getByTestId("unlock-scene")).toHaveAttribute("data-motion", "reduced");
    expect(container.querySelector(".unlock-stage, .unlock-rays, .unlock-item")).toBeNull();
  });

  it("is CSS only: no video files", () => {
    const src = readFileSync(join(__dirname, "UnlockScene.tsx"), "utf8");
    expect(src).not.toMatch(/\.(mp4|webm|gif|mov)\b|<video/);
  });
});
