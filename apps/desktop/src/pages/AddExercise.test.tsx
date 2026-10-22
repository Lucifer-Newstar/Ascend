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
    muscles: [{ muscle: "external_obliques", weight: 1 }, { muscle: "rectus_abdominis", weight: 0.5 }], rep_low: 10, rep_high: 30, met: null,
    instructions: [], aliases: [],
  },
  field_sources: { section: "rules", equipment: "rules", measure: "rules", pattern: "rules", difficulty: "rules", muscles: "local_ai", rep_low: "rules", rep_high: "rules" },
  attribution: [],
  matches: [{ id: 4, name: "Pallof Press", score: 0.78, via: "fuzzy", section: "gym", image: null }],
  duplicate_of: null,
  ai: { status: "ok", detail: "", model: "qwen3:4b", applied: ["muscles"] },
  online: { status: "off", detail: "", model: null, applied: [] },
  confidence: { section: "medium", equipment: "medium", measure: "medium", pattern: "medium", muscles: "medium", difficulty: "low", instructions: "low" },
  insufficient: [],
  offline: null,
  offline_sources: {},
  research: null,
  ...over,
});

const researched = (): ExerciseAnalysis => {
  const base = analysis({ name: "Spoto Press" });
  return {
    ...base,
    proposal: { ...base.proposal, equipment: "barbell", measure: "reps", pattern: "push", rep_low: 6, rep_high: 12, muscles: [{ muscle: "pec_major_sternal", weight: 1 }, { muscle: "triceps_lateral", weight: 0.5 }], instructions: ["Lower the bar.", "Press up."] },
    field_sources: { ...base.field_sources, equipment: "wger", muscles: "wger", instructions: "wger" },
    confidence: { ...base.confidence, equipment: "high", muscles: "high", instructions: "high" },
    attribution: [{ source: "wger", title: "wger exercise #77: Spoto Press", url: "https://wger.de/en/exercise/77/view/", license: "CC-BY-SA 4" }],
    online: { status: "ok", detail: "", model: null, applied: ["muscles", "equipment", "instructions"] },
    offline: { ...base.proposal, equipment: "other", measure: "reps", pattern: "push", rep_low: 6, rep_high: 12 },
    offline_sources: { equipment: "rules", muscles: "rules" },
    research: {
      query: "Spoto Press", consent: "once", outcome: "ok", summary: "", summary_url: "",
      calls: [{ source: "wger", url: "https://wger.de/api/v2/exercise-translation/?name=Spoto+Press", status: "ok" }, { source: "wikipedia", url: "https://en.wikipedia.org/api/rest_v1/page/summary/Spoto_press", status: "not_found" }],
      fields: [
        { field: "equipment", label: "Equipment", value: "barbell", source: "wger", url: "https://wger.de/en/exercise/77/view/", offline_value: "other", offline_source: "rules", conflict: true },
        { field: "muscles", label: "Muscles", value: "lower_chest (+ triceps)", source: "wger", url: "https://wger.de/en/exercise/77/view/", offline_value: "obliques (+ abs)", offline_source: "rules", conflict: true },
      ],
    },
  };
};

function renderView(online = false, save = vi.fn(async (patch) => ({ ...DEFAULT_SETTINGS, online_lookup: online, ...patch }))) {
  const onCreated = vi.fn();
  const onOpenExisting = vi.fn();
  const utils = render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, online_lookup: online }} save={save}>
      <ToastProvider>
        <AddExerciseView onBack={vi.fn()} onCreated={onCreated} onOpenExisting={onOpenExisting} />
      </ToastProvider>
    </PrefsProvider>,
  );
  return { ...utils, onCreated, onOpenExisting, save };
}

beforeEach(() => {
  vi.mocked(api.analyzeExercise).mockReset().mockResolvedValue(analysis());
  vi.mocked(api.createExercise).mockReset().mockResolvedValue({ id: 99, name: "Banded Pallof Hold" } as never);
});

