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
    confirmAction: vi.fn(),
    cancelAction: vi.fn(),
    undoAction: vi.fn(),
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
    expect(screen.getByText(/Works offline · Ctrl\+K/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Message the trainer"), "hello{Enter}");
    await userEvent.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Back.")).toBeInTheDocument();
  });

  it("asks a question handed over by another part of the app", async () => {
    vi.mocked(api.trainerChat).mockResolvedValue(reply({ reply: "About 1.6 g per kg." }));
    const onAsked = vi.fn();
    render(
      <PrefsProvider initial={DEFAULT_SETTINGS} save={async (p) => ({ ...DEFAULT_SETTINGS, ...p })}>
        <TrainerChat open onClose={() => {}} onAction={vi.fn()} question="how much protein" onAsked={onAsked} />
      </PrefsProvider>,
    );
    expect(await screen.findByText("About 1.6 g per kg.")).toBeInTheDocument();
    expect(api.trainerChat).toHaveBeenCalledWith("how much protein");
    expect(onAsked).toHaveBeenCalled();
  });

  it("shows a proposed action as a card that runs only on Confirm, then offers Undo", async () => {
    const proposal = {
      id: 7, kind: "log_weight", label: "Log a weigh-in", risk: "low", params: { weight_kg: 81.4 },
      summary: ["Log 81.4 kg for today"], status: "proposed", source: "chat", origin_text: "weight 81.4",
      confirm_word: null, undoable: true, auto_ok: false, result: null, error: null,
      created_at: "2026-10-23T09:00:00", executed_at: null, undone_at: null,
    };
    vi.mocked(api.trainerChat).mockResolvedValue(reply({ reply: "Here's what I'd log.", proposal,
      actions: [{ kind: "proposal", target: "7", label: "Review" }] }));
    vi.mocked(api.confirmAction).mockResolvedValue({ ...proposal, status: "executed", executed_at: "2026-10-23T09:00:05" });
    vi.mocked(api.undoAction).mockResolvedValue({ ...proposal, status: "undone", undone_at: "2026-10-23T09:00:09" });
    setup();
    await userEvent.type(screen.getByLabelText("Message the trainer"), "weight 81.4{Enter}");
    const card = await screen.findByTestId("action-card");
    expect(card).toHaveTextContent("Log 81.4 kg for today");
    expect(api.confirmAction).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(api.confirmAction).toHaveBeenCalledWith(7, null));
    await userEvent.click(await screen.findByRole("button", { name: "Undo" }));
    expect(await screen.findByText("Undone.")).toBeInTheDocument();
  });

  it("needs the confirm word typed for a destructive action", async () => {
    const proposal = {
      id: 9, kind: "erase_data", label: "Erase my data", risk: "destructive", params: {},
      summary: ["Back up, then erase your logs"], status: "proposed", source: "chat", origin_text: "start fresh",
      confirm_word: "erase", undoable: false, auto_ok: false, result: null, error: null,
      created_at: "2026-10-23T09:00:00", executed_at: null, undone_at: null,
    };
    vi.mocked(api.trainerChat).mockResolvedValue(reply({ reply: "Sure.", proposal }));
    vi.mocked(api.confirmAction).mockResolvedValue({ ...proposal, status: "executed" });
    setup();
    await userEvent.type(screen.getByLabelText("Message the trainer"), "start fresh{Enter}");
    const confirm = await screen.findByRole("button", { name: "Confirm" });
    expect(confirm).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Type erase to confirm"), "erase");
    expect(confirm).toBeEnabled();
    await userEvent.click(confirm);
    await waitFor(() => expect(api.confirmAction).toHaveBeenCalledWith(9, "erase"));
  });
});
