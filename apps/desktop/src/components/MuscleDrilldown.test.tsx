import type { MuscleHistory } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { MuscleDrilldown } from "./MuscleDrilldown";

vi.mock("../api/client", () => ({ api: { muscleHistory: vi.fn() } }));

const history: MuscleHistory = {
  code: "quads", label: "Quads", days: 7, status: "optimal", es_7d: 12, target_low: 10, target_high: 20,
  readiness: 0.8, ready_at: null, daily: [], contributing_sets: [], suggestion: null, formula_version: "load-1.1.0",
};

describe("MuscleDrilldown", () => {
  it("takes focus when it opens and closes on Escape", async () => {
    vi.mocked(api.muscleHistory).mockResolvedValue(history);
    const onClose = vi.fn();
    render(<MuscleDrilldown code="quads" onClose={onClose} />);
    expect(await screen.findByRole("heading", { name: "Quads" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Muscle details" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("asks for a new range when the day switch changes", async () => {
    vi.mocked(api.muscleHistory).mockResolvedValue(history);
    render(<MuscleDrilldown code="quads" onClose={vi.fn()} />);
    await screen.findByRole("heading", { name: "Quads" });
    await userEvent.click(screen.getByLabelText("30 days"));
    expect(api.muscleHistory).toHaveBeenLastCalledWith("quads", 30);
  });
});
