import type { SkillStep } from "@ascend/shared";
import { describe, expect, it } from "vitest";

import { layoutTrees, neighbour, NODE_H, NODE_W, stateLabel } from "./SkillTreeCanvas";

const step = (key: string, requires: string[] = [], status: SkillStep["status"] = "locked", pct = 0): SkillStep => ({
  key, name: key, exercise: key, exercise_id: null, measure: "reps", status, pct, unlocked_at: null, criteria: [], requires, xp: 0, uncertain: false, note: "",
});

describe("layoutTrees", () => {
  it("puts a step one column after the deepest step it requires and stacks branches", () => {
    const tree = { key: "t", name: "Tree", steps: [step("a", [], "unlocked"), step("b", ["a"], "next", 40), step("c", ["a"]), step("d", ["b", "c"])] };
    const l = layoutTrees([tree]);
    const at = (k: string) => l.nodes.find((n) => n.id === `t/${k}`)!;
    expect([at("a").col, at("b").col, at("c").col, at("d").col]).toEqual([0, 1, 1, 2]);
    expect(at("c").row).toBe(at("b").row + 1); // branch stacked below
    expect(l.edges).toHaveLength(4);
    expect(at("b").x - at("a").x).toBeGreaterThan(NODE_W);
    expect(at("c").y - at("b").y).toBeGreaterThanOrEqual(NODE_H);
  });

  it("chains steps with no requires to the previous step, and stacks trees", () => {
    const l = layoutTrees([
      { key: "x", name: "X", steps: [step("1"), step("2"), step("3")] },
      { key: "y", name: "Y", steps: [step("1")] },
    ]);
    expect(l.edges.map((e) => `${e.from}>${e.to}`)).toEqual(["x/1>x/2", "x/2>x/3"]);
    expect(l.nodes.find((n) => n.id === "y/1")!.row).toBeGreaterThan(0);
    expect(l.labels.map((x) => x.name)).toEqual(["X", "Y"]);
  });

  it("lays out 150+ nodes (performance budget: one pass, no quadratic blow-up)", () => {
    const trees = Array.from({ length: 20 }, (_, t) => ({
      key: `t${t}`, name: `T${t}`, steps: Array.from({ length: 8 }, (_, i) => step(`s${i}`)),
    }));
    const t0 = performance.now();
    const l = layoutTrees(trees);
    expect(l.nodes).toHaveLength(160);
    expect(performance.now() - t0).toBeLessThan(50);
  });
});

describe("keyboard movement", () => {
  const l = layoutTrees([
    { key: "x", name: "X", steps: [step("1"), step("2"), step("3")] },
    { key: "y", name: "Y", steps: [step("1"), step("2")] },
  ]);
  it("follows edges left and right, and jumps between trees up and down", () => {
    expect(neighbour(l, "x/1", "ArrowRight")).toBe("x/2");
    expect(neighbour(l, "x/2", "ArrowLeft")).toBe("x/1");
    expect(neighbour(l, "x/3", "ArrowRight")).toBeNull();
    expect(neighbour(l, "x/2", "ArrowDown")).toBe("y/2");
    expect(neighbour(l, "y/1", "ArrowUp")).toBe("x/1");
  });

  it("names every state in words", () => {
    expect(stateLabel(step("a", [], "unlocked"))).toBe("mastered");
    expect(stateLabel(step("a", [], "next", 0))).toBe("available");
    expect(stateLabel(step("a", [], "next", 72.4))).toBe("in progress, 72%");
    expect(stateLabel(step("a"))).toBe("locked");
  });
});
