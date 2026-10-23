import type { Settings } from "@ascend/shared";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { api } from "../api/client";
import { SettingsPage, sectionFromHash } from "./Settings";

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
    themes: vi.fn().mockResolvedValue([
      { key: "shadow", name: "Shadow", tagline: "Night dungeon", free: true, unlocked: true, requirement: "Free", progress: "" },
      { key: "dark", name: "Dark", tagline: "The original look, dark", free: true, unlocked: true, requirement: "Free", progress: "" },
      { key: "light", name: "Light", tagline: "The original look, light", free: true, unlocked: true, requirement: "Free", progress: "" },
      { key: "crimson", name: "Crimson Gate", tagline: "A red battlefield", free: false, unlocked: false, requirement: "Reach a 7-day streak", progress: "Best streak 2 of 7 days" },
    ]),
  },
}));

function setup(save: (p: Partial<Settings>) => Promise<Settings>, initial: Settings = DEFAULT_SETTINGS) {
  return render(
    <PrefsProvider initial={initial} save={save}>
      <ToastProvider>
        <SettingsPage onToggleAi={() => {}} onChanged={() => {}} />
      </ToastProvider>
    </PrefsProvider>,
  );
}

async function openSection(name: string) {
  const nav = await screen.findByRole("navigation", { name: "Settings sections" });
  await userEvent.click(within(nav).getByRole("button", { name }));
}

describe("SettingsPage", () => {
  beforeEach(() => {
    document.documentElement.removeAttribute("data-theme");
    window.history.replaceState(null, "", "#settings");
  });

  it("has six sections and shows one at a time", async () => {
    setup(vi.fn());
    const nav = await screen.findByRole("navigation", { name: "Settings sections" });
    expect(within(nav).getAllByRole("button").map((b) => b.textContent)).toEqual([
      "Profile", "Trainer", "Appearance & sound", "Units", "Data & backups", "Advanced",
    ]);
    expect(screen.getByRole("region", { name: "Profile" })).toBeInTheDocument();
    await openSection("Units");
    expect(screen.getByRole("region", { name: "Units" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Profile" })).toBeNull();
    expect(window.location.hash).toBe("#settings/units");
  });

  it("opens a section from the address", () => {
    expect(sectionFromHash("#settings/data")).toBe("data");
    expect(sectionFromHash("#settings")).toBe("profile");
    expect(sectionFromHash("#settings/nope")).toBe("profile");
  });

  it("picks a theme, shows locked ones with what earns them, and applies it to <html>", async () => {
    const save = vi.fn(async (p: Partial<Settings>) => ({ ...DEFAULT_SETTINGS, ...p }));
    setup(save);
    await openSection("Appearance & sound");
    const crimson = await screen.findByTestId("theme-crimson");
    expect(crimson).toBeDisabled();
    expect(crimson).toHaveTextContent("Reach a 7-day streak");
    expect(crimson).toHaveTextContent("Best streak 2 of 7 days");
    expect(document.documentElement.dataset.theme).toBe("shadow");
    await userEvent.click(screen.getByTestId("theme-light"));
    expect(save).toHaveBeenCalledWith({ theme: "light" });
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
  });

  it("dims or turns off the background art on a v1.2 theme", async () => {
    const save = vi.fn(async (p: Partial<Settings>) => ({ ...DEFAULT_SETTINGS, ...p }));
    setup(save);
    await openSection("Appearance & sound");
    await userEvent.click(await screen.findByLabelText("Dim"));
    expect(save).toHaveBeenCalledWith({ background_art: "dim" });
    await waitFor(() => expect(document.documentElement.dataset.art).toBe("dim"));
  });

  it("switches units and training days", async () => {
    const save = vi.fn(async (p: Partial<Settings>) => ({ ...DEFAULT_SETTINGS, ...p }));
    setup(save);
    await openSection("Units");
    await userEvent.click(await screen.findByLabelText("lb · in · mi"));
    expect(save).toHaveBeenCalledWith({ units: "imperial" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: /training days/i }), "5");
    expect(save).toHaveBeenCalledWith({ sessions_per_week: 5 });
  });

  it("asks for consent before turning on online research (Advanced)", async () => {
    const save = vi.fn(async (p: Partial<Settings>) => ({ ...DEFAULT_SETTINGS, ...p }));
    setup(save);
    await openSection("Advanced");
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
    await openSection("Advanced");
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
    await openSection("Appearance & sound");
    const toggle = await screen.findByRole("checkbox", { name: /reduce motion/i });
    expect(toggle).not.toBeChecked();
    expect(document.documentElement.dataset.motion).toBe("full");
    await userEvent.click(toggle);
    expect(save).toHaveBeenCalledWith({ reduce_motion: true });
    await waitFor(() => expect(document.documentElement.dataset.motion).toBe("reduce"));
    expect(toggle).toBeChecked();
  });

  it("keeps the old value when saving fails", async () => {
    const save = vi.fn().mockRejectedValue(new Error("engine offline"));
    setup(save);
    await openSection("Units");
    await userEvent.click(await screen.findByLabelText("lb · in · mi"));
    expect(await screen.findByText("engine offline")).toBeInTheDocument();
    expect(screen.getByLabelText("kg · cm · km")).toBeChecked();
  });

  it("has one trainer voice switch, in the Trainer section", async () => {
    setup(vi.fn());
    await openSection("Trainer");
    expect(await screen.findAllByRole("checkbox", { name: /trainer voice/i })).toHaveLength(1);
  });

  it("keeps the formula numbers behind Details", async () => {
    setup(async (p) => ({ ...DEFAULT_SETTINGS, ...p }));
    expect(await screen.findByText(/This week it follows your weigh-ins and meals: 2,790 kcal/)).toBeInTheDocument();
    expect(screen.getByText("Details")).toBeInTheDocument();
    expect(screen.queryByText(/tdee-v1/)).toBeNull(); // no version tags
  });

  it("has no axe violations", async () => {
    const { container } = setup(vi.fn());
    await screen.findByRole("heading", { name: "Your body & goal" });
    await expectNoAxeViolations(container);
  });
});
