/**
 * One action allowlist (actions-v1) for the command bar, the trainer chat and the local AI:
 * packages/shared/src/command-vectors.json. The sidecar's pytest suite checks its registry,
 * parser and chat replies against the same file.
 */
import type { ChatAction } from "@ascend/shared";
import { describe, expect, it } from "vitest";

import shared from "../../../../packages/shared/src/command-vectors.json";
import { COMMAND_ACTIONS, parseCommand, UI_COMMANDS } from "./commands";

type Vector = { text: string; kind: string | null; params?: Record<string, number | string> };
const allowed = new Map(shared.actions.map((a) => [a.kind, a]));

describe("shared action allowlist", () => {
  it("maps every data-changing command to an allowlisted action and nothing else", () => {
    for (const [command, kind] of Object.entries(COMMAND_ACTIONS)) {
      expect(allowed.get(kind)?.command).toBe(command);
    }
    const fromFile = shared.actions.filter((a) => a.command).map((a) => [a.command, a.kind]);
    expect(Object.fromEntries(fromFile)).toEqual(COMMAND_ACTIONS);
    expect([...UI_COMMANDS]).toEqual(shared.ui);
  });

  it("lists the same chat UI actions the shared types allow", () => {
    const kinds: ChatAction["kind"][] = ["navigate", "tour", "planner", "trainer_picker", "proposal", "share"];
    expect([...kinds].sort()).toEqual([...shared.chat_ui].sort());
  });

  it.each(shared.vectors as Vector[])("parses “$text” the way the sidecar does", (v) => {
    const first = parseCommand(v.text, "metric", new Date("2026-10-23T13:00:00"))[0];
    if (v.kind === null) {
      expect(first && first.kind in COMMAND_ACTIONS).toBe(false);
      return;
    }
    expect(first.kind).toBe(allowed.get(v.kind)!.command);
    const p = v.params!;
    if (first.kind === "set") {
      expect(first.query).toBe(p.exercise);
      expect(first.reps).toBe(p.reps);
      expect(first.weightKg).toBeCloseTo(Number(p.weight_kg));
      expect(first.sets ?? 1).toBe(p.sets);
      if (p.rpe !== undefined) expect(first.rpe).toBe(p.rpe);
    } else if (first.kind === "hold") {
      expect(first.query).toBe(p.exercise);
      expect(first.seconds).toBe(p.seconds);
    } else if (first.kind === "weight") {
      expect(first.kg).toBeCloseTo(Number(p.weight_kg), 1);
    } else if (first.kind === "meal") {
      expect(first.query).toBe(p.food);
      expect(first.portions ?? 1).toBe(p.portions);
      if (p.meal_type !== undefined) expect(first.mealType).toBe(p.meal_type);
    }
  });
});
