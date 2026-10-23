import type { ChatReply } from "@ascend/shared";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { SLOW_AFTER_MS, TrainerChat } from "./TrainerChat";

vi.mock("../api/client", () => ({
  api: {
    trainerChat: vi.fn(),
    trainerFeed: vi.fn(),
    trainerFeedRead: vi.fn().mockResolvedValue(null),
    coachWarm: vi.fn().mockResolvedValue({ loaded: false, model: "qwen3:4b", seconds: 0 }),
  },
}));

const reply = (over: Partial<ChatReply>): ChatReply => ({
  reply: "Hey.", mood: "neutral", intent: "greeting", source: "rules", fallback_reason: null,
  actions: [], suggestions: [], faq_id: null, proposal: null, ...over,
});

function setup(onAction = vi.fn(), ai = true) {
  render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, ai_enabled: ai }} save={async (p) => ({ ...DEFAULT_SETTINGS, ...p })}>
      <TrainerChat open onClose={() => {}} onAction={onAction} />
    </PrefsProvider>,
  );
  return onAction;
}

describe("TrainerChat", () => {
  beforeEach(() => {
    vi.mocked(api.trainerFeed).mockResolvedValue({ messages: [], unread: 0, algo_version: "watch-v1" });
  });
  afterEach(() => vi.useRealTimers());

  it("greets, warms the model and answers with actions", async () => {
    vi.mocked(api.trainerChat).mockResolvedValue(reply({
      reply: "Let's go.", intent: "tour", mood: "hyped",
      actions: [{ kind: "tour", target: "skills", label: "Tour Skills" }, { kind: "proposal", target: null, label: "Hidden" }],
    }));
    const onAction = setup();
    expect(await screen.findByText(/I'm here/)).toBeInTheDocument();
    expect(api.coachWarm).toHaveBeenCalled();
    await userEvent.type(screen.getByLabelText("Message the trainer"), "tour me through skills{Enter}");
    expect(await screen.findByText("Let's go.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Hidden" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Tour Skills" }));
    expect(onAction).toHaveBeenCalledWith({ kind: "tour", target: "skills", label: "Tour Skills" });
    await expectNoAxeViolations(document.body);
  });

  it("shows why a rule-based answer stood in for the model", async () => {
    vi.mocked(api.trainerChat).mockResolvedValue(reply({ reply: "That one isn't in my notes.", intent: "unknown", fallback_reason: "guard_rejected" }));
    setup();
    await userEvent.type(screen.getByLabelText("Message the trainer"), "meaning of life{Enter}");
    expect(await screen.findByText("The AI reply didn't pass the safety check, so here's a rule-based answer.")).toBeInTheDocument();
  });

  it("says the model may be loading when an answer is slow", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let resolve: (r: ChatReply) => void = () => {};
    vi.mocked(api.trainerChat).mockReturnValue(new Promise((r) => { resolve = r; }));
    setup();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    await user.type(screen.getByLabelText("Message the trainer"), "hello{Enter}");
    expect(screen.getByTestId("chat-busy")).toHaveTextContent("Thinking…");
    act(() => { vi.advanceTimersByTime(SLOW_AFTER_MS + 10); });
    expect(screen.getByTestId("chat-busy")).toHaveTextContent(/Loading the local AI/);
    await act(async () => resolve(reply({ reply: "Hey, Navin." })));
    expect(await screen.findByText("Hey, Navin.")).toBeInTheDocument();
  });

  it("shows unread watcher notices and marks them read", async () => {
    vi.mocked(api.trainerFeed).mockResolvedValue({
      unread: 1, algo_version: "watch-v1",
      messages: [{ id: 7, kind: "pr", mood: "proud", text: "New record on Back Squat.", action_kind: "share", action_target: "pr", share: null, created_at: "2026-10-23T08:00:00", read: false }],
    });
    setup();
    expect(await screen.findByText("New record on Back Squat.")).toBeInTheDocument();
    expect(screen.getByText("Noticed")).toBeInTheDocument();
    await waitFor(() => expect(api.trainerFeedRead).toHaveBeenCalledWith([7]));
  });

  it("offers retry when the engine is unreachable", async () => {
    vi.mocked(api.trainerChat).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(reply({ reply: "Back." }));
    setup(vi.fn(), false);
    expect(screen.getByText(/AI off/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Message the trainer"), "hello{Enter}");
    await userEvent.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Back.")).toBeInTheDocument();
  });
});
