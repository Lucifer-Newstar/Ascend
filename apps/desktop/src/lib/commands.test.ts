import type { Exercise } from "@ascend/shared";
import { describe, expect, it } from "vitest";

import { mealTypeFor, parseCommand, rankExercises } from "./commands";

const at = (h: number) => new Date(2026, 9, 20, h, 0, 0);

describe("parseCommand", () => {
  it("reads a set with load, reps and RPE in kg or lb", () => {
    expect(parseCommand("bench 80x5 @8", "metric")[0]).toEqual({ kind: "set", query: "bench", weightKg: 80, reps: 5, rpe: 8 });
    expect(parseCommand("log back squat 100 kg × 3", "metric")[0]).toEqual({ kind: "set", query: "back squat", weightKg: 100, reps: 3, rpe: null });
    expect(parseCommand("row 135lb x 8", "metric")[0]).toMatchObject({ kind: "set", weightKg: 61.23, reps: 8 });
    // No unit: the user's units.
    expect(parseCommand("ohp 95x5", "imperial")[0]).toMatchObject({ weightKg: 43.09 });
    expect(parseCommand("bench 82,5x5", "metric")[0]).toMatchObject({ weightKg: 82.5 });
  });

  it("reads bodyweight sets and holds", () => {
    expect(parseCommand("pull-up x8", "metric")[0]).toEqual({ kind: "set", query: "pull-up", weightKg: 0, reps: 8, rpe: null });
    expect(parseCommand("push-up 20 reps", "metric")[0]).toMatchObject({ kind: "set", reps: 20 });
    expect(parseCommand("plank 45s", "metric")[0]).toEqual({ kind: "hold", query: "plank", seconds: 45, rpe: null });
    expect(parseCommand("tuck front lever 12 sec @9", "metric")[0]).toEqual({ kind: "hold", query: "tuck front lever", seconds: 12, rpe: 9 });
  });

  it("reads weigh-ins, meals, skills, theme and AI", () => {
    expect(parseCommand("weight 81.4", "metric")[0]).toEqual({ kind: "weight", kg: 81.4 });
    expect(parseCommand("bw 180 lb", "metric")[0]).toEqual({ kind: "weight", kg: 81.6 });
    expect(parseCommand("lunch chicken rice", "metric", at(9))[0]).toEqual({ kind: "meal", query: "chicken rice", mealType: "lunch" });
    expect(parseCommand("ate oats", "metric", at(8))[0]).toEqual({ kind: "meal", query: "oats", mealType: "breakfast" });
    expect(parseCommand("train front lever", "metric")[0]).toEqual({ kind: "train", query: "front lever" });
    expect(parseCommand("dark", "metric")[0]).toEqual({ kind: "theme", theme: "dark" });
    expect(parseCommand("light mode", "metric")[0]).toEqual({ kind: "theme", theme: "light" });
    expect(parseCommand("ai off", "metric")[0]).toEqual({ kind: "ai", on: false });
  });

  it("opens pages by name or alias", () => {
    expect(parseCommand("fuel", "metric")[0]).toEqual({ kind: "nav", page: "diet", label: "Fuel" });
    expect(parseCommand("go to settings", "metric")[0]).toMatchObject({ kind: "nav", page: "settings" });
    expect(parseCommand("hist", "metric")[0]).toMatchObject({ kind: "nav", page: "history" });
  });

  it("sends anything else to the Coach, and always offers the Coach last", () => {
    expect(parseCommand("why are my shoulders sore?", "metric")).toEqual([{ kind: "coach", question: "why are my shoulders sore?" }]);
    const c = parseCommand("bench 80x5", "metric");
    expect(c[c.length - 1]).toEqual({ kind: "coach", question: "bench 80x5" });
    expect(parseCommand("   ", "metric")).toEqual([]);
  });

  it("picks the meal from the hour when no meal word is used", () => {
    expect([8, 12, 18, 23].map((h) => mealTypeFor(undefined, h))).toEqual(["breakfast", "lunch", "dinner", "snack"]);
  });
});

describe("rankExercises", () => {
  const ex = (id: number, name: string, extra: Partial<Exercise> = {}): Exercise => ({
    id, name, equipment: "barbell", section: "gym", met: null, time_based: false, muscles: [], source: "free-exercise-db", ...extra,
  });
  const list = [
    ex(1, "Bench Dips", { equipment: "bodyweight" }),
    ex(2, "Barbell Bench Press", { source: "ascend", aliases: ["Barbell Bench Press - Medium Grip"] }),
    ex(3, "Dumbbell Bench Press", { equipment: "dumbbell", source: "ascend" }),
    ex(4, "Overhead Press", { source: "ascend" }),
    ex(5, "Pull-up", { equipment: "bar", source: "ascend", aliases: ["pullup", "chin-up bar pull"] }),
    ex(6, "Back Squat", { source: "ascend", aliases: ["squat"] }),
  ];
  it("prefers exact names and aliases, curated entries and loaded equipment for a loaded set", () => {
    expect(rankExercises("bench", list, 2, { weighted: true }).map((e) => e.name)).toEqual(["Barbell Bench Press", "Dumbbell Bench Press"]);
    expect(rankExercises("squat", list, 1)[0].name).toBe("Back Squat");
    expect(rankExercises("pullup", list, 1)[0].name).toBe("Pull-up");
    expect(rankExercises("pull up", list, 1)[0].name).toBe("Pull-up");
  });
  it("expands common abbreviations", () => {
    expect(rankExercises("ohp", list, 1)[0].name).toBe("Overhead Press");
    expect(rankExercises("db bench", list, 1)[0].name).toBe("Dumbbell Bench Press");
  });
  it("returns nothing for no match", () => {
    expect(rankExercises("zzz", list)).toEqual([]);
  });
});
