import type { MuscleHistory, MuscleRecovery, RecoveryGroup } from "@ascend/shared";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { MuscleDrilldown, RecoveryYou } from "./MuscleDrilldown";

vi.mock("../api/client", () => ({
  api: { muscleHistory: vi.fn(), updateSettings: vi.fn(), recovery: vi.fn(() => Promise.reject(new Error("not needed"))), recoveryExplanation: vi.fn(() => Promise.reject(new Error("not needed"))) },
}));

const history: MuscleHistory = {
  code: "vastus_lateralis", label: "Quads", days: 7, status: "optimal", es_7d: 12, target_low: 10, target_high: 20,
  readiness: 0.8, ready_at: null, daily: [], contributing_sets: [], suggestion: null, formula_version: "load-1.1.0",
};

describe("MuscleDrilldown", () => {
  it("takes focus when it opens and closes on Escape", async () => {
    vi.mocked(api.muscleHistory).mockResolvedValue(history);
    const onClose = vi.fn();
    render(<MuscleDrilldown code="vastus_lateralis" onClose={onClose} />);
    expect(await screen.findByRole("heading", { name: "Quads" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Muscle details" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    // Plays the closing animation first, then unmounts (once, even on a second Escape).
    expect(screen.getByRole("region", { name: "Muscle details" })).toHaveClass("panel-out");
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  });

  it("opens with the panel-in animation", async () => {
    vi.mocked(api.muscleHistory).mockResolvedValue(history);
    render(<MuscleDrilldown code="vastus_lateralis" onClose={vi.fn()} />);
    expect(await screen.findByRole("region", { name: "Muscle details" })).toHaveClass("panel-in");
  });

  it("closes at once with reduced motion", async () => {
    vi.mocked(api.muscleHistory).mockResolvedValue(history);
    const onClose = vi.fn();
    render(
      <PrefsProvider initial={{ ...DEFAULT_SETTINGS, reduce_motion: true }} save={vi.fn()}>
        <MuscleDrilldown code="vastus_lateralis" onClose={onClose} />
      </PrefsProvider>,
    );
    await screen.findByRole("heading", { name: "Quads" });
    await userEvent.click(screen.getByRole("button", { name: "Close muscle details" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("asks for a new range when the day switch changes", async () => {
    vi.mocked(api.muscleHistory).mockResolvedValue(history);
    render(<MuscleDrilldown code="vastus_lateralis" onClose={vi.fn()} />);
    await screen.findByRole("heading", { name: "Quads" });
    await userEvent.click(screen.getByLabelText("30 days"));
    expect(api.muscleHistory).toHaveBeenLastCalledWith("vastus_lateralis", 30);
  });
});

describe("RecoveryYou", () => {
  const muscle: MuscleRecovery = {
    key: "vastus_lateralis", label: "Quads", group: "Legs", status: "recovering", readiness: 0.55, readiness_population: 0.63,
    fatigue: 5.4, capacity: 12, half_life_h: 57.6, prior_half_life_h: 48, k: 1.2, modifier: 1.1, es_7d: 8,
    ready_at: null, last_trained: null, top_sets: [],
    why: { formula: "readiness = 1 - min(1, M x F / C)", inputs: { fatigue_F: 5.4, capacity_C: 12, personal_k: 1.2 } },
  };
  const group: RecoveryGroup = { group: "Legs", k: 1.2, k_low: 1.05, k_high: 1.38, n: 9, personal: true, alpha: 0.12, updated_at: null };

  it("compares you with the population and explains the number", async () => {
    render(<RecoveryYou m={muscle} g={group} />);
    expect(screen.getByTestId("recovery-you")).toHaveTextContent("you 55% · population 63%");
    expect(screen.getByText(/recover slower than the population: half-life 57.6 h instead of 48 h/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Why is Quads readiness 55%?" }));
    expect(screen.getByTestId("why-panel")).toHaveTextContent("Your recovery factor, k1.2");
  });

  it("does not claim slower or faster while the interval includes the population value", () => {
    render(<RecoveryYou m={{ ...muscle, k: 1.03, half_life_h: 49.4 }} g={{ ...group, k: 1.03, k_low: 0.7, k_high: 1.45 }} />);
    expect(screen.getByText(/recover about like the population so far: half-life 49.4 h against 48 h/)).toBeInTheDocument();
    expect(screen.queryByText(/recover slower/)).not.toBeInTheDocument();
  });

  it("says when the population value is still in use", () => {
    render(<RecoveryYou m={{ ...muscle, k: 1, half_life_h: 48 }} g={{ ...group, k: 1, personal: false, n: 2 }} />);
    expect(screen.getByText(/Population recovery for Legs until your sessions show a clear difference \(2 usable so far\)/)).toBeInTheDocument();
  });
});
