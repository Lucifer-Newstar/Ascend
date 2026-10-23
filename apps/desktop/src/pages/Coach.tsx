/**
 * Coach (12-column grid, spec §8.4 "System"): the AI status bar, the chat with ARC (8 columns)
 * and, beside it, the weekly review, the deload check and the System log of engine notices.
 */
import type { CoachReply, SystemNotice } from "@ascend/shared";
import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";

import { api } from "../api/client";
import { PENDING_COACH_KEY } from "../components/CommandBar";
import { DeloadCard, WeeklyReviewCard } from "../components/PlanCards";
import { IconSpark } from "../components/Icons";
import { PageGrid, Panel } from "../components/Page";
import { TrainerPortrait, useTrainerOn } from "../components/Trainer";
import { replySourceLabel } from "../lib/fallback";
import { moodFor } from "../lib/trainer";
import { useApi } from "../lib/useApi";

interface Msg {
  role: "user" | "coach";
  text: string;
  reply?: CoachReply;
  /** Set on a failed answer: the question to resend with Retry. */
  failedQuestion?: string;
}

export function CoachPage({ aiEnabled, refreshKey }: { aiEnabled: boolean | null; refreshKey: number }) {
  const trainer = useTrainerOn();
  const status = useApi(api.coachStatus, [aiEnabled, refreshKey]);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const end = useRef<HTMLDivElement>(null);

  // A question typed into the command bar (Ctrl+K) arrives here and is asked once.
  useEffect(() => {
    const pending = sessionStorage.getItem(PENDING_COACH_KEY);
    if (!pending) return;
    sessionStorage.removeItem(PENDING_COACH_KEY);
    setMsgs((m) => [...m, { role: "user", text: pending }]);
    void ask(pending);
  }, []);

  // Keep the newest message in view as the conversation grows.
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "nearest" });
  }, [msgs.length, busy]);

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
    <PageGrid label="Coach">
      <div className="card rise-in col-span-12 flex flex-wrap items-center justify-between gap-2 p-4 text-sm" role="status">
        <div className="flex items-center gap-3">
          <span className={`h-2.5 w-2.5 rounded-full ${s?.ai_enabled && s.ollama_available ? "bg-good" : s?.ai_enabled ? "bg-warn" : "bg-faint"}`} />
          <span className="text-ink">
            {status.error && !s ? "Couldn't check the local AI" : !s ? "Checking local AI…" : !s.ai_enabled ? "AI off · rule-based coach" : s.ollama_available ? `Local AI ready · ${s.model}` : `AI on, but ${s.model} isn't running locally`}
          </span>
        </div>
        {status.error && !s ? (
          <button type="button" className="text-xs text-accent hover:underline" onClick={status.reload}>Retry</button>
        ) : (
          <span className="text-xs text-muted">All numbers come from fixed formulas; the AI only explains them.</span>
        )}
      </div>

      <section className="card rise-in col-span-12 flex h-[min(720px,calc(100vh-190px))] min-h-[460px] flex-col self-start p-5 xl:sticky xl:top-0 xl:col-span-8" style={{ ["--i" as string]: 1 } as CSSProperties} aria-labelledby="chat-title">
        <h2 id="chat-title" className="card-title mb-3">Ask ARC</h2>
        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto" aria-live="polite" aria-label="Conversation with the coach">
          {msgs.length === 0 && (
            <div className="grid h-full place-items-center text-center">
              <div>
                <IconSpark className="mx-auto text-accent" width={28} height={28} />
                <p className="mt-3 text-sm text-ink">Ask ARC about your training, recovery or food.</p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {["What should I train today?", "Am I eating enough protein?", "Why is my chest amber?"].map((x) => (
                    <button key={x} type="button" className="chip hover:border-accent/50 hover:text-accent" onClick={() => { setQ(x); input.current?.focus(); }}>{x}</button>
                  ))}
                </div>
              </div>
            </div>
          )}
          {msgs.map((m, i) => (
            <div key={i} className={`panel-in flex items-start gap-2 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              {trainer && m.role !== "user" && <TrainerPortrait mood={m.reply ? moodFor(m.reply.tip_code) : "neutral"} size={36} />}
              <div className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${m.role === "user" ? "bg-accent/15 text-ink" : "border border-line bg-panel-2 text-ink"}`}>
                {m.text}
                {m.failedQuestion && (
                  <button type="button" className="mt-1.5 block text-xs text-accent hover:underline" disabled={busy} aria-label="Ask this question again" onClick={() => retry(i, m.failedQuestion!)}>
                    Retry
                  </button>
                )}
                {m.reply && (
                  <div className="mt-1.5 text-[11px] text-faint">
                    {replySourceLabel(m.reply)}
                  </div>
                )}
              </div>
            </div>
          ))}
          {busy && (
            <div className="flex items-center gap-2 text-xs text-muted" role="status">
              <span className="flex gap-1" aria-hidden="true">
                {[0, 1, 2].map((d) => (
                  <span key={d} className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" style={{ animationDelay: `${d * 160}ms` }} />
                ))}
              </span>
              ARC is thinking…
            </div>
          )}
          <div ref={end} />
        </div>
        <form onSubmit={send} className="mt-4 flex gap-2 border-t border-line pt-4">
          <input ref={input} className="input" aria-label="Ask the coach" placeholder="Ask anything about your training…" value={q} onChange={(e) => setQ(e.target.value)} maxLength={1000} />
          <button className="btn-primary px-5" disabled={busy || !q.trim()}>Send</button>
        </form>
      </section>
      <div className="col-span-12 space-y-5 xl:col-span-4">
        <WeeklyReviewCard refreshKey={refreshKey} />
        <DeloadCard refreshKey={refreshKey} />
        <SystemLog refreshKey={refreshKey} />
      </div>
    </PageGrid>
  );
}

const NOTICE_CHIP: Record<SystemNotice["code"], string> = { deload: "Deload", raised: "Target raised", recovered: "Recovered" };

/** The System notices the engines raised (deload, target raised, muscle recovered), newest first. */
function SystemLog({ refreshKey }: { refreshKey: number }) {
  const notices = useApi(api.notices, [refreshKey]);
  const list = [...(notices.data ?? [])].sort((a, b) => b.at.localeCompare(a.at)).slice(0, 8);
  return (
    <Panel id="system-log" index={4} title="System log" hint="Notices raised by the engines' fixed rules"
      loading={notices.loading && !notices.data} error={!notices.data ? notices.error ?? null : null} onRetry={notices.reload} skeletonLines={4}
      empty={notices.data && list.length === 0 ? { title: "No System notices right now.", hint: "A deload, a raised target or a recovered muscle shows up here." } : null}>
      <ol className="space-y-3">
        {list.map((n) => (
          <li key={n.id} className="rounded-md border border-line bg-panel-2 p-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="chip">{NOTICE_CHIP[n.code] ?? n.code}</span>
              <span className="text-[11px] text-muted">{timeAgo(n.at)}</span>
            </div>
            <div className="mt-1.5 font-medium text-ink">{n.title}</div>
            <p className="mt-0.5 text-xs leading-relaxed text-muted">{n.text}</p>
          </li>
        ))}
      </ol>
    </Panel>
  );
}

function timeAgo(iso: string, now = Date.now()): string {
  const mins = Math.max(0, Math.round((now - new Date(iso).getTime()) / 60000));
  if (mins < 60) return `${mins} min ago`;
  const h = Math.round(mins / 60);
  return h < 48 ? `${h} h ago` : `${Math.round(h / 24)} d ago`;
}
