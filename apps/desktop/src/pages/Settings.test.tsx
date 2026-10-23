import type { Settings } from "@ascend/shared";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { api } from "../api/client";
import { SettingsPage } from "./Settings";

vi.mock("../api/client", () => ({
  api: {
    profile: vi.fn().mockResolvedValue({
      name: "Navin", age: 21, sex: "male", height_cm: 175, weight_kg: 70, goal: "bulk", activity: "moderate",
      target_weight_kg: null,
      energy: { bmr: 1700, tdee: 2600, kcal_target: 2900, protein_target_g: 140, formula_version: "tdee-v1", is_estimate: true },
    }),
    updateSettings: vi.fn(),
    onlineLog: vi.fn().mockResolvedValue([]),
    backups: vi.fn().mockResolvedValue([]),
    clearOnlineLog: vi.fn().mockResolvedValue(undefined),
    tdee: vi.fn().mockResolvedValue({ algo_version: "tdee-v1", target_source: "adaptive", target_kcal: 2790 }),
    aiSetup: vi.fn().mockRejectedValue(new Error("engine offline")),
  },
}));

function setup(save: (p: Partial<Settings>) => Promise<Settings>, onOpenData = () => {}) {
  return render(
    <PrefsProvider initial={DEFAULT_SETTINGS} save={save}>
      <ToastProvider>
        <SettingsPage onToggleAi={() => {}} onChanged={() => {}} onOpenData={onOpenData} />
      </ToastProvider>
    </PrefsProvider>,
  );
}

describe("SettingsPage", () => {
  beforeEach(() => {
    document.documentElement.removeAttribute("data-theme");
  });

  it("saves the light theme and applies it to <html>", async () => {
    const save = vi.fn(async (p: Partial<Settings>) => ({ ...DEFAULT_SETTINGS, ...p }));
    setup(save);
    await screen.findByRole("heading", { name: "Appearance" });
    expect(document.documentElement.dataset.theme).toBe("dark");
    await userEvent.click(screen.getByLabelText("Light"));
    expect(save).toHaveBeenCalledWith({ theme: "light" });
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
    expect(screen.getByLabelText("Light")).toBeChecked();
  });

  it("switches units and training days", async () => {
    const save = vi.fn(async (p: Partial<Settings>) => ({ ...DEFAULT_SETTINGS, ...p }));
    setup(save);
    await userEvent.click(await screen.findByLabelText("lb · in · mi"));
    expect(save).toHaveBeenCalledWith({ units: "imperial" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: /training days/i }), "5");
    expect(save).toHaveBeenCalledWith({ sessions_per_week: 5 });
  });

  it("asks for consent before turning on online research", async () => {
    const save = vi.fn(async (p: Partial<Settings>) => ({ ...DEFAULT_SETTINGS, ...p }));
    setup(save);
    const toggle = await screen.findByRole("checkbox", { name: /research exercises you add on wger.de and wikipedia/i });
    expect(toggle).not.toBeChecked();
    await userEvent.click(toggle);
    expect(save).not.toHaveBeenCalled();
    const ask = screen.getByRole("group", { name: "Allow online research?" });
    expect(ask).toHaveTextContent("only the exercise name");
    await userEvent.click(within(ask).getByRole("button", { name: "Cancel" }));
    expect(toggle).not.toBeChecked();
    await userEvent.click(toggle);
    await userEvent.click(screen.getByRole("button", { name: "Allow" }));
    expect(save).toHaveBeenCalledWith({ online_lookup: true });
    await waitFor(() => expect(toggle).toBeChecked());
    await userEvent.click(toggle);
    expect(save).toHaveBeenLastCalledWith({ online_lookup: false });
  });

  it("shows the local lookup log and clears it", async () => {
    vi.mocked(api.onlineLog).mockResolvedValueOnce([
      { id: 2, at: "2026-10-20T18:00:00", query: "spoto press", consent: "once", outcome: "ok",
        sources: [{ source: "wger", url: "https://wger.de/api/v2/exercise-translation/?name=spoto+press", status: "not_found" }, { source: "wger", url: "https://wger.de/api/v2/exercise-translation/?name=Spoto+Press", status: "ok" }, { source: "wikipedia", url: "https://en.wikipedia.org/api/rest_v1/page/summary/Spoto_press", status: "not_found" }] },
    ]).mockResolvedValueOnce([]);
    const { container } = setup(vi.fn(async (p: Partial<Settings>) => ({ ...DEFAULT_SETTINGS, ...p })));
    expect(await screen.findByText("“spoto press”")).toBeInTheDocument();
    expect(screen.getByText(/wger.de, Wikipedia/)).toBeInTheDocument();
    expect(screen.getByText("found")).toBeInTheDocument();
    await expectNoAxeViolations(container);
    await userEvent.click(screen.getByRole("button", { name: "Clear log" }));
    expect(api.clearOnlineLog).toHaveBeenCalled();
    expect(await screen.findByText("No online lookups yet.")).toBeInTheDocument();
  });

  it("turns on Reduce motion and mirrors it onto <html data-motion>", async () => {
    const save = vi.fn(async (p: Partial<Settings>) => ({ ...DEFAULT_SETTINGS, ...p }));
    setup(save);
    const toggle = await screen.findByRole("checkbox", { name: /reduce motion/i });
    expect(toggle).not.toBeChecked();
    expect(document.documentElement.dataset.motion).toBe("full");
    await userEvent.click(toggle);
    expect(save).toHaveBeenCalledWith({ reduce_motion: true });
    await waitFor(() => expect(document.documentElement.dataset.motion).toBe("reduce"));
    expect(toggle).toBeChecked();
  });

  it("groups appearance apart from units and training", async () => {
    setup(vi.fn());
    const appearance = await screen.findByRole("region", { name: "Appearance" });
    expect(within(appearance).getByRole("group", { name: "Theme" })).toBeInTheDocument();
    expect(within(appearance).getByRole("checkbox", { name: /reduce motion/i })).toBeInTheDocument();
    const units = screen.getByRole("region", { name: "Units & training" });
    expect(within(units).getByRole("group", { name: "Units" })).toBeInTheDocument();
    expect(within(units).getByRole("combobox", { name: /training days/i })).toBeInTheDocument();
  });

  it("keeps the old value when saving fails", async () => {
    const save = vi.fn().mockRejectedValue(new Error("engine offline"));
    setup(save);
    await userEvent.click(await screen.findByLabelText("Light"));
    expect(await screen.findByText("engine offline")).toBeInTheDocument();
    expect(screen.getByLabelText("Dark")).toBeChecked();
  });

  it("links to the Import & export page", async () => {
    const open = vi.fn();
    setup(vi.fn(), open);
    await userEvent.click(await screen.findByRole("button", { name: /open import & export/i }));
    expect(open).toHaveBeenCalled();
  });

  it("has no axe violations", async () => {
    const { container } = setup(vi.fn());
    await screen.findByRole("heading", { name: "Appearance" });
    await expectNoAxeViolations(container);
  });

  it("indexes every section and jumps to one", async () => {
    setup(vi.fn());
    const nav = await screen.findByRole("navigation", { name: "Settings sections" });
    await userEvent.click(within(nav).getByRole("button", { name: "Keyboard shortcuts" }));
    expect(screen.getByRole("heading", { name: "Keyboard shortcuts" })).toHaveFocus();
  });

  it("names this week's adaptive target beside the formula estimate", async () => {
    setup(async (p) => ({ ...DEFAULT_SETTINGS, ...p }));
    expect(await screen.findByText(/this week's adaptive target 2,790 kcal \(tdee-v1/)).toBeInTheDocument();
  });
});
