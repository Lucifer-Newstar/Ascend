import type { UnlockEntry } from "@ascend/shared";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { UnlocksPage } from "./Unlocks";

vi.mock("../api/client", () => ({ api: { unlocks: vi.fn() } }));

const log: UnlockEntry[] = [
  { key: "cosmetic:pet_frost_cub", kind: "cosmetic", title: "Frost Cub", detail: "For your first seasonal boss.", at: "2026-10-25T18:30:00", seeded: false },
  { key: "boss:Iron Golem", kind: "boss", title: "Iron Golem", detail: "Title earned: Golem Breaker.", at: "2026-10-20T09:00:00", seeded: true },
  { key: "rank:D", kind: "rank", title: "Rank D", detail: "", at: "2026-10-20T09:00:00", seeded: true },
];

describe("Unlocks page (v1.4)", () => {
  it("lists unlocks with their dates, filters by kind and replays one", async () => {
    vi.mocked(api.unlocks).mockResolvedValue(log);
    const onBack = vi.fn();
    const { container } = render(
      <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()}><UnlocksPage onBack={onBack} /></PrefsProvider>,
    );
    const rows = await screen.findAllByTestId("unlock-row");
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent("Frost Cub");
    expect(rows[0]).toHaveTextContent("New cosmetic · 25 Oct 2026");
    expect(rows[1]).toHaveTextContent("Boss cleared · by 20 Oct 2026"); // already unlocked before v1.4
    await expectNoAxeViolations(container);
    await userEvent.click(screen.getByRole("radio", { name: "Ranks" }));
    expect(screen.getAllByTestId("unlock-row")).toHaveLength(1);
    await userEvent.click(within(screen.getByTestId("unlock-row")).getByRole("button", { name: "Replay: Rank D" }));
    expect(screen.getByTestId("unlock-scene")).toHaveAttribute("data-kind", "rank");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.queryByTestId("unlock-scene")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Back to Profile" }));
    expect(onBack).toHaveBeenCalled();
  });
});
