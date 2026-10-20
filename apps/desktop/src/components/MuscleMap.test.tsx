import type { MuscleActivity, MuscleState, Settings } from "@ascend/shared";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { MuscleMap } from "./MuscleMap";

vi.mock("../api/client", () => ({
  api: { muscleActivity: vi.fn(), muscleHistory: vi.fn(), updateSettings: vi.fn(), recovery: vi.fn(() => Promise.reject(new Error("not needed"))), recoveryExplanation: vi.fn(() => Promise.reject(new Error("not needed"))) },
}));

const m = (key: string, label: string, map_slug: string, over: Partial<MuscleState> = {}): MuscleState => ({
  key, label, group: "", map_slug, status: "under", es_7d: 0, weekly_low: 10, weekly_high: 20, readiness: 1, ready_at: null, ...over,
});
const muscles = [
  m("lower_chest", "Lower chest", "chest", { status: "recovering", es_7d: 9, readiness: 0.6, ready_at: "2026-10-21T08:00:00" }),
  m("biceps", "Biceps", "biceps", { status: "optimal", es_7d: 12, readiness: 0.98 }),
  m("quads", "Quads", "quadriceps", { status: "no_data" }),
  m("lats", "Lats", "upper-back", { status: "under", es_7d: 3 }),
];
const activity = (days: number): MuscleActivity[] => [
  { key: "lower_chest", sets: days === 30 ? 30 : 9, volume_kg: 4200, last_trained: new Date().toISOString() },
  { key: "biceps", sets: days === 30 ? 40 : 12, volume_kg: 1800, last_trained: "2026-10-15T09:00:00" },
  { key: "quads", sets: 0, volume_kg: 0, last_trained: null },
  { key: "lats", sets: 3, volume_kg: 900, last_trained: "2026-10-17T09:00:00" },
];

function renderMap(settings: Partial<Settings> = {}) {
  return render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, ...settings }} save={vi.fn()}>
      <MuscleMap muscles={muscles} />
    </PrefsProvider>,
  );
}

const figure = () => screen.getByTestId("muscle-figure");
const pathOf = (slug: string) => figure().querySelector(`path[id="${slug}"]`) as SVGPathElement;

describe("MuscleMap", () => {
  beforeEach(() => {
    vi.mocked(api.muscleActivity).mockImplementation(async (days: number) => activity(days));
    vi.mocked(api.muscleHistory).mockResolvedValue({
      code: "lower_chest", label: "Lower chest", days: 7, status: "recovering", es_7d: 9, target_low: 10, target_high: 20,
      readiness: 0.6, ready_at: null, daily: [], contributing_sets: [], suggestion: null, formula_version: "load-1.1.0",
    });
  });

  it("flips between front and back as a card rotate", async () => {
    renderMap();
    const flip = screen.getByTestId("muscle-flip");
    expect(figure()).toHaveAttribute("data-side", "front");
    expect(flip.style.transform).toBe("none");
    await userEvent.click(screen.getByRole("button", { name: "Show back of the body" }));
    expect(figure()).toHaveAttribute("data-side", "back");
    expect(flip.style.transform).toBe("rotateY(180deg)");
    expect(screen.getByRole("button", { name: "Show front of the body" })).toBeInTheDocument();
  });

  it("shows sets, volume and last trained when a muscle is hovered", async () => {
    renderMap();
    await waitFor(() => expect(api.muscleActivity).toHaveBeenCalledWith(7));
    await screen.findByText("Needs attention");
    await act(async () => {});
    fireEvent.pointerMove(pathOf("chest"), { clientX: 40, clientY: 80 });
    const tip = await screen.findByTestId("muscle-tooltip");
    expect(within(tip).getByText("Chest")).toBeInTheDocument();
    expect(within(tip).getByText("Recovering")).toBeInTheDocument();
    expect(within(tip).getByText("4,200 kg")).toBeInTheDocument();
    expect(within(tip).getByText("today")).toBeInTheDocument();
    // The hovered muscle is lifted by a generated rule scoped to this figure.
    expect(figure().querySelector("style")?.textContent).toMatch(/path\[id="chest"\] \{ transform: scale\(1\.045\)/);
    fireEvent.pointerLeave(figure());
    await waitFor(() => expect(screen.queryByTestId("muscle-tooltip")).toBeNull());
  });

  it("glows fatigued muscles and pulses the ones ready to train", async () => {
    renderMap();
    await screen.findByText("Ready again:", { exact: false });
    const css = figure().querySelector("style")?.textContent ?? "";
    expect(css).toMatch(/path\[id="chest"\] \{ filter: url\(#mm[a-z0-9]+-glow\)/i);
    expect(css).toMatch(/path\[id="biceps"\][^{]*\{ animation: asc-muscle-pulse/);
    expect(css).not.toMatch(/path\[id="chest"\][^{]*\{ animation/);
    expect(screen.getByText("Ready again:").parentElement).toHaveTextContent("Biceps, Upper back");
  });

  it("opens the drill-down when a muscle is clicked", async () => {
    renderMap();
    await act(async () => {});
    fireEvent.click(pathOf("chest"));
    const panel = await screen.findByRole("region", { name: "Muscle details" });
    expect(panel).toHaveClass("panel-in");
    expect(api.muscleHistory).toHaveBeenCalledWith("lower_chest", 7);
  });

  it("recolours by volume for the chosen range", async () => {
    renderMap();
    await userEvent.click(screen.getByLabelText("Volume"));
    await waitFor(() => expect(api.muscleActivity).toHaveBeenLastCalledWith(7));
    await userEvent.click(screen.getByLabelText("30 days"));
    await waitFor(() => expect(api.muscleActivity).toHaveBeenLastCalledWith(30));
    // Biceps carry the most sets in 30 days, so they take the deepest colour; quads are untrained.
    await waitFor(() => expect(pathOf("biceps").getAttribute("fill")).toBe("#2fd9f2"));
    expect(pathOf("quadriceps").getAttribute("fill")).not.toBe("#2fd9f2");
    expect(screen.getByText(/More sets · last 30 days/)).toBeInTheDocument();
  });

  it("does not tilt with reduced motion", async () => {
    renderMap({ reduce_motion: true });
    await act(async () => {});
    const tilt = screen.getByTestId("muscle-flip").parentElement as HTMLElement;
    fireEvent.pointerMove(pathOf("chest"), { clientX: 5, clientY: 5 });
    await act(async () => {
      await new Promise((r) => requestAnimationFrame(() => r(null)));
    });
    expect(tilt.style.getPropertyValue("--tx")).not.toMatch(/[1-9]/);
  });

  it("keeps the figure out of the accessibility tree and has no axe violations", async () => {
    const { container } = renderMap();
    await screen.findByText("Needs attention");
    expect(figure()).toHaveAttribute("aria-hidden", "true");
    await expectNoAxeViolations(container);
  });
});
