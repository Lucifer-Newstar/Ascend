/**
 * Why a rule-based answer stands in for the local model's, in one honest line. Each reason
 * is distinct (1.0.0 showed "AI didn't answer in time" for every failure).
 */
export const FALLBACK_LABEL: Record<string, string> = {
  ai_disabled: "AI is off, so this is a rule-based answer.",
  ollama_unavailable: "Local AI isn't running (see Settings > AI setup), so this is a rule-based answer.",
  timeout: "The local AI took too long (it may still be loading), so this is a rule-based answer.",
  model_error: "The local AI returned an error, so this is a rule-based answer.",
  guard_rejected: "The AI reply didn't pass the safety check, so here's a rule-based answer.",
};

export function fallbackLabel(reason: string | null | undefined): string | null {
  if (!reason) return null;
  return FALLBACK_LABEL[reason] ?? "Rule-based answer.";
}

/** The label under a coach reply: model, routed to the trainer's notes, or why rules answered. */
export function replySourceLabel(r: { source: string; model: string | null; tip_code: string; fallback_reason: string | null }): string {
  if (r.source === "ollama") return `Local AI · ${r.model ?? "model"}`;
  if (r.tip_code.startsWith("trainer:")) return "Answered from the trainer's notes.";
  return fallbackLabel(r.fallback_reason) ?? "Rule-based tip.";
}
