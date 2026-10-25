import type { FeedMessage, ProgressPhoto } from "@ascend/shared";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { ProfilePage } from "./Profile";

vi.mock("../api/client", () => ({
  api: {
    profile: vi.fn(), game: vi.fn(), stats: vi.fn(), titles: vi.fn(), trainerFeed: vi.fn(), photos: vi.fn(), photoData: vi.fn(),
    addPhoto: vi.fn(), deletePhoto: vi.fn(), shareCard: vi.fn(),
    prs: vi.fn(), bosses: vi.fn(),
  },
}));

const photo = (id: number, taken_on: string): ProgressPhoto => ({ id, taken_on, pose: "front", note: "", mime: "image/jpeg", bytes: 1000, created_at: `${taken_on}T09:00:00` });
const pr: FeedMessage = { id: 3, kind: "pr", mood: "proud", text: "New record on Back Squat: an estimated 120 kg one-rep max.", action_kind: "share", action_target: "pr",
  share: { kind: "pr", exercise: "Back Squat", e1rm_kg: 120 }, created_at: "2026-10-22T10:00:00", read: true };

function renderPage() {
  return render(
    <PrefsProvider initial={DEFAULT_SETTINGS} save={async (p) => ({ ...DEFAULT_SETTINGS, ...p })}>
      <ToastProvider><ProfilePage refreshKey={0} /></ToastProvider>
    </PrefsProvider>,
  );
}

