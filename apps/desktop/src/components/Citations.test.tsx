import type { ChatReply } from "@ascend/shared";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { DEFAULT_SETTINGS, PrefsProvider } from "../lib/prefs";
import { expectNoAxeViolations } from "../test/axe";
import { Citations } from "./Citations";
import { TrainerChat } from "./TrainerChat";

vi.mock("../api/client", () => ({
  api: {
    trainerChat: vi.fn(),
    trainerFeed: vi.fn().mockResolvedValue({ messages: [], unread: 0, algo_version: "watch-v1" }),
    trainerFeedRead: vi.fn().mockResolvedValue(null),
    coachWarm: vi.fn().mockResolvedValue({ loaded: false, model: "qwen3:4b", seconds: 0 }),
  },
}));

const CREATINE = {
  passage_id: "note:nutrition_basics:creatine",
  title: "Creatine",
  source: "ASCEND team notes",
  licence: "MIT (part of ASCEND)",
  url: "https://github.com/Lucifer-Newstar/Ascend-",
  ref: "nutrition_basics",
};

describe("Citations", () => {
  it("renders nothing without citations", () => {
    const { container } = render(<Citations items={[]} />);
    expect(container).toBeEmptyDOMElement();
    render(<Citations items={undefined} />);
    expect(screen.queryByTestId("citations")).not.toBeInTheDocument();
  });

  it("shows the source under a knowledge answer in the chat", async () => {
    const reply: ChatReply = {
      reply: "Here's what I have on that (Creatine): Creatine monohydrate is one of the most studied supplements.",
      mood: "neutral", intent: "nutrition_question", source: "knowledge", fallback_reason: null,
      actions: [], suggestions: [], faq_id: null, proposal: null, citations: [CREATINE],
    };
    vi.mocked(api.trainerChat).mockResolvedValue(reply);
    render(
      <PrefsProvider initial={{ ...DEFAULT_SETTINGS, ai_enabled: false }} save={async (p) => ({ ...DEFAULT_SETTINGS, ...p })}>
        <TrainerChat open onClose={() => {}} onAction={vi.fn()} />
      </PrefsProvider>,
    );
    await userEvent.type(screen.getByLabelText("Message the trainer"), "is creatine safe{Enter}");
    const box = await screen.findByTestId("citations");
    expect(within(box).getByRole("link", { name: "Creatine" })).toHaveAttribute("href", CREATINE.url);
    expect(box).toHaveTextContent("ASCEND team notes");
    expect(box).toHaveTextContent("MIT (part of ASCEND)");
    await expectNoAxeViolations(document.body);
  });
});
