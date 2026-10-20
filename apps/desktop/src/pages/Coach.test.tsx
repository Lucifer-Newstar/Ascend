import { render, screen, waitFor, within } from "@testing-library/react";
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

  it("puts a suggested question in the labelled box and announces the conversation", async () => {
    vi.mocked(api.coachAsk).mockResolvedValue(reply);
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "What should I train today?" }));
    const box = screen.getByRole("textbox", { name: "Ask the coach" });
    expect(box).toHaveValue("What should I train today?");
    expect(box).toHaveFocus();
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    const log = screen.getByLabelText("Conversation with the coach");
    expect(log).toHaveAttribute("aria-live", "polite");
    expect(await within(log).findByText("Train legs today.")).toBeInTheDocument();
  });

  it("offers a retry when the AI status check fails", async () => {
    vi.mocked(api.coachStatus).mockRejectedValueOnce(new Error("offline"));
    renderPage();
    expect(await screen.findByText("Couldn't check the local AI")).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: "Retry" })[0]);
    await waitFor(() => expect(screen.getByText("AI off · rule-based coach")).toBeInTheDocument());
  });

  it("shows a recommended deload as a System warning window, and a plain card otherwise", async () => {
    vi.mocked(api.deload).mockResolvedValue({
      recommended: true, kind: "planned", training_weeks: 5, guidance: null, deload_week: null, algo_version: "deload-v2",
      signals: [{ code: "weeks", active: true, detail: "5 hard weeks in a row" }],
    });
    renderPage();
    const notice = await screen.findByRole("region", { name: "Deload notice" });
    expect(notice).toHaveAttribute("data-variant", "warning");
    expect(within(notice).getByText("Planned deload: 5 hard weeks in a row.")).toBeInTheDocument();
    expect(within(notice).getByRole("button", { name: "Start deload week" })).toBeInTheDocument();
  });
});
