/**
 * Response/request types of the sidecar API, kept in sync by hand with the
 * Pydantic schemas in services/sidecar/app/modules/<module>/schemas.py.
 * (Phase 2: generate these from /openapi.json with openapi-typescript.)
 */

export type Sex = "male" | "female";
export type Goal = "cut" | "maintain" | "bulk";
export type Activity = "sedentary" | "light" | "moderate" | "active" | "very_active";
export type MuscleStatus = "under" | "optimal" | "recovering" | "over" | "no_data";
export type MealType = "breakfast" | "lunch" | "dinner" | "snack";

export interface ProfileIn {
  name: string;
  age: number;
  sex: Sex;
  height_cm: number;
  weight_kg: number;
  goal: Goal;
  activity: Activity;
}

export interface EnergyTargets {
  bmr: number;
  tdee: number;
  kcal_target: number;
  protein_target_g: number;
  formula_version: string;
  is_estimate: boolean;
}

export interface Profile extends ProfileIn {
  energy: EnergyTargets;
}

export interface MuscleState {
  key: string;
  label: string;
  group: string;
  map_slug: string;
  status: MuscleStatus;
  es_7d: number;
  weekly_low: number;
  weekly_high: number;
  readiness: number;
  ready_at: string | null;
}

export interface Exercise {
  id: number;
  name: string;
  equipment: string;
  muscles: { muscle: string; weight: number }[];
}

export interface WorkoutSet {
  id: number;
  exercise_id: number;
  exercise_name: string;
  weight_kg: number;
  reps: number;
  rpe: number | null;
  e1rm: number | null;
  is_pr: boolean;
  performed_at: string;
}

export interface Workout {
  id: number;
  day: string;
  started_at: string;
  finished_at: string | null;
  sets: WorkoutSet[];
}

export interface LoggedSet {
  set: WorkoutSet;
  xp_awarded: number;
  previous_best_e1rm: number | null;
}

export interface FinishedWorkout {
  workout: Workout;
  xp_awarded: number;
  active_minutes: number;
  hard_sets: number;
}

export interface Food {
  id: number;
  name: string;
  portion_label: string;
  portion_g: number;
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  source: string;
}

export interface MealItem {
  id: number;
  food_id: number;
  food_name: string;
  portions: number;
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface Meal {
  id: number;
  day: string;
  meal_type: MealType;
  logged_at: string;
  items: MealItem[];
  kcal: number;
}

export interface Totals {
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface DayLog {
  day: string;
  meals: Meal[];
  totals: Totals;
  kcal_target: number | null;
  protein_target_g: number | null;
  values_are_approximate: boolean;
}

export interface QuestItem {
  id: number;
  day: string;
  kind: "training" | "nutrition" | "recovery";
  code: string;
  title: string;
  detail: string;
  metric: string;
  target: number;
  progress: number;
  xp: number;
  completed_at: string | null;
}

export interface XpInfo {
  total: number;
  today: number;
  level: number;
  xp_into_level: number;
  xp_for_next: number;
  rank: string;
  rank_title: string;
  daily_cap: number;
  formula_version: string;
}

export interface StreakInfo {
  current: number;
  best: number;
  freezes_held: number;
  freezes_used: number;
  active_today: boolean;
}

export interface GameSummary {
  xp: XpInfo;
  streak: StreakInfo;
  quest: QuestItem[];
}

export interface Ring {
  value: number;
  target: number;
  label: string;
  is_estimate: boolean;
}

export interface Dashboard {
  date: string;
  has_profile: boolean;
  rings: { tasks: Ring; kcal_in: Ring; kcal_out: Ring };
  nutrition: Totals;
  game: GameSummary;
  muscles: MuscleState[];
}

export interface CoachReply {
  source: "rules" | "ollama";
  text: string;
  tip_code: string;
  model: string | null;
  fallback_reason: string | null;
}

export interface CoachStatus {
  ai_enabled: boolean;
  ollama_available: boolean;
  model: string;
}

export interface HistoryDay {
  day: string;
  workouts: Workout[];
  meals: Meal[];
  kcal_in: number;
  sets: number;
  xp: number;
}
