import { describe, expect, it } from "vitest";

import { FALLBACK_LABEL, fallbackLabel, replySourceLabel } from "./fallback";

describe("fallback labels", () => {
  it("names each reason differently", () => {
    const labels = ["ai_disabled", "ollama_unavailable", "timeout", "model_error", "guard_rejected"].map((r) => fallbackLabel(r));
    expect(new Set(labels).size).toBe(5);
    expect(fallbackLabel("guard_rejected")).toBe("The AI reply didn't pass the safety check, so here's a rule-based answer.");
    expect(fallbackLabel(null)).toBeNull();
    expect(Object.values(FALLBACK_LABEL).some((l) => l.includes("didn't answer in time"))).toBe(false);
  });

  it("labels model, routed and fallback replies", () => {
    expect(replySourceLabel({ source: "ollama", model: "qwen3:4b", tip_code: "x", fallback_reason: null })).toBe("Local AI · qwen3:4b");
    expect(replySourceLabel({ source: "rules", model: null, tip_code: "trainer:greeting", fallback_reason: null })).toBe("Answered from the trainer's notes.");
    expect(replySourceLabel({ source: "rules", model: "qwen3:4b", tip_code: "under_quads", fallback_reason: "timeout" })).toMatch(/took too long/);
  });
});