describe("ProfilePage", () => {
  beforeEach(() => {
    vi.mocked(api.profile).mockResolvedValue({ name: "Navin", age: 21 } as never);
    vi.mocked(api.game).mockResolvedValue({ xp: { level: 7, rank: "D", rank_title: "Hunter" }, streak: { current: 4, best: 9 } } as never);
    vi.mocked(api.stats).mockResolvedValue({ stats: [{ key: "str", label: "Strength", value: 31, formula: "", inputs: {} }], version: "v", window_days: 28 });
    vi.mocked(api.titles).mockResolvedValue([{ title: "Golem Breaker", boss: "Iron Golem" } as never]);
    vi.mocked(api.prs).mockResolvedValue([]);
    vi.mocked(api.bosses).mockResolvedValue([
      { name: "Iron Golem", title: "Golem Breaker", tier: "E", category: "strength", min_level: "beginner", seasonal: false, season: null, months: [], drop: null, beaten: 1 },
      { name: "Bone Titan", title: "Titan Toppler", tier: "S", category: "strength", min_level: "expert", seasonal: false, season: null, months: [], drop: null, beaten: 0 },
      { name: "Harvest Colossus", title: "Harvest Breaker", tier: "level", category: "martial_arts", min_level: "beginner", seasonal: true, season: "Harvest Festival", months: [10, 11], drop: "outfit_harvest_festival", beaten: 0 },
    ]);
    vi.mocked(api.trainerFeed).mockResolvedValue({ messages: [pr], unread: 0, algo_version: "watch-v1" });
    vi.mocked(api.photos).mockResolvedValue([photo(2, "2026-10-01"), photo(1, "2026-09-01")]);
    vi.mocked(api.photoData).mockResolvedValue({ id: 1, mime: "image/jpeg", data_url: "data:image/jpeg;base64,/9j/" });
  });

  it("shows the Hunter card, achievements and blurred photos", async () => {
    const { container } = renderPage();
    expect(await screen.findByTestId("hunter-name")).toHaveTextContent("Navin");
    expect(await screen.findByText(/Level 7 · Rank D/)).toBeInTheDocument();
    expect(await screen.findByText("Golem Breaker")).toBeInTheDocument();
    expect(await screen.findByText(/120 kg one-rep max/)).toBeInTheDocument();
    const tiles = await screen.findAllByTestId("photo-tile");
    expect(tiles).toHaveLength(2);
    await waitFor(() => expect(container.querySelectorAll('img[data-blurred="true"]').length).toBe(2));
    await userEvent.click(screen.getByRole("button", { name: "Show photos" }));
    expect(container.querySelectorAll('img[data-blurred="true"]').length).toBe(0);
    await expectNoAxeViolations(container);
  });

  it("compares two photos side by side with no AI judging them", async () => {
    renderPage();
    const tiles = await screen.findAllByTestId("photo-tile");
    await userEvent.click(within(tiles[0]).getByRole("button", { name: "Compare" }));
    await userEvent.click(within(tiles[1]).getByRole("button", { name: "Compare" }));
    expect(await screen.findByTestId("compare")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /local AI/ })).toBeNull();
    expect(screen.queryByTestId("photo-feedback")).toBeNull();
  });

  it("opens a share card for an achievement with the caption and the X link", async () => {
    vi.mocked(api.shareCard).mockResolvedValue({ kind: "pr", title: "New personal record", headline: "Back Squat: 120 kg", detail: "Estimated one-rep max",
      caption: "New PR on Back Squat: an estimated 120 kg one-rep max. Tracked with ASCEND. #ASCEND #calisthenics", x_url: "https://x.com/intent/tweet?text=New", version: "share-v1" });
    const open = vi.spyOn(window, "open").mockImplementation(() => null);
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /^Share: New record/ }));
    const dialog = await screen.findByTestId("share-dialog");
    expect(api.shareCard).toHaveBeenCalledWith({ kind: "pr", exercise: "Back Squat", e1rm_kg: 120 });
    expect(await within(dialog).findByTestId("share-caption")).toHaveTextContent("#ASCEND");
    await userEvent.click(within(dialog).getByRole("button", { name: "Post on X" }));
    expect(open).toHaveBeenCalledWith("https://x.com/intent/tweet?text=New", "_blank", "noopener");
    open.mockRestore();
  });

  it("shows the avatar at your rank and a wardrobe of unlockable cosmetics", async () => {
    const save = vi.fn(async (p) => ({ ...DEFAULT_SETTINGS, ...p }));
    render(
      <PrefsProvider initial={DEFAULT_SETTINGS} save={save}>
        <ToastProvider><ProfilePage refreshKey={0} /></ToastProvider>
      </PrefsProvider>,
    );
    const wardrobe = await screen.findByTestId("wardrobe");
    expect((await screen.findAllByTestId("avatar"))[0]).toHaveAttribute("data-rank", "D");
    // a starter outfit is open; rank C, a 30-day streak and a seasonal drop are not yet
    expect(within(wardrobe).getByTestId("cosmetic-outfit_cyber_hunter")).toBeEnabled();
    expect(within(wardrobe).getByTestId("cosmetic-outfit_celestial_warrior")).toBeDisabled();
    expect(within(wardrobe).getByTestId("cosmetic-outfit_celestial_warrior")).toHaveTextContent("Reach rank C");
    expect(within(wardrobe).getByTestId("cosmetic-weapon_shadow_dagger")).toBeEnabled(); // one boss beaten
    await userEvent.click(within(wardrobe).getByTestId("cosmetic-outfit_cyber_hunter"));
    expect(save).toHaveBeenCalledWith({ outfit: "outfit_cyber_hunter" });
    await userEvent.click(within(wardrobe).getByRole("radio", { name: "Female" }));
    expect(save).toHaveBeenCalledWith({ avatar: "female" });
    // themed items hide when switched off
    await userEvent.click(within(wardrobe).getByLabelText("Show themed cosmetics"));
    expect(save).toHaveBeenLastCalledWith(expect.objectContaining({ themed_cosmetics: false }));
    await waitFor(() => expect(within(wardrobe).queryByTestId("cosmetic-outfit_celestial_warrior")).toBeNull());
  });

  it("lists the boss ladder by tier with the seasonal bosses and their drops", async () => {
    renderPage();
    const ladder = await screen.findByTestId("boss-ladder");
    expect(within(ladder).getByRole("region", { name: "Tier E" })).toHaveTextContent("Iron Golem");
    expect(within(ladder).getByRole("region", { name: "Tier S" })).toHaveTextContent("Bone Titan");
    const seasonal = within(ladder).getByRole("region", { name: "Seasonal bosses" });
    expect(seasonal).toHaveTextContent("Harvest Festival, Oct to Nov");
    expect(seasonal).toHaveTextContent("drops Harvest Festival set");
    expect(within(ladder).getAllByTestId("ladder-boss")[0]).toHaveTextContent("Beaten 1x");
  });
});
