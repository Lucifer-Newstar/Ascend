import type { ChatReply } from "@ascend/shared";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { resetChat } from "../lib/chatStore";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { TEAM_AREAS, teamFor } from "../lib/trainer";
import { ChatPage } from "../pages/Chat";
import { expectNoAxeViolations } from "../test/axe";
import { TrainerChat } from "./TrainerChat";

vi.mock("../api/client", () => ({
  api: {
    trainerChat: vi.fn(), trainerFeed: vi.fn(), trainerFeedRead: vi.fn(), coachWarm: vi.fn(),
    confirmAction: vi.fn(), undoAction: vi.fn(),
  },
}));

const reply = (r: Partial<ChatReply>): ChatReply => ({
  reply: "", mood: "neutral", intent: "faq", source: "rules", fallback_reason: null,
  actions: [], suggestions: [], faq_id: null, proposal: null, speaker: "iskra", handoff: null, ...r,
});

const toVera = reply({
  reply: "Here's what I have on that (Creatine): 3-5 g a day works.", source: "knowledge",
  intent: "nutrition_question", speaker: "vera", handoff: "That's Vera's area (nutrition). Over to her.",
});

function renderPage(settings: Partial<typeof DEFAULT_SETTINGS> = {}) {
  return render(
    <PrefsProvider initial={{ ...DEFAULT_SETTINGS, ...settings }} save={vi.fn()}>
      <ChatPage onAction={vi.fn()} onActionDone={vi.fn()} onPickTrainer={vi.fn()} />
    </PrefsProvider>,
  );
}

describe("Coaching team (item 13)", () => {
  beforeEach(() => {
    resetChat();
    vi.mocked(api.trainerFeed).mockResolvedValue({ messages: [], unread: 0 } as never);
    vi.mocked(api.trainerChat).mockResolvedValue(toVera);
  });

  it("every specialist covers one area and the main trainer is not on their own team", () => {
    expect(Object.keys(TEAM_AREAS).sort()).toEqual(["dario", "idris", "kai", "tara", "vera"]);
    expect(teamFor("iskra").map((m) => m.trainer.id)).toEqual(["vera", "tara", "kai", "dario", "idris"]);
    expect(teamFor("kai").map((m) => m.trainer.id)).not.toContain("kai");
    expect(teamFor("kai").map((m) => m.trainer.id)).not.toContain("iskra");
  });

  it("shows the main trainer's handoff line, then the specialist's name and portrait", async () => {
    const { container } = renderPage({ trainer_id: "iskra" });
    await userEvent.type(screen.getByLabelText("Message the trainer"), "is creatine worth it{Enter}");
    const line = await screen.findByTestId("handoff-line");
    expect(line).toHaveTextContent("Iskra: That's Vera's area (nutrition). Over to her.");
    const who = screen.getByTestId("speaker-label");
    expect(who).toHaveAttribute("data-trainer", "vera");
    expect(who).toHaveTextContent("Vera Kestrine");
    // The big portrait and the name follow the specialist while they answer.
    expect(screen.getByTestId("chat-speaker")).toHaveTextContent("Vera Kestrine");
    expect(screen.getByAltText("Vera Kestrine, calm").getAttribute("src")).toContain("vera-portrait");
    expect(screen.getByText("Specialist · Iskra runs your chat")).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });

  it("the main trainer takes the floor back on the next app reply", async () => {
    vi.mocked(api.trainerChat)
      .mockResolvedValueOnce(toVera)
      .mockResolvedValueOnce(reply({ reply: "XP comes from logging sets.", speaker: "iskra" }));
    renderPage({ trainer_id: "iskra" });
    await userEvent.type(screen.getByLabelText("Message the trainer"), "is creatine worth it{Enter}");
    await screen.findByTestId("handoff-line");
    await userEvent.type(screen.getByLabelText("Message the trainer"), "how does xp work{Enter}");
    expect(await screen.findByText("XP comes from logging sets.")).toBeInTheDocument();
    expect(screen.getByTestId("chat-speaker")).toHaveTextContent("Instructor Iskra Vey");
    expect(screen.getAllByTestId("handoff-line")).toHaveLength(1);
  });

  it("lists your team under the main trainer, and hides it when the team is off", () => {
    const { unmount } = renderPage({ trainer_id: "iskra" });
    const row = screen.getByTestId("team-row");
    for (const name of ["Idris", "Dario", "Kai", "Tara", "Vera"]) expect(within(row).getByText(name, { exact: false })).toBeInTheDocument();
    unmount();
    renderPage({ trainer_id: "iskra", team_handoff: false });
    expect(screen.queryByTestId("team-row")).toBeNull();
  });

  it("the drawer header shows who is answering", async () => {
    render(
      <PrefsProvider initial={{ ...DEFAULT_SETTINGS, trainer_id: "iskra" }} save={vi.fn()}>
        <TrainerChat open onClose={vi.fn()} onAction={vi.fn()} />
      </PrefsProvider>,
    );
    await userEvent.type(screen.getByLabelText("Message the trainer"), "is creatine worth it{Enter}");
    await screen.findByTestId("handoff-line");
    const header = screen.getByRole("banner");
    expect(header).toHaveTextContent("Vera Kestrine");
    expect(header).toHaveTextContent("with Iskra");
    expect(within(header).getByTestId("trainer-portrait")).toHaveAttribute("data-trainer", "vera");
  });

  it("a reply without a handoff shows no handoff line or specialist label", async () => {
    vi.mocked(api.trainerChat).mockResolvedValue(reply({ reply: "Logged. Strong start.", speaker: "iskra" }));
    renderPage({ trainer_id: "iskra" });
    await userEvent.type(screen.getByLabelText("Message the trainer"), "10 pushups{Enter}");
    expect(await screen.findByText("Logged. Strong start.")).toBeInTheDocument();
    expect(screen.queryByTestId("handoff-line")).toBeNull();
    expect(screen.queryByTestId("speaker-label")).toBeNull();
  });
});
