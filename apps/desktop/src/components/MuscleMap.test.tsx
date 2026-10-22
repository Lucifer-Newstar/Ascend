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
  m("pec_major_sternal", "Lower chest", "pec_major_sternal", { status: "recovering", es_7d: 9, readiness: 0.6, ready_at: "2026-10-21T08:00:00" }),
  m("biceps_long", "Biceps", "biceps_long", { status: "optimal", es_7d: 12, readiness: 0.98 }),
  m("vastus_lateralis", "Vastus lateralis", "vastus_lateralis", { status: "no_data" }),
  m("latissimus_dorsi", "Lats", "latissimus_dorsi", { status: "under", es_7d: 3 }),
];
const activity = (days: number): MuscleActivity[] => [
  { key: "pec_major_sternal", sets: days === 30 ? 30 : 9, volume_kg: 4200, last_trained: new Date().toISOString() },
  { key: "biceps_long", sets: days === 30 ? 40 : 12, volume_kg: 1800, last_trained: "2026-10-15T09:00:00" },
  { key: "vastus_lateralis", sets: 0, volume_kg: 0, last_trained: null },
  { key: "latissimus_dorsi", sets: 3, volume_kg: 900, last_trained: "2026-10-17T09:00:00" },
];

function renderMap(settings: Partial<Settings> = {}) {
  return render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, ...settings }} save={vi.fn()}>
      <MuscleMap muscles={muscles} />
    </PrefsProvider>,
  );
}

const figure = () => screen.getByTestId("muscle-figure");
const pathOf = (slug: string) => figure().querySelector(`path[data-key="${slug}"]`) as SVGPathElement;

describe("MuscleMap", () => {
  beforeEach(() => {
    vi.mocked(api.muscleActivity).mockImplementation(async (days: number) => activity(days));
    vi.mocked(api.muscleHistory).mockResolvedValue({
      code: "pec_major_sternal", label: "Lower chest", days: 7, status: "recovering", es_7d: 9, target_low: 10, target_high: 20,
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
    fireEvent.pointerMove(pathOf("pec_major_sternal"), { clientX: 40, clientY: 80 });
    const tip = await screen.findByTestId("muscle-tooltip");
    expect(within(tip).getByText("Lower chest")).toBeInTheDocument();
    expect(within(tip).getByText("Recovering")).toBeInTheDocument();
    expect(within(tip).getByText("4,200 kg")).toBeInTheDocument();
    expect(within(tip).getByText("today")).toBeInTheDocument();
    // The hovered muscle is lifted by a generated rule scoped to this figure.
    expect(figure().querySelector("style")?.textContent).toMatch(/path\[data-key="pec_major_sternal"\] \{ transform: scale\(1\.04\)/);
    fireEvent.pointerLeave(figure());
    await waitFor(() => expect(screen.queryByTestId("muscle-tooltip")).toBeNull());
  });

  it("outlines fatigued muscles and pulses the ones ready to train", async () => {
    renderMap();
    await screen.findByText("Ready again:", { exact: false });
    const css = figure().querySelector("style")?.textContent ?? "";
    expect(css).toMatch(/path\[data-key="pec_major_sternal"\] \{ stroke: color-mix/);
    expect(css).not.toMatch(/drop-shadow/);
    expect(css).toMatch(/path\[data-key="biceps_long"\][^{]*\{ animation: asc-muscle-pulse/);
    expect(css).not.toMatch(/path\[data-key="pec_major_sternal"\][^{]*\{ animation/);
    expect(screen.getByText("Ready again:").parentElement).toHaveTextContent("Biceps, Lats");
  });

  it("opens the drill-down when a muscle is clicked", async () => {
    renderMap();
    await act(async () => {});
    fireEvent.click(pathOf("pec_major_sternal"));
    const panel = await screen.findByRole("region", { name: "Muscle details" });
    expect(panel).toHaveClass("panel-in");
    expect(api.muscleHistory).toHaveBeenCalledWith("pec_major_sternal", 7);
  });

  it("recolours by volume for the chosen range", async () => {
    renderMap();
    await userEvent.click(screen.getByLabelText("Volume"));
    await waitFor(() => expect(api.muscleActivity).toHaveBeenLastCalledWith(7));
    await userEvent.click(screen.getByLabelText("30 days"));
    await waitFor(() => expect(api.muscleActivity).toHaveBeenLastCalledWith(30));
    // Biceps carry the most sets in 30 days, so they take the deepest colour; quads are untrained.
    await waitFor(() => expect(pathOf("biceps_long").getAttribute("fill")).toBe("#5193a6"));
    expect(pathOf("vastus_lateralis").getAttribute("fill")).not.toBe("#5193a6");
    expect(screen.getByText(/More sets · last 30 days/)).toBeInTheDocument();
  });

  it("does not tilt with reduced motion", async () => {
    renderMap({ reduce_motion: true });
    await act(async () => {});
    const tilt = screen.getByTestId("muscle-flip").parentElement as HTMLElement;
    fireEvent.pointerMove(pathOf("pec_major_sternal"), { clientX: 5, clientY: 5 });
    await act(async () => {
      await new Promise((r) => requestAnimationFrame(() => r(null)));
    });
    expect(tilt.style.getPropertyValue("--tx")).not.toMatch(/[1-9]/);
  });

  it("shows the deep layer on request", async () => {
    renderMap();
    await act(async () => {});
    expect(figure().querySelector('path[data-key="pec_minor"]')).toBeNull();
    await userEvent.click(screen.getByLabelText("Deep"));
    expect(figure()).toHaveAttribute("data-layer", "deep");
    expect(figure().querySelector('path[data-key="pec_minor"]')).not.toBeNull();
  });

  it("keeps the figure out of the accessibility tree and has no axe violations", async () => {
    const { container } = renderMap();
    await screen.findByText("Needs attention");
    expect(figure()).toHaveAttribute("aria-hidden", "true");
    await expectNoAxeViolations(container);
  });
});
