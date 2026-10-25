import type { AiSetup } from "@ascend/shared";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { expectNoAxeViolations } from "../test/axe";
import { AiSetupPanel } from "./AiSetupPanel";

vi.mock("../api/client", () => ({ api: { aiSetup: vi.fn(), aiModel: vi.fn(), aiTest: vi.fn() } }));

const base: AiSetup = {
  ai_enabled: true, tier: "rules", ollama_installed: false, ollama_running: false, ollama_version: null,
  models: [], model: "qwen3:4b", model_installed: false,
  recommended: { model: "qwen3:0.6b", size_gb: 0.5, reason: "8 GB of RAM: the small model keeps replies quick.", pull_command: "ollama pull qwen3:0.6b" },
  hardware: { ram_gb: 8, vram_gb: null, gpu: null }, failures: 0, suggestion: null, smaller_model: "qwen3:1.7b",
  algo_version: "ai-tiers-v1",
};

describe("AiSetupPanel", () => {
  it("explains rule-based mode and recommends a model", async () => {
    vi.mocked(api.aiSetup).mockResolvedValue(base);
    render(<AiSetupPanel aiEnabled onToggleAi={() => {}} />);
    expect(await screen.findByTestId("ai-tier")).toHaveTextContent("Ollama isn't installed");
    expect(screen.getByText("qwen3:0.6b (0.5 GB)")).toBeInTheDocument();
    expect(screen.getByText("ollama pull qwen3:0.6b")).toBeInTheDocument();
    expect(screen.getByText(/no NVIDIA GPU found/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Test the AI" })).toBeDisabled();
    await expectNoAxeViolations(document.body);
  });

  it("switches model, tests it and offers a smaller one after failures", async () => {
    const ready: AiSetup = {
      ...base, tier: "ai", ollama_installed: true, ollama_running: true, ollama_version: "0.12.6", model_installed: true,
      models: [{ name: "qwen3:4b", size_gb: 2.5 }, { name: "qwen3:1.7b", size_gb: 1.4 }],
      failures: 3, suggestion: "The last 3 AI answers failed or timed out. Switch to qwen3:1.7b for quicker answers?",
      hardware: { ram_gb: 16, vram_gb: 4, gpu: "RTX 3050" },
    };
    vi.mocked(api.aiSetup).mockResolvedValue(ready);
    vi.mocked(api.aiModel).mockResolvedValue(ready);
    vi.mocked(api.aiTest).mockResolvedValue({ ok: true, model: "qwen3:4b", seconds: 1.2, reason: null, reply: "Ready." });
    render(<AiSetupPanel aiEnabled onToggleAi={() => {}} />);
    expect(await screen.findByTestId("ai-tier")).toHaveTextContent("AI mode: qwen3:4b is ready.");
    expect(screen.getByText("RTX 3050 · 4 GB")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Use qwen3:1.7b" }));
    expect(api.aiModel).toHaveBeenCalledWith("qwen3:1.7b");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Model in use" }), "qwen3:1.7b");
    await waitFor(() => expect(api.aiModel).toHaveBeenCalledTimes(2));
    await userEvent.click(screen.getByRole("button", { name: "Test the AI" }));
    expect(await screen.findByText(/Answered in 1.2 s/)).toBeInTheDocument();
  });
});
