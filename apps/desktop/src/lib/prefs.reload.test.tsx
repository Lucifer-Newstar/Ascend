import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DEFAULT_SETTINGS, PrefsProvider, usePrefs } from "./prefs";

function Show() {
  const { settings, reload } = usePrefs();
  return (
    <>
      <p data-testid="units">{settings.units}</p>
      <button type="button" onClick={() => void reload()}>Reload</button>
    </>
  );
}

describe("prefs reload (v1.3)", () => {
  it("reads the settings again after the trainer changed one", async () => {
    const load = vi.fn().mockResolvedValue({ ...DEFAULT_SETTINGS, units: "imperial" });
    render(
      <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()} load={load}>
        <Show />
      </PrefsProvider>,
    );
    expect(screen.getByTestId("units")).toHaveTextContent("metric");
    await act(async () => screen.getByRole("button", { name: "Reload" }).click());
    expect(screen.getByTestId("units")).toHaveTextContent("imperial");
  });

  it("keeps the current settings when the engine can't be read", async () => {
    const load = vi.fn().mockRejectedValue(new Error("offline"));
    render(
      <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()} load={load}>
        <Show />
      </PrefsProvider>,
    );
    await act(async () => screen.getByRole("button", { name: "Reload" }).click());
    expect(screen.getByTestId("units")).toHaveTextContent("metric");
  });
});
