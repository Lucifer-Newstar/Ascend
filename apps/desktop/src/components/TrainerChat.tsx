/**
 * The trainer chat drawer. Rules answer first on the sidecar (greetings, help, tours, app
 * questions, "start fresh", goal checks), so it works with the AI off. When a reply is
 * rule-based because the model could not be used, the reason is shown under it.
 *
 * The drawer stays mounted while closed, so the conversation survives closing it.
 */
import type { ChatAction, ChatReply, FeedMessage } from "@ascend/shared";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { api } from "../api/client";
import { fallbackLabel } from "../lib/fallback";
import { useOptionalPrefs } from "../lib/prefs";
import { type TrainerMood } from "../lib/trainer";
import { ActionCard } from "./ActionCard";
import { TrainerPortrait, useTrainer } from "./Trainer";

export const START_SUGGESTIONS = ["Give me a tour", "What can you do?", "What should I train today?", "How does XP work?"];

interface Msg {
  id: number;
  role: "user" | "trainer";
  text: string;
  mood?: TrainerMood;
  reply?: ChatReply;
  notice?: FeedMessage;
  failed?: string;
}

/** Wait this long before saying the model may be loading (cold start). */
export const SLOW_AFTER_MS = 4000;

export function TrainerChat({
  open,
  onClose,
  onAction,
  supports = ["navigate", "tour"],
  greeting,
  question,
  onAsked,
  onActionDone,
}: {
  open: boolean;
  onClose: () => void;
  /** Run a reply's action (open a page, start a tour...). */
  onAction: (a: ChatAction) => void;
  /** Action kinds this build can run; others are not shown. */
  supports?: ChatAction["kind"][];
  /** A first message shown when the chat is empty (e.g. the first-run welcome). */
  greeting?: string;
  /** A question to ask as soon as the chat is open (from the command bar). */
  question?: string | null;
  /** Called once `question` has been sent, so the caller can clear it. */
  onAsked?: () => void;
  /** An action card was confirmed, cancelled or undone (refresh the page behind). */
  onActionDone?: () => void;
}) {
  const prefs = useOptionalPrefs();
  const trainer = useTrainer();
  const aiOn = prefs?.settings.ai_enabled !== false;
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [slow, setSlow] = useState(false);
  const seq = useRef(0);
  const input = useRef<HTMLInputElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const opened = useRef(false);

  const push = (m: Omit<Msg, "id">) => setMsgs((list) => [...list, { ...m, id: ++seq.current }]);

  useEffect(() => {
    if (!open) return;
    input.current?.focus();
    if (aiOn) void api.coachWarm().catch(() => undefined);
    if (opened.current) return;
    opened.current = true;
    push({ role: "trainer", mood: "neutral", text: greeting ?? "I'm here. Ask me anything about ASCEND, say \"tour\" for a walkthrough, or ask what to train." });
    api.trainerFeed().then((feed) => {
      const unread = feed.messages.filter((m) => !m.read).reverse();
      if (!unread.length) return;
      setMsgs((list) => [...list, ...unread.map((n) => ({ id: ++seq.current, role: "trainer" as const, mood: n.mood, text: n.text, notice: n }))]);
      void api.trainerFeedRead(unread.map((m) => m.id)).catch(() => undefined);
    }).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "end" });
  }, [msgs, busy]);

  useEffect(() => {
    if (!open || !question) return;
    onAsked?.();
    void ask(question);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, question]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  async function ask(q: string) {
    const question = q.trim();
    if (!question || busy) return;
    push({ role: "user", text: question });
    setText("");
    setBusy(true);
    setSlow(false);
    const timer = window.setTimeout(() => setSlow(true), SLOW_AFTER_MS);
    try {
      const reply = await api.trainerChat(question);
      push({ role: "trainer", mood: reply.mood, text: reply.reply, reply });
    } catch (e) {
      push({ role: "trainer", mood: "warning", text: `I couldn't reach the local engine: ${(e as Error).message}`, failed: question });
    } finally {
      window.clearTimeout(timer);
      setBusy(false);
      setSlow(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    void ask(text);
  }

  const last = msgs[msgs.length - 1];
  const chips = last?.reply?.suggestions.length ? last.reply.suggestions : msgs.length <= 1 ? START_SUGGESTIONS : [];

  return (
    <div
      role="dialog"
      aria-modal="false"
      aria-label="Trainer chat"
      hidden={!open}
      data-testid="trainer-chat"
      className="fixed bottom-4 right-4 top-[84px] z-40 flex w-[380px] max-w-[calc(100vw-2rem)] flex-col rounded-xl border border-line-2 bg-panel shadow-2xl"
    >
      <header className="flex items-center gap-3 border-b border-line px-4 py-3">
        <TrainerPortrait mood={(last?.role === "trainer" && last.mood) || "neutral"} size={40} />
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-sm font-semibold text-ink">{trainer.name}</h2>
          <p className="text-[11px] text-muted">{aiOn ? "Rules first, local AI for the rest" : "AI off · answering from my notes"}</p>
        </div>
        <button type="button" onClick={onClose} className="rounded-md px-2 py-1 text-muted hover:bg-panel-2 hover:text-ink" aria-label="Close chat">
          ✕
        </button>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
      <ol className="space-y-3" aria-live="polite" aria-label="Messages">
        {msgs.map((m) => (
          <li key={m.id} className={m.role === "user" ? "flex justify-end" : "flex"}>
            <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${m.role === "user" ? "bg-accent/15 text-ink" : "border border-line-2 bg-panel-2/80 text-ink"}`}>
              {m.role === "trainer" && <span className="sr-only">{trainer.name}: </span>}
              {m.notice && <span className="mb-1 block text-[10px] uppercase tracking-wider text-accent">Noticed</span>}
              <p className="whitespace-pre-wrap">{m.text}</p>
              {m.reply?.fallback_reason && <p className="mt-1 text-[11px] text-muted">{fallbackLabel(m.reply.fallback_reason)}</p>}
              {m.reply?.source === "ollama" && <p className="mt-1 text-[11px] text-muted">Worded by the local AI · numbers checked</p>}
              {m.reply?.proposal && <ActionCard initial={m.reply.proposal} onDone={() => onActionDone?.()} />}
              {(m.reply?.actions ?? []).filter((a) => supports.includes(a.kind)).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {m.reply!.actions.filter((a) => supports.includes(a.kind) && a.kind !== "proposal").map((a) => (
                    <button key={`${a.kind}-${a.target}`} type="button" className="btn-ghost px-2 py-1 text-xs" onClick={() => onAction(a)}>
                      {a.label}
                    </button>
                  ))}
                </div>
              )}
              {m.notice?.action_kind && supports.includes(m.notice.action_kind as ChatAction["kind"]) && m.notice.action_target && (
                <button type="button" className="btn-ghost mt-2 px-2 py-1 text-xs"
                  onClick={() => onAction({ kind: m.notice!.action_kind as ChatAction["kind"], target: m.notice!.action_target, label: "Open" })}>
                  Open
                </button>
              )}
              {m.failed && (
                <button type="button" className="btn-ghost mt-2 px-2 py-1 text-xs" onClick={() => void ask(m.failed!)}>
                  Retry
                </button>
              )}
            </div>
          </li>
        ))}
        {busy && (
          <li className="flex" data-testid="chat-busy">
            <div className="rounded-lg border border-line-2 bg-panel-2/60 px-3 py-2 text-xs text-muted">
              {slow && aiOn ? "Loading the local AI… the first answer after a break can take up to a minute." : "Thinking…"}
            </div>
          </li>
        )}
      </ol>
      <div ref={end} />
      </div>
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-1.5 border-t border-line px-4 py-2" aria-label="Suggestions">
          {chips.map((c) => (
            <button key={c} type="button" className="rounded-full border border-line-2 px-2.5 py-1 text-[11px] text-muted hover:border-accent/50 hover:text-ink" onClick={() => void ask(c)}>
              {c}
            </button>
          ))}
        </div>
      )}
      <form onSubmit={submit} className="flex gap-2 border-t border-line p-3">
        <label className="sr-only" htmlFor="trainer-chat-input">Message the trainer</label>
        <input id="trainer-chat-input" ref={input} className="input min-w-0 flex-1" value={text} onChange={(e) => setText(e.target.value)}
          placeholder="Ask anything, or try “give me a tour”" maxLength={1000} autoComplete="off" />
        <button type="submit" className="btn-primary px-3" disabled={busy || !text.trim()}>Send</button>
      </form>
    </div>
  );
}

/** Top-bar button that opens the chat, with a dot for unread notices. */
export function TrainerChatButton({ onOpen, unread = 0, icon, name = "your trainer" }: { onOpen: () => void; unread?: number; icon: string; name?: string }) {
  return (
    <button type="button" onClick={onOpen} data-tour="trainer"
      title={`Chat with ${name}`}
      aria-label={unread ? `Trainer chat, ${unread} new` : "Trainer chat"}
      className="relative flex items-center gap-2 rounded-full border border-accent/50 px-2 py-1 text-xs text-ink transition-colors hover:bg-accent/10">
      <img src={icon} alt="" width={22} height={22} className="rounded-full" />
      Trainer
      {unread > 0 && <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-bold text-on-accent">{unread}</span>}
    </button>
  );
}
