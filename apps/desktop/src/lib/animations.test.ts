import { existsSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { ANIMATED, animationFor, slugOf } from "./animations";

const PUBLIC = join(__dirname, "..", "..", "public", "exercises");

describe("exercise animations", () => {
  it("ships an animation and a first-frame still for every animated move, each small", () => {
    expect(ANIMATED.size).toBeGreaterThanOrEqual(25);
    for (const slug of ANIMATED) {
      const anim = join(PUBLIC, `${slug}-anim.webp`);
      expect(existsSync(anim), anim).toBe(true);
      expect(existsSync(join(PUBLIC, `${slug}.webp`)), slug).toBe(true);
      expect(statSync(anim).size).toBeLessThan(160_000);
    }
  });

  it("finds a move by its photo or, without one, by its name", () => {
    expect(slugOf("Jab-Cross Shadow Drill")).toBe("jab-cross-shadow-drill");
    expect(animationFor({ name: "Push-ups", image: "exercises/pushups.webp" })).toEqual({ anim: "exercises/pushups-anim.webp", still: "exercises/pushups.webp" });
    expect(animationFor({ name: "Roundhouse Kick Drill", image: null })?.anim).toBe("exercises/roundhouse-kick-drill-anim.webp");
    expect(animationFor({ name: "Archer Pull-up", image: "exercises/archer-pull-up.webp" })).toBeNull();
  });
});
