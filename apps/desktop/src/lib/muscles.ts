/** Display names for the 19 ASCEND muscle regions (keys match the sidecar taxonomy). */
export const MUSCLE_LABEL: Record<string, string> = {
  upper_chest: "Upper chest", lower_chest: "Chest", front_delts: "Front delts", side_delts: "Side delts",
  rear_delts: "Rear delts", biceps: "Biceps", triceps: "Triceps", forearms: "Forearms", traps: "Traps",
  lats: "Lats", rhomboids: "Mid-back", lower_back: "Lower back", abs: "Abs", obliques: "Obliques",
  glutes: "Glutes", quads: "Quads", hamstrings: "Hamstrings", adductors: "Adductors", calves: "Calves",
};

export const muscleLabel = (key: string): string => MUSCLE_LABEL[key] ?? key;
