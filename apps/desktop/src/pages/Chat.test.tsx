import type { ChatReply } from "@ascend/shared";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { TrainerChat } from "../components/TrainerChat";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { ChatPage } from "./Chat";

vi.mock("../api/client", () => ({
  api: { trainerChat: vi.fn(), trainerFeed: vi.fn(), trainerFeedRead: vi.fn(), coachWarm: vi.fn() },
}));

const reply = (r: Partial<ChatReply>): ChatReply => ({
  reply: "", mood: "neutral", intent: "faq", source: "rules", fallback_reason: null,
  actions: [], suggestions: [], faq_id: null, proposal: null, ...r,
});

function renderChat(trainer_id: "tara" | "iskra" = "tara") {
  const onPickTrainer = vi.fn();
  const view = render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, trainer_id }} save={vi.fn()}>
      <ChatPage onAction={vi.fn()} onActionDone={vi.fn()} onPickTrainer={onPickTrainer} />
    </PrefsProvider>,
  );
  return { onPickTrainer, ...view };
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
});
