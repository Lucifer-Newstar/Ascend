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
  target_weight_kg?: number | null;
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

export type Section = "gym" | "calisthenics" | "cardio" | "martial_arts" | "flexibility" | "meditation";

export interface Exercise {
  id: number;
  name: string;
  equipment: string;
  section: Section;
  met: number | null;
  time_based: boolean;
  muscles: { muscle: string; weight: number }[];
}

export interface WorkoutSet {
  id: number;
  exercise_id: number;
  exercise_name: string;
  weight_kg: number;
  reps: number;
  rpe: number | null;
  duration_s: number | null;
  distance_m: number | null;
  avg_hr: number | null;
  e1rm: number | null;
  is_pr: boolean;
  performed_at: string;
}

export interface SetIn {
  exercise_id: number;
  weight_kg?: number;
  reps?: number;
  rpe?: number | null;
  duration_s?: number | null;
  distance_m?: number | null;
  avg_hr?: number | null;
}

export type SetPatch = Partial<Pick<SetIn, "rpe" | "duration_s" | "distance_m">> & {
  weight_kg?: number;
  reps?: number;
};

export interface Workout {
  id: number;
  day: string;
  section: Section;
  started_at: string;
  finished_at: string | null;
  sets: WorkoutSet[];
  /** "app" for sessions logged in ASCEND, else the app it was imported from. */
  source: WorkoutSource;
  /** The other app's workout name (imports only). */
  title: string;
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

export interface CalmStreak {
  current: number;
  best: number;
  active_today: boolean;
}

export interface GameSummary {
  xp: XpInfo;
  streak: StreakInfo;
  calm: CalmStreak;
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
  /** "ai_disabled", "ollama_unavailable", "ollama_error: …" or "check_failed: numbers|banned". */
  fallback_reason: string | null;
  /** Validator results for a model reply, e.g. {numbers: "pass", banned: "pass"}. */
  checks?: Record<string, string> | null;
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

// --- settings -------------------------------------------------------------------

export type Units = "metric" | "imperial";
export type ThemePref = "dark" | "light" | "system";

export interface Settings {
  ai_enabled: boolean;
  units: Units;
  theme: ThemePref;
  sessions_per_week: number;
}

// --- progress ---------------------------------------------------------------------

export interface WorkoutSummary {
  id: number;
  day: string;
  section: Section;
  started_at: string;
  finished_at: string | null;
  sets: number;
  volume_kg: number;
  xp: number;
  source: WorkoutSource;
  title: string;
}

export interface BodyMetric {
  id: number;
  measured_at: string;
  weight_kg: number;
  trend_kg: number;
  waist_cm: number | null;
  resting_hr: number | null;
}

export type MeasurementSite = "waist" | "hips" | "chest" | "arm" | "thigh" | "calf" | "neck";

export interface Measurement {
  id: number;
  measured_at: string;
  site: MeasurementSite;
  cm: number;
  change_cm: number | null;
}

export interface Eta {
  goal_kg: number | null;
  current_trend_kg: number | null;
  rate_kg_per_week: number | null;
  eta_from: string | null;
  eta_to: string | null;
  confidence: "low" | "medium" | "high";
  on_track: boolean;
  reason: string | null;
  formula_version: string;
  note: string;
}

export interface WeekSummary {
  week_start: string;
  sessions: number;
  sets: number;
  volume_kg: number;
  active_minutes: number;
  xp: number;
  avg_kcal_in: number | null;
  avg_weight_kg: number | null;
}

export interface PersonalRecord {
  exercise_id: number;
  exercise: string;
  type: string;
  value: number;
  weight_kg: number;
  reps: number;
  formula: string;
  algo_version: string;
  achieved_at: string;
  set_id: number;
}

export interface MuscleDay {
  day: string;
  eff_sets: number;
  readiness: number;
}

export interface MuscleHistory {
  code: string;
  label: string;
  days: number;
  status: MuscleStatus;
  es_7d: number;
  target_low: number;
  target_high: number;
  readiness: number;
  ready_at: string | null;
  daily: MuscleDay[];
  contributing_sets: { set_id: number; at: string; exercise: string; weight: number; effort: number; es: number }[];
  suggestion: string | null;
  formula_version: string;
}

// --- readiness, deload, weekly review -------------------------------------------------

export type Soreness = "none" | "some" | "a_lot";

export interface CheckinIn {
  sleep: number;
  energy: number;
  soreness: Soreness;
  mood: number;
}

export interface Checkin extends CheckinIn {
  day: string;
  readiness: number;
  band: "green" | "amber" | "red";
  quest_adjustment: string;
  algo_version: string;
}

export interface DeloadAdvice {
  recommended: boolean;
  kind: "planned" | "reactive" | "active" | "none";
  training_weeks: number;
  signals: { code: string; active: boolean; detail: string }[];
  guidance: string | null;
  deload_week: string | null;
  algo_version: string;
}

export interface ReviewFinding {
  code: string;
  severity: number;
  title: string;
  detail: string;
  proposal: string | null;
  numbers: Record<string, unknown>;
}

export interface WeeklyReview {
  week_start: string;
  week_end: string;
  sessions_done: number;
  sessions_planned: number;
  findings: ReviewFinding[];
  top: ReviewFinding[];
  summary: string;
  summary_source: "model" | "template";
  algo_version: string;
}

// --- import / export (docs/contracts/import-export.yaml) ---------------------------

export type WorkoutSource = "app" | "strong" | "hevy";
export type ImportSource = "strong" | "hevy";

/** The CSV travels as text: IPC carries JSON only. */
export interface ImportIn {
  csv: string;
  /** Default true: report only, write nothing. */
  dry_run?: boolean;
  /** Strong's 2025 export has no unit column. */
  unit?: "kg" | "lb";
  include_warmups?: boolean;
}

export interface ImportReport {
  format: "strong_csv" | "strong_csv_2025" | "hevy_csv" | "ascend_plan_csv";
  workouts: number;
  sets: number;
  unmatched_exercises: string[];
  warnings: string[];
  dry_run: boolean;
  skipped_duplicates: number;
  skipped_warmups: number;
  /** Source exercise name -> ASCEND library name. */
  matched_exercises: Record<string, string>;
}
