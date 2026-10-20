import type { CoachReply } from "@ascend/shared";
import { useState, type FormEvent } from "react";

import { api } from "../api/client";
import { DeloadCard, WeeklyReviewCard } from "../components/PlanCards";
import { IconSpark } from "../components/Icons";
import { useApi } from "../lib/useApi";

interface Msg {
  role: "user" | "coach";
  text: string;
  reply?: CoachReply;
  /** Set on a failed answer: the question to resend with Retry. */
  failedQuestion?: string;
}

const FALLBACK_LABEL: Record<string, string> = {
  ai_disabled: "AI is off, so this is a rule-based tip.",
  ollama_unavailable: "Local AI not found (start Ollama and run `ollama pull qwen3:4b`). Showing a rule-based tip.",
};

export function CoachPage({ aiEnabled, refreshKey }: { aiEnabled: boolean | null; refreshKey: number }) {
  const status = useApi(api.coachStatus, [aiEnabled, refreshKey]);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);

  async function ask(question: string) {
    setBusy(true);
    try {
      const reply = await api.coachAsk(question);
      setMsgs((m) => [...m, { role: "coach", text: reply.text, reply }]);
    } catch (err) {
      setMsgs((m) => [...m, { role: "coach", text: `Couldn't answer: ${(err as Error).message}`, failedQuestion: question }]);
    } finally {
      setBusy(false);
    }
  }

  async function send(e: FormEvent) {
    e.preventDefault();
    const question = q.trim();
    if (!question) return;
    setMsgs((m) => [...m, { role: "user", text: question }]);
    setQ("");
    await ask(question);
  }

  function retry(index: number, question: string) {
    setMsgs((m) => m.filter((_, i) => i !== index)); // drop the failed answer, keep the question
    void ask(question);
  }

  const s = status.data;
  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-4">
      <div className="card flex items-center justify-between p-4 text-sm">
        <div className="flex items-center gap-3">
          <span className={`h-2.5 w-2.5 rounded-full ${s?.ai_enabled && s.ollama_available ? "bg-good" : s?.ai_enabled ? "bg-warn" : "bg-faint"}`} />
          <span className="text-ink">
            {status.error && !s ? "Couldn't check the local AI" : !s ? "Checking local AI…" : !s.ai_enabled ? "AI off · rule-based coach" : s.ollama_available ? `Local AI ready · ${s.model}` : `AI on, but ${s.model} isn't running locally`}
          </span>
        </div>
        {status.error && !s ? (
          <button type="button" className="text-xs text-accent hover:underline" onClick={status.reload}>Retry</button>
        ) : (
          <span className="text-xs text-faint">All numbers come from fixed formulas; the AI only explains them.</span>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <WeeklyReviewCard refreshKey={refreshKey} />
        <DeloadCard refreshKey={refreshKey} />
      </div>

      <div className="card flex min-h-[420px] flex-1 flex-col p-5">
        <div className="flex-1 space-y-3 overflow-y-auto">
          {msgs.length === 0 && (
            <div className="grid h-full place-items-center text-center">
              <div>
                <IconSpark className="mx-auto text-accent" width={28} height={28} />
                <p className="mt-3 text-sm text-ink">Ask ARC about your training, recovery or food.</p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {["What should I train today?", "Am I eating enough protein?", "Why is my chest amber?"].map((x) => (
                    <button key={x} type="button" className="chip hover:border-accent/50 hover:text-accent" onClick={() => setQ(x)}>{x}</button>
                  ))}
                </div>
              </div>
            </div>
          )}
          {msgs.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${m.role === "user" ? "bg-accent/15 text-ink" : "border border-line bg-panel-2 text-ink"}`}>
                {m.text}
                {m.failedQuestion && (
                  <button type="button" className="mt-1.5 block text-xs text-accent hover:underline" disabled={busy} aria-label="Ask this question again" onClick={() => retry(i, m.failedQuestion!)}>
                    Retry
                  </button>
                )}
                {m.reply && (
                  <div className="mt-1.5 text-[11px] text-faint">
                    {m.reply.source === "ollama" ? `Local AI · ${m.reply.model}` : FALLBACK_LABEL[m.reply.fallback_reason ?? ""] ?? "Rule-based tip (AI didn't answer in time)."}
                  </div>
                )}
              </div>
            </div>
          ))}
          {busy && <div className="text-xs text-muted" role="status">ARC is thinking…</div>}
        </div>
        <form onSubmit={send} className="mt-4 flex gap-2 border-t border-line pt-4">
          <input className="input" placeholder="Ask anything about your training…" value={q} onChange={(e) => setQ(e.target.value)} maxLength={1000} />
          <button className="btn-primary px-5" disabled={busy || !q.trim()}>Send</button>
        </form>
      </div>
    </div>
  );
}