describe("AddExerciseView", () => {
  it("proposes details with their sources and saves user edits as 'You'", async () => {
    const { container, onCreated } = renderView();
    expect(screen.getByText(/Online research is off/)).toBeInTheDocument();
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
    expect(body.muscles).toEqual([{ muscle: "external_obliques", weight: 1 }, { muscle: "rectus_abdominis", weight: 1 }]);
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

  it("says when offline data is not enough and offers Allow once / Always / No", async () => {
    const weak = analysis({ insufficient: ["equipment", "muscles"], confidence: { ...analysis().confidence, equipment: "low", muscles: "low" }, ai: { status: "unavailable", detail: "", model: "qwen3:4b", applied: [] } });
    vi.mocked(api.analyzeExercise).mockResolvedValueOnce(weak).mockResolvedValueOnce(researched());
    const { container } = renderView(false);
    expect(screen.getByText(/Online research is off/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Exercise name"), "Spoto press");
    await userEvent.click(screen.getByRole("button", { name: "Suggest details" }));
    expect(api.analyzeExercise).toHaveBeenLastCalledWith({ name: "Spoto press", equipment: null, notes: "", online: false });
    expect(await screen.findByText(/Not enough offline data for/)).toBeInTheDocument();
    expect(screen.getByText(/could not pin down its equipment, muscles/)).toBeInTheDocument();
    expect(screen.getAllByText("Low").length).toBeGreaterThanOrEqual(2);
    expect(await axeViolations(container)).toEqual([]);
    await userEvent.click(screen.getByRole("button", { name: "Allow once" }));
    expect(api.analyzeExercise).toHaveBeenLastCalledWith({ name: "Spoto press", equipment: null, notes: "", online: true, allow_once: true });
    expect(await screen.findByRole("heading", { name: "Research report" })).toBeInTheDocument();
    expect(screen.getByText(/allowed once/)).toBeInTheDocument();
    expect(screen.getByText(/wger.de: found/)).toBeInTheDocument();
    expect(screen.getByText(/Wikipedia: nothing under this name/)).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("Always turns the setting on before researching; No dismisses the offer", async () => {
    const weak = analysis({ insufficient: ["muscles"], confidence: { ...analysis().confidence, muscles: "low" } });
    vi.mocked(api.analyzeExercise).mockResolvedValue(weak);
    const { save } = renderView(false);
    await userEvent.type(screen.getByLabelText("Exercise name"), "Spoto press");
    await userEvent.click(screen.getByRole("button", { name: "Suggest details" }));
    await userEvent.click(await screen.findByRole("button", { name: "No" }));
    expect(screen.queryByText(/Not enough offline data/)).toBeNull();
    expect(api.analyzeExercise).toHaveBeenCalledTimes(1);
    expect(save).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Check again" }));
    await userEvent.click(await screen.findByRole("button", { name: "Always (turns on Online research)" }));
    expect(save).toHaveBeenCalledWith({ online_lookup: true });
    expect(api.analyzeExercise).toHaveBeenLastCalledWith(expect.objectContaining({ online: true }));
    expect(vi.mocked(api.analyzeExercise).mock.lastCall?.[0]).not.toHaveProperty("allow_once");
  });

  it("lets the user keep the offline guess over a research finding before saving", async () => {
    vi.mocked(api.analyzeExercise).mockResolvedValue(researched());
    renderView(true);
    await userEvent.type(screen.getByLabelText("Exercise name"), "Spoto press");
    await userEvent.click(screen.getByRole("button", { name: "Suggest details" }));
    expect(await screen.findByRole("heading", { name: "Research report" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "wger.de" })[0]).toHaveAttribute("href", "https://wger.de/en/exercise/77/view/");
    await userEvent.click(screen.getByRole("button", { name: "Keep offline equipment" }));
    expect(screen.getByText("kept offline")).toBeInTheDocument();
    expect(api.createExercise).not.toHaveBeenCalled(); // nothing is saved silently
    await userEvent.click(screen.getByRole("button", { name: "Add to my library" }));
    const body = vi.mocked(api.createExercise).mock.calls[0][0];
    expect(body.equipment).toBe("other");
    expect(body.field_sources.equipment).toBe("rules");
    expect(body.field_sources.muscles).toBe("wger");
    expect(body.attribution[0].license).toBe("CC-BY-SA 4");
  });

  it("with the setting on offers a lookup on demand and says when the model is missing", async () => {
    vi.mocked(api.analyzeExercise).mockResolvedValue(analysis({ ai: { status: "unavailable", detail: "", model: "qwen3:4b", applied: [] }, online: { status: "not_requested", detail: "", model: null, applied: [] } }));
    renderView(true);
    expect(screen.getByText(/Online research is on/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Exercise name"), "Zercher squat");
    await userEvent.click(screen.getByRole("button", { name: "Suggest details" }));
    expect(await screen.findByText(/Local AI model not installed: rules only/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Look it up online" }));
    expect(api.analyzeExercise).toHaveBeenLastCalledWith(expect.objectContaining({ online: true }));
  });
});
