/**
 * The trainer conversation, shared by the chat drawer and the Chat page (v1.3), so moving
 * between them keeps the thread. It lives for the app session, like the drawer did.
 */
import type { ChatReply, FeedMessage } from "@ascend/shared";
import { useSyncExternalStore } from "react";

import type { TrainerMood } from "./trainer";

export interface ChatMsg {
  id: number;
  role: "user" | "trainer";
  text: string;
  mood?: TrainerMood;
  reply?: ChatReply;
  notice?: FeedMessage;
  failed?: string;
}

let msgs: ChatMsg[] = [];
let seq = 0;
let started = false;
const subs = new Set<() => void>();
const emit = () => subs.forEach((fn) => fn());

export const chatStore = {
  get: (): ChatMsg[] => msgs,
  subscribe(fn: () => void): () => void {
    subs.add(fn);
    return () => subs.delete(fn);
  },
  push(...items: Omit<ChatMsg, "id">[]): void {
    msgs = [...msgs, ...items.map((m) => ({ ...m, id: ++seq }))];
    emit();
  },
  /** True the first time it is called in a session: the greeting and unread notices go in once. */
  start(): boolean {
    if (started) return false;
    started = true;
    return true;
  },
};

/** Test helper: an empty conversation. */
export function resetChat(): void {
  msgs = [];
  seq = 0;
  started = false;
  emit();
}

export function useChatMessages(): ChatMsg[] {
  return useSyncExternalStore(chatStore.subscribe, chatStore.get, chatStore.get);
}

/** The mood of the trainer's latest line (the portraits follow it). */
export function latestMood(list: ChatMsg[]): TrainerMood {
  const last = list[list.length - 1];
  return (last?.role === "trainer" && last.mood) || "neutral";
}
