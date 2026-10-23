/**
 * One action allowlist (actions-v1) for the trainer chat and the local AI:
 * packages/shared/src/command-vectors.json. The sidecar's pytest suite checks its registry,
 * parser and chat replies against the same file. Since v1.2 the chat is the one box
 * (Ctrl+K opens it), so the app has no second parser to keep in step.
 */
import type { ChatAction } from "@ascend/shared";
import { describe, expect, it } from "vitest";

import shared from "../../../../packages/shared/src/command-vectors.json";
import { isChatKey } from "./shortcuts";

describe("shared action allowlist", () => {
  it("lists the same chat UI actions the shared types allow", () => {
    const kinds: ChatAction["kind"][] = ["navigate", "tour", "planner", "trainer_picker", "proposal", "share"];
    expect([...kinds].sort()).toEqual([...shared.chat_ui].sort());
  });

  it("covers the plain logging lines the chat understands", () => {
    const texts = shared.vectors.map((v) => v.text);
    expect(texts).toEqual(expect.arrayContaining(["10 pushups", "2 idli for breakfast", "chicken breast 200g"]));
  });
});

describe("Ctrl+K", () => {
  const base = { key: "k", ctrlKey: false, metaKey: false, altKey: false, shiftKey: false };
  it("opens the trainer chat with Ctrl or Cmd, and nothing else", () => {
    expect(isChatKey({ ...base, ctrlKey: true })).toBe(true);
    expect(isChatKey({ ...base, key: "K", metaKey: true })).toBe(true);
    expect(isChatKey(base)).toBe(false);
    expect(isChatKey({ ...base, ctrlKey: true, shiftKey: true })).toBe(false);
  });
});
