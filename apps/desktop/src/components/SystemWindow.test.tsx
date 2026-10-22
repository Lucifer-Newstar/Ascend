import type { GameSummary, QuestItem, SystemNotice } from "@ascend/shared";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef, useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { axeViolations } from "../test/axe";
import { eventsBetween, nextNotice, SystemEvents } from "./SystemEvents";
import { rankTint, SystemWindow, windowAccent } from "./SystemWindow";

function wrap(ui: React.ReactNode, reduce = false) {
  return <PrefsProvider initial={{ ...DEFAULT_SETTINGS, reduce_motion: reduce }} save={vi.fn()}>{ui}</PrefsProvider>;
}

describe("SystemWindow", () => {
  it("renders a named region with a bracketed header, corner brackets and a scan line", async () => {
    const { container } = render(wrap(<SystemWindow title="Daily quest" variant="quest"><p>Pull-ups 5 × 6</p></SystemWindow>));
    const region = screen.getByRole("region", { name: "Daily quest" });
    expect(region).toHaveTextContent("[ Daily quest ]");
    expect(region.querySelectorAll(".sys-corner")).toHaveLength(4);
    expect(region.querySelector(".sys-scan")).not.toBeNull();
    expect(region).toHaveAttribute("data-motion", "full");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("with Reduce motion renders no scan line (the entrance is a 120 ms fade in CSS)", () => {
    render(wrap(<SystemWindow title="Level up" variant="levelup" />, true));
    const region = screen.getByRole("region", { name: "Level up" });
    expect(region).toHaveAttribute("data-motion", "reduced");
    expect(region.querySelector(".sys-scan")).toBeNull();
  });

  it("as a modal traps focus, closes on Esc and returns focus", async () => {
    function Harness() {
      const [open, setOpen] = useState(false);
      const ok = useRef<HTMLButtonElement>(null);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>Open</button>
          {open && (
            <SystemWindow modal title="Skill acquired" variant="skill" onClose={() => setOpen(false)} initialFocus={ok}
              actions={<><button type="button">View tree</button><button ref={ok} type="button">Continue</button></>} />
          )}
        </>
      );
    }
    const { container } = render(wrap(<Harness />));
    const opener = screen.getByRole("button", { name: "Open" });
    await userEvent.click(opener);
    const dialog = screen.getByRole("dialog", { name: "Skill acquired" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("button", { name: "Continue" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "View tree" })).toHaveFocus();
    await userEvent.tab({ shift: true });
    expect(screen.getByRole("button", { name: "Continue" })).toHaveFocus();
    expect(await axeViolations(container)).toEqual([]);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(opener).toHaveFocus();
  });

  it("tints by variant first, then by rank (System UI only)", () => {
    expect(windowAccent("warning", "S")).toBe("--color-warn");
    expect(windowAccent("levelup", "E")).toBe("--color-xp");
    expect(windowAccent("quest", "E")).toBe("--color-accent");
    expect(rankTint("D")).toBe("--color-accent");
    expect(rankTint("B")).toBe("--color-xp");
    expect(rankTint("S")).toBe("--color-rank-s");
  });
});

const quest = (over: Partial<QuestItem> = {}): QuestItem => ({
  id: 1, day: "2026-10-20", kind: "training", code: "t", title: "Pull-ups", detail: "", metric: "sets", target: 3, progress: 3, xp: 30, completed_at: null, ...over,
});

const game = (level: number, rank: string, items: QuestItem[]): GameSummary => ({
  xp: { total: 100, today: 10, level, xp_into_level: 5, xp_for_next: 100, rank, rank_title: "Hunter", daily_cap: 500, formula_version: "v" },
  streak: { current: 1, best: 1, freezes_held: 0, freezes_used: 0, active_today: true },
  calm: { current: 0, best: 0, active_today: false },
  quest: items,
});

describe("System events", () => {
  it("finds level up, rank up and quest complete, and nothing on the first load", () => {
    const g1 = game(4, "E", [quest(), quest({ id: 2 })]);
    expect(eventsBetween(null, g1)).toEqual([]);
    const prev = { level: 4, rank: "E", questDone: false };
    const g2 = game(5, "D", [quest({ completed_at: "x" }), quest({ id: 2, completed_at: "y" })]);
    const ev = eventsBetween(prev, g2);
    expect(ev.map((e) => e.variant)).toEqual(["levelup", "quest"]);
    expect(ev[0].text).toContain("Rank up: E → D");
    expect(ev[0].title).toBe("Rank up");
    expect(ev[1].text).toBe("Daily quest cleared: 2 of 2 tasks · 60 XP.");
    expect(eventsBetween({ level: 5, rank: "D", questDone: true }, g2)).toEqual([]);
  });

  it("shows a notice when the level rises and closes it with Esc", async () => {
    const { rerender } = render(wrap(<SystemEvents game={game(4, "E", [quest()])} />));
    expect(screen.queryByTestId("system-event-levelup")).toBeNull();
    rerender(wrap(<SystemEvents game={game(5, "E", [quest()])} />));
    expect(screen.getByRole("region", { name: "Level up" })).toHaveTextContent("Level 5 reached. Rank E · Hunter.");
    expect(screen.getByTestId("moment-levelup")).toHaveTextContent("LV 5");
    expect(screen.getByRole("status")).toHaveTextContent("Level up. Level 5 reached.");
    await act(async () => { await userEvent.keyboard("{Escape}"); });
    expect(screen.queryByRole("region", { name: "Level up" })).toBeNull();
  });
});

describe("System notices", () => {
  const deload: SystemNotice = { id: "deload:2026-10-19", code: "deload", title: "Deload advised", text: "The System detects stalled lifts and fatigue building up in several muscles.", at: "2026-10-20T07:00:00" };
  const raised: SystemNotice = { id: "raised:9:1", code: "raised", title: "Target raised", text: "Barbell Bench Press: next time 3 × 6 @ 62.5 kg.", at: "2026-10-20T07:00:00" };

  it("picks the first notice not shown before", () => {
    expect(nextNotice([deload, raised], [])).toBe(deload);
    expect(nextNotice([deload, raised], [deload.id])).toBe(raised);
    expect(nextNotice([deload, raised], [deload.id, raised.id])).toBeNull();
  });

  it("speaks once: one notice per refresh, never the same id twice", async () => {
    window.localStorage.clear();
    const notices = vi.fn(async () => [deload, raised]);
    const g = game(4, "E", [quest()]);
    const { rerender } = render(wrap(<SystemEvents game={g} notices={notices} />));
    expect(await screen.findByTestId("system-event-warning")).toHaveTextContent("Deload advised");
    expect(screen.queryByTestId("system-event-notice")).toBeNull();
    rerender(wrap(<SystemEvents game={{ ...g }} notices={notices} />));
    expect(await screen.findByTestId("system-event-notice")).toHaveTextContent("Target raised");
    rerender(wrap(<SystemEvents game={{ ...g }} notices={notices} />));
    await act(async () => { await Promise.resolve(); });
    expect(screen.getAllByTestId(/system-event-/)).toHaveLength(2);
    expect(JSON.parse(window.localStorage.getItem("ascend.system.notices.seen") ?? "[]")).toEqual([deload.id, raised.id]);
  });
});
