import type { Settings, StreakInfo, XpInfo } from "@ascend/shared";
import { act, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { XpBar, resetXpMemory } from "./XpBar";

vi.mock("../api/client", () => ({ api: { updateSettings: vi.fn() } }));

const xp = (over: Partial<XpInfo> = {}): XpInfo => ({
  total: 1200, today: 40, level: 4, xp_into_level: 200, xp_for_next: 800, rank: "D", rank_title: "Apprentice",
  daily_cap: 600, formula_version: "xp-v1", ...over,
});
const streak = (current: number): StreakInfo => ({ current, best: 9, freezes_held: 1, freezes_used: 0, active_today: true });

const wrap = (settings: Partial<Settings> = {}) =>
  function W({ children }: { children: ReactNode }) {
    return <PrefsProvider initial={{ ...DEFAULT_SETTINGS, ...settings }} save={vi.fn()}>{children}</PrefsProvider>;
  };

const fillOf = () => (screen.getByTestId("xp-fill") as HTMLElement).style.transform;
const nextFrame = () => act(() => new Promise<void>((r) => requestAnimationFrame(() => r())));

describe("XpBar", () => {
  beforeEach(() => resetXpMemory());

  it("slides the fill in from empty with transform (no width animation)", async () => {
    render(<XpBar xp={xp()} streak={streak(3)} />, { wrapper: wrap() });
    expect(fillOf()).toBe("translateX(-100%)");
    await nextFrame();
    expect(fillOf()).toBe("translateX(-75%)"); // 200 / 800
  });

  it("starts at the real value with reduced motion", () => {
    render(<XpBar xp={xp()} streak={streak(3)} />, { wrapper: wrap({ reduce_motion: true }) });
    expect(fillOf()).toBe("translateX(-75%)");
    expect(screen.getAllByTestId("count-up")[0]).toHaveTextContent("200");
  });

  it("celebrates a level gained since the last visit, once", async () => {
    const first = render(<XpBar xp={xp()} streak={streak(3)} />, { wrapper: wrap() });
    expect(screen.queryByText("Level up!")).toBeNull();
    first.unmount();
    render(<XpBar xp={xp({ level: 5, xp_into_level: 40, total: 1840 })} streak={streak(3)} />, { wrapper: wrap() });
    expect(screen.getByText("Level up!")).toBeInTheDocument();
    expect(screen.getByTestId("confetti")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Level up! You reached level 5.");
  });

  it("announces a level-up without confetti when motion is reduced", () => {
    render(<XpBar xp={xp()} streak={streak(3)} />, { wrapper: wrap({ reduce_motion: true }) }).unmount();
    render(<XpBar xp={xp({ level: 5 })} streak={streak(3)} />, { wrapper: wrap({ reduce_motion: true }) });
    expect(screen.getByRole("status")).toHaveTextContent("Level up!");
    expect(screen.queryByTestId("confetti")).toBeNull();
  });

  it("lights the streak flame only while a streak is alive", () => {
    const { rerender } = render(<XpBar xp={xp()} streak={streak(3)} />, { wrapper: wrap() });
    expect(screen.getByTestId("streak").querySelector("[data-flame]")).toHaveAttribute("data-flame", "on");
    rerender(<XpBar xp={xp()} streak={streak(0)} />);
    expect(screen.getByTestId("streak").querySelector("[data-flame]")).toHaveAttribute("data-flame", "off");
  });

  it("has no axe violations", async () => {
    const { container } = render(<XpBar xp={xp()} streak={streak(3)} />, { wrapper: wrap() });
    await expectNoAxeViolations(container);
  });
});
