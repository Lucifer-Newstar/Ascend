import type { Settings } from "@ascend/shared";
import { act, render, renderHook, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CountUp, easeOutCubic, useReducedMotion } from "./motion";
import { DEFAULT_SETTINGS, PrefsProvider } from "./prefs";

vi.mock("../api/client", () => ({ api: { updateSettings: vi.fn() } }));

function mockOsReducedMotion(matches: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: query.includes("reduced-motion") ? matches : false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

const withPrefs = (settings: Partial<Settings>) =>
  function Wrapper({ children }: { children: ReactNode }) {
    return <PrefsProvider initial={{ ...DEFAULT_SETTINGS, ...settings }} save={vi.fn()}>{children}</PrefsProvider>;
  };

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("useReducedMotion", () => {
  it("is off by default", () => {
    const { result } = renderHook(() => useReducedMotion(), { wrapper: withPrefs({}) });
    expect(result.current).toBe(false);
  });

  it("follows the in-app Reduce motion toggle", () => {
    const { result } = renderHook(() => useReducedMotion(), { wrapper: withPrefs({ reduce_motion: true }) });
    expect(result.current).toBe(true);
    expect(document.documentElement.dataset.motion).toBe("reduce");
  });

  it("follows the OS prefers-reduced-motion setting even with the toggle off", () => {
    mockOsReducedMotion(true);
    const { result } = renderHook(() => useReducedMotion(), { wrapper: withPrefs({ reduce_motion: false }) });
    expect(result.current).toBe(true);
  });

  it("works outside the prefs provider (OS setting only)", () => {
    const { result } = renderHook(() => useReducedMotion());
    expect(result.current).toBe(false);
  });
});

describe("CountUp", () => {
  it("shows the final value at once with reduced motion", () => {
    render(<CountUp value={1234} />, { wrapper: withPrefs({ reduce_motion: true }) });
    expect(screen.getByTestId("count-up")).toHaveTextContent("1,234");
  });

  it("counts up from 0 to the value otherwise, and announces only the final value", async () => {
    vi.useFakeTimers({ toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance"] });
    render(<CountUp value={500} duration={400} />, { wrapper: withPrefs({}) });
    const ticking = screen.getByTestId("count-up");
    expect(ticking).toHaveAttribute("aria-hidden", "true");
    expect(ticking).toHaveTextContent("0");
    expect(screen.getByText("500", { selector: ".sr-only" })).toBeInTheDocument();
    await act(async () => {
      vi.advanceTimersByTime(200);
    });
    const mid = Number(ticking.textContent);
    expect(mid).toBeGreaterThan(0);
    expect(mid).toBeLessThan(500);
    await act(async () => {
      vi.advanceTimersByTime(400);
    });
    expect(ticking).toHaveTextContent("500");
  });

  it("eases out (fast start, gentle finish)", () => {
    expect(easeOutCubic(0)).toBe(0);
    expect(easeOutCubic(1)).toBe(1);
    expect(easeOutCubic(0.5)).toBeGreaterThan(0.5);
  });
});
