import type { ChatReply } from "@ascend/shared";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { TrainerChat } from "../components/TrainerChat";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { ChatPage } from "./Chat";

vi.mock("../api/client", () => ({
  api: {
    trainerChat: vi.fn(), trainerFeed: vi.fn(), trainerFeedRead: vi.fn(), coachWarm: vi.fn(),
    confirmAction: vi.fn(), undoAction: vi.fn(),
  },
}));

const reply = (r: Partial<ChatReply>): ChatReply => ({
  reply: "", mood: "neutral", intent: "faq", source: "rules", fallback_reason: null,
  actions: [], suggestions: [], faq_id: null, proposal: null, ...r,
});

function renderChat(trainer_id: "tara" | "iskra" = "tara") {
  const onPickTrainer = vi.fn();
  const onActionDone = vi.fn();
  const view = render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, trainer_id }} save={vi.fn()}>
      <ChatPage onAction={vi.fn()} onActionDone={onActionDone} onPickTrainer={onPickTrainer} />
    </PrefsProvider>,
  );
  return { onPickTrainer, onActionDone, ...view };
}

describe("Chat page (v1.3)", () => {
  beforeEach(() => {
    vi.mocked(api.trainerFeed).mockResolvedValue({ messages: [], unread: 0 } as never);
    vi.mocked(api.trainerChat).mockResolvedValue(reply({ reply: "Logged. Strong start.", mood: "proud" }));
  });

  it("shows the picked trainer large, with what they know best", async () => {
    const { container, onPickTrainer } = renderChat("tara");
    const portrait = screen.getByAltText("Tara, calm");
    expect(portrait).toHaveAttribute("data-trainer", "tara");
    expect(portrait.getAttribute("src")).toContain("tara-portrait");
    expect(screen.getByText("Best at: Flexibility, mobility, meditation and recovery")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Change trainer" }));
    expect(onPickTrainer).toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Close chat" })).toBeNull();
    await expectNoAxeViolations(container);
  });

  it("the portrait follows the mood of the latest reply", async () => {
    renderChat("iskra");
    await userEvent.type(screen.getByLabelText("Message the trainer"), "10 pushups{Enter}");
    expect(await screen.findByText("Logged. Strong start.")).toBeInTheDocument();
    expect(screen.getByAltText("Instructor Iskra Vey, proud")).toHaveAttribute("data-mood", "proud");
  });

  it("shares one conversation with the Ctrl+K drawer", async () => {
    const { unmount } = renderChat("iskra");
    await userEvent.type(screen.getByLabelText("Message the trainer"), "10 pushups{Enter}");
    expect(await screen.findByText("Logged. Strong start.")).toBeInTheDocument();
    unmount();
    render(
      <PrefsProvider initial={DEFAULT_SETTINGS} save={vi.fn()}>
        <TrainerChat open onClose={vi.fn()} onAction={vi.fn()} />
      </PrefsProvider>,
    );
    expect(screen.getByText("10 pushups")).toBeInTheDocument();
    expect(screen.getByText("Logged. Strong start.")).toBeInTheDocument();
  });

  it("a plan edit from chat runs only on Confirm and tells the app after Confirm and Undo", async () => {
    const proposal = {
      id: 12, kind: "edit_plan", label: "Edit my plan", risk: "low",
      params: { op: "rest", exercise: "squats", rest_s: 90 },
      summary: ["Bodyweight Squat: rest 90 s between sets instead of 60 s."], status: "proposed",
      source: "chat", origin_text: "rest 90s on squats", confirm_word: null, undoable: true,
      auto_ok: false, result: null, error: null, created_at: "2026-10-25T09:00:00",
      executed_at: null, undone_at: null,
    };
    vi.mocked(api.trainerChat).mockResolvedValue(reply({ reply: "Here's the change.", proposal }));
    vi.mocked(api.confirmAction).mockResolvedValue({ ...proposal, status: "executed" });
    vi.mocked(api.undoAction).mockResolvedValue({ ...proposal, status: "undone" });
    const { onActionDone } = renderChat("iskra");
    await userEvent.type(screen.getByLabelText("Message the trainer"), "rest 90s on squats{Enter}");
    expect(await screen.findByTestId("action-card")).toHaveTextContent("rest 90 s between sets");
    expect(onActionDone).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(onActionDone).toHaveBeenCalledTimes(1));
    await userEvent.click(await screen.findByRole("button", { name: "Undo" }));
    expect(await screen.findByText("Undone.")).toBeInTheDocument();
    expect(onActionDone).toHaveBeenCalledTimes(2);
  });

  it("Build my plan starts the trainer's plan interview and its chips answer it (v1.4)", async () => {
    vi.mocked(api.trainerChat)
      .mockResolvedValueOnce(reply({ reply: "Let's build your week. What's the main goal?", intent: "plan_builder", mood: "hyped",
        suggestions: ["Gain weight", "Build muscle", "Lose fat", "Get stronger", "Stop"] }))
      .mockResolvedValueOnce(reply({ reply: "Your weight now and where you'd like to be?", intent: "plan_builder", suggestions: ["Skip", "Stop"] }));
    renderChat("iskra");
    await userEvent.click(screen.getByTestId("build-plan"));
    expect(api.trainerChat).toHaveBeenCalledWith("Build my plan");
    expect(await screen.findByText("Let's build your week. What's the main goal?")).toBeInTheDocument();
    const chips = screen.getByLabelText("Suggestions");
    await userEvent.click(within(chips).getByRole("button", { name: "Gain weight" }));
    expect(api.trainerChat).toHaveBeenLastCalledWith("Gain weight");
    expect(await screen.findByText("Your weight now and where you'd like to be?")).toBeInTheDocument();
  });
});
