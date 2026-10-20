import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { ToastProvider } from "../components/Toast";
import { CoachPage } from "./Coach";

vi.mock("../api/client", () => ({
  api: { coachStatus: vi.fn(), coachAsk: vi.fn(), weeklyReview: vi.fn(), deload: vi.fn(), startDeload: vi.fn() },
}));

const reply = { source: "rules" as const, text: "Train legs today.", tip_code: "under_quads", model: null, fallback_reason: "ai_disabled" };

function renderPage() {
  return render(<ToastProvider><CoachPage aiEnabled={false} refreshKey={0} /></ToastProvider>);
}

describe("CoachPage", () => {
  beforeEach(() => {
    vi.mocked(api.coachStatus).mockResolvedValue({ ai_enabled: false, ollama_available: false, model: "qwen3:4b" });
    vi.mocked(api.weeklyReview).mockRejectedValue(new Error("skip"));
    vi.mocked(api.deload).mockRejectedValue(new Error("skip"));
  });

  it("retries a failed answer with the same question", async () => {
    vi.mocked(api.coachAsk).mockRejectedValueOnce(new Error("engine restarting")).mockResolvedValueOnce(reply);
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/Ask anything/), "What should I train?");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText(/Couldn't answer: engine restarting/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ask this question again" }));
    expect(await screen.findByText("Train legs today.")).toBeInTheDocument();
    expect(api.coachAsk).toHaveBeenLastCalledWith("What should I train?");
    expect(screen.queryByText(/Couldn't answer/)).toBeNull();
    expect(screen.getAllByText("What should I train?")).toHaveLength(1);
  });

  it("offers a retry when the AI status check fails", async () => {
    vi.mocked(api.coachStatus).mockRejectedValueOnce(new Error("offline"));
    renderPage();
    expect(await screen.findByText("Couldn't check the local AI")).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: "Retry" })[0]);
    await waitFor(() => expect(screen.getByText("AI off · rule-based coach")).toBeInTheDocument());
  });
});
