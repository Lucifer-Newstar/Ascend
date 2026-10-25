import { describe, expect, it } from "vitest";

import { allowedEquipment, fitsKit, hasGymKit, needsBench, needsLabel, hunterClass } from "./loadout";

describe("loadout", () => {
  it("filters nothing without a checklist or with a gym", () => {
    expect(allowedEquipment([])).toBeNull();
    expect(allowedEquipment(undefined)).toBeNull();
    expect(allowedEquipment(["gym", "none"])).toBeNull();
  });

  it("lets floor moves through and adds what each piece of kit unlocks", () => {
    const none = allowedEquipment(["none"]);
    expect(fitsKit("bodyweight", none)).toBe(true);
    expect(fitsKit("barbell", none)).toBe(false);
    expect(fitsKit("bar", none)).toBe(false);
    const bar = allowedEquipment(["pullup_bar", "rings"]);
    expect(fitsKit("bar", bar)).toBe(true);
    expect(fitsKit("rings", bar)).toBe(true);
    expect(fitsKit(null, bar)).toBe(true);
  });

  it("counts rings as a bar and keeps bench presses for a bench (v1.3)", () => {
    const rings = allowedEquipment(["rings"]);
    expect(fitsKit("bar", rings, "Pull-up")).toBe(true);
    const db = allowedEquipment(["dumbbells"]);
    expect(fitsKit("dumbbell", db, "Dumbbell Bench Press")).toBe(false);
    expect(fitsKit("dumbbell", db, "Dumbbell Floor Press")).toBe(true);
    expect(needsLabel("dumbbell", "Dumbbell Bench Press", db)).toBe("needs: a bench");
    expect(fitsKit("dumbbell", allowedEquipment(["dumbbells", "bench"]), "Incline Dumbbell Press")).toBe(true);
    expect(fitsKit("barbell", allowedEquipment(["gym"]), "Barbell Bench Press")).toBe(true);
    expect(needsBench("Bench Dips")).toBe(false);
  });

  it("says what a locked move needs, and when Train starts on gym", () => {
    expect(needsLabel("barbell")).toBe("needs: a barbell");
    expect(needsLabel("sandbag")).toBe("needs: sandbag");
    expect(hasGymKit(["none"])).toBe(false);
    expect(hasGymKit(["dumbbells"])).toBe(true);
    expect(hasGymKit([])).toBe(true);
  });

  it("names your class from your kit", () => {
    expect(hunterClass([]).name).toBe("Home Hunter");
    expect(hunterClass(["none"]).name).toBe("Home Hunter");
    expect(hunterClass(["pullup_bar"]).name).toBe("Bar Ronin");
    expect(hunterClass(["pullup_bar", "rings"]).name).toBe("Calisthenics Ronin");
    expect(hunterClass(["rings", "dumbbells"]).name).toBe("Iron Duelist");
    expect(hunterClass(["dumbbells", "gym"]).name).toBe("Iron Lifter");
  });
});
