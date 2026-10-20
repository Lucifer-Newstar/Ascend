import type { ExerciseAnalysis } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { axeViolations } from "../test/axe";
import { AddExerciseView } from "./AddExercise";

vi.mock("../api/client", () => ({ api: { analyzeExercise: vi.fn(), createExercise: vi.fn() } }));

const analysis = (over: Partial<ExerciseAnalysis> = {}): ExerciseAnalysis => ({
  name: "Banded Pallof Hold",
  proposal: {
    section: "gym", equipment: "band", measure: "hold", pattern: "isometric", difficulty: "intermediate",
    muscles: [{ muscle: "obliques", weight: 1 }, { muscle: "abs", weight: 0.5 }], rep_low: 10, rep_high: 30, met: null,
    instructions: [], aliases: [],
  },
  field_sources: { section: "rules", equipment: "rules", measure: "rules", pattern: "rules", difficulty: "rules", muscles: "local_ai", rep_low: "rules", rep_high: "rules" },
  attribution: [],
  matches: [{ id: 4, name: "Pallof Press", score: 0.78, via: "fuzzy", section: "gym", image: null }],
  duplicate_of: null,
  ai: { status: "ok", detail: "", model: "qwen3:4b", applied: ["muscles"] },
  online: { status: "off", detail: "", model: null, applied: [] },
  ...over,
});

function renderView(online = false) {
  const onCreated = vi.fn();
  const onOpenExisting = vi.fn();
  const utils = render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, online_lookup: online }} save={vi.fn()}>
      <ToastProvider>
        <AddExerciseView onBack={vi.fn()} onCreated={onCreated} onOpenExisting={onOpenExisting} />
      </ToastProvider>
    </PrefsProvider>,
  );
  return { ...utils, onCreated, onOpenExisting };
}

beforeEach(() => {
  vi.mocked(api.analyzeExercise).mockReset().mockResolvedValue(analysis());
  vi.mocked(api.createExercise).mockReset().mockResolvedValue({ id: 99, name: "Banded Pallof Hold" } as never);
});

describe("AddExerciseView", () => {
  it("proposes details with their sources and saves user edits as 'You'", async () => {
    const { container, onCreated } = renderView();
    expect(screen.queryByLabelText(/Also look up on wger/)).toBeNull(); // online lookup is off
    await userEvent.type(screen.getByLabelText("Exercise name"), "Banded Pallof Hold");
    await userEvent.click(screen.getByRole("button", { name: "Suggest details" }));
    expect(api.analyzeExercise).toHaveBeenCalledWith({ name: "Banded Pallof Hold", equipment: null, notes: "", online: false });
    expect(await screen.findByText(/Local AI filled in 1 field/)).toBeInTheDocument();
    expect(screen.getAllByText("Local AI").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Pallof Press · 78% match/ })).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Difficulty"), "beginner");
    await userEvent.selectOptions(screen.getByLabelText("Role of muscle 2"), "1");
    expect(await axeViolations(container)).toEqual([]);
    await userEvent.click(screen.getByRole("button", { name: "Add to my library" }));
    const body = vi.mocked(api.createExercise).mock.calls[0][0];
    expect(body.difficulty).toBe("beginner");
    expect(body.field_sources.difficulty).toBe("user");
    expect(body.field_sources.muscles).toBe("user");
    expect(body.field_sources.equipment).toBe("rules");
    expect(body.muscles).toEqual([{ muscle: "obliques", weight: 1 }, { muscle: "abs", weight: 1 }]);
    expect(onCreated).toHaveBeenCalledWith(99);
  });

  it("blocks duplicates and offers the existing exercise", async () => {
    vi.mocked(api.analyzeExercise).mockResolvedValue(analysis({ duplicate_of: { id: 3, name: "Pull-up", score: 1, via: "exact", section: "calisthenics", image: null } }));
    const { onOpenExisting } = renderView();
    await userEvent.type(screen.getByLabelText("Exercise name"), "pullups");
    await userEvent.click(screen.getByRole("button", { name: "Suggest details" }));
    expect(await screen.findByText(/is already in the library/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add to my library" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Open Pull-up" }));
    expect(onOpenExisting).toHaveBeenCalledWith(3);
  });

  it("asks wger only when allowed in Settings and ticked, and says when the model is missing", async () => {
    vi.mocked(api.analyzeExercise).mockResolvedValue(analysis({ ai: { status: "unavailable", detail: "", model: "qwen3:4b", applied: [] }, online: { status: "not_found", detail: "", model: null, applied: [] } }));
    renderView(true);
    await userEvent.type(screen.getByLabelText("Exercise name"), "Spoto press");
    await userEvent.click(screen.getByLabelText(/Also look up on wger.de/));
    await userEvent.click(screen.getByRole("button", { name: "Suggest details" }));
    expect(api.analyzeExercise).toHaveBeenCalledWith(expect.objectContaining({ online: true }));
    expect(await screen.findByText(/Local AI model not installed: rules only · wger.de has no exercise with this exact name/)).toBeInTheDocument();
  });
});
