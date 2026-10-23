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
    addPhoto: vi.fn(), deletePhoto: vi.fn(), photoFeedbackStatus: vi.fn(), photoFeedback: vi.fn(), shareCard: vi.fn(),
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
    vi.mocked(api.trainerFeed).mockResolvedValue({ messages: [pr], unread: 0, algo_version: "watch-v1" });
    vi.mocked(api.photos).mockResolvedValue([photo(2, "2026-10-01"), photo(1, "2026-09-01")]);
    vi.mocked(api.photoData).mockResolvedValue({ id: 1, mime: "image/jpeg", data_url: "data:image/jpeg;base64,/9j/" });
    vi.mocked(api.photoFeedbackStatus).mockResolvedValue({ enabled: false, available: false, model: "qwen3-vl:2b", reason: "Off. Turn on Progress photo feedback in Settings to use it." });
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

  it("compares two photos and says why AI feedback is off", async () => {
    renderPage();
    const tiles = await screen.findAllByTestId("photo-tile");
    await userEvent.click(within(tiles[0]).getByRole("button", { name: "Compare" }));
    await userEvent.click(within(tiles[1]).getByRole("button", { name: "Compare" }));
    expect(await screen.findByTestId("compare")).toBeInTheDocument();
    expect(screen.getByTestId("feedback-off")).toHaveTextContent("Turn on Progress photo feedback");
    expect(api.photoFeedback).not.toHaveBeenCalled();
  });

  it("asks the local AI only when it is available, and labels the answer", async () => {
    vi.mocked(api.photoFeedbackStatus).mockResolvedValue({ enabled: true, available: true, model: "qwen3-vl:2b", reason: "Ready." });
    vi.mocked(api.photoFeedback).mockResolvedValue({ text: "Shoulders look broader.", guarded: true, model: "qwen3-vl:2b", version: "photo-feedback-v1", is_ai: true });
    renderPage();
    const tiles = await screen.findAllByTestId("photo-tile");
    await userEvent.click(within(tiles[0]).getByRole("button", { name: "Compare" }));
    await userEvent.click(within(tiles[1]).getByRole("button", { name: "Compare" }));
    await userEvent.click(await screen.findByRole("button", { name: "Ask the local AI what changed" }));
    const fb = await screen.findByTestId("photo-feedback");
    expect(fb).toHaveTextContent("Shoulders look broader.");
    expect(fb).toHaveTextContent("not medical advice");
    expect(fb).toHaveTextContent("safety filter");
    expect(api.photoFeedback).toHaveBeenCalledWith(1, 2); // older first
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
});
