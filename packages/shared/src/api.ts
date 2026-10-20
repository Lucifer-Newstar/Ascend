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

/** GET /muscles/activity?days=1..30: per-muscle load over a window (map hover card). */
export interface MuscleActivity {
  key: string;
  /** Effective sets in the window (primary movers 1, secondary movers their share). */
  sets: number;
  /** Lifting volume load (weight x reps) attributed by muscle share, kg. */
  volume_kg: number;
  /** Most recent load, looking back up to 28 days. */
  last_trained: string | null;
}

export type Section = "gym" | "calisthenics" | "cardio" | "martial_arts" | "flexibility" | "meditation";

/** How a set of this exercise is measured: reps, seconds per isometric hold, or time. */
export type Measure = "reps" | "hold" | "time";
export type Difficulty = "beginner" | "intermediate" | "expert";
/** Where an exercise (or one of its fields) came from. */
export type FieldSource = "library" | "rules" | "local_ai" | "wger" | "wikipedia" | "user";

export interface Exercise {
  id: number;
  name: string;
  equipment: string;
  section: Section;
  met: number | null;
  time_based: boolean;
  muscles: { muscle: string; weight: number }[];
  slug?: string | null;
  measure?: Measure;
  difficulty?: Difficulty | null;
  pattern?: string;
  /** Thumbnail path relative to index.html, e.g. "exercises/pullups.webp". */
  image?: string | null;
  source?: "ascend" | "free-exercise-db" | "custom";
  is_custom?: boolean;
  aliases?: string[];
}

export interface SkillLink {
  skill_key: string;
  skill_name: string;
  step_name: string | null;
  /** "step": part of the tree itself; "feeder": builds strength for it. */
  role: "step" | "feeder";
}

export interface Attribution {
  source: string;
  title: string;
  url: string;
  license: string;
}

export interface ExerciseDetail extends Exercise {
  instructions: string[];
  mechanic: string | null;
  rep_low: number | null;
  rep_high: number | null;
  field_sources: Record<string, FieldSource>;
  attribution: Attribution[];
  source_ref: string | null;
  created_at: string | null;
  skills: SkillLink[];
  sets_logged: number;
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
  /** The exercise's measure ("hold" sets keep their seconds in duration_s). */
  measure?: Measure;
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
  /** Skill-tree steps this set unlocked ("Skill acquired" moments); usually empty. */
  unlocks?: SkillUnlock[];
}

// ---- skill trees ------------------------------------------------------------

export type SkillFamily = "pull" | "push" | "core" | "balance" | "legs" | "levers";
export type StepStatus = "unlocked" | "next" | "locked";

export interface SkillCriterion {
  text: string;
  exercise: string;
  exercise_id: number | null;
  sets: number;
  target: number;
  unit: "reps" | "s";
  added_kg: number;
  per_side: boolean;
  best_value: number | null;
  best_score: number;
  sessions_met: number;
  sessions_needed: number;
  pct: number;
  met: boolean;
  /** Holds beyond the plausibility limit, not counted. */
  ignored_sets: number;
}

export interface SkillStep {
  key: string;
  name: string;
  exercise: string;
  exercise_id: number | null;
  measure: Measure;
  status: StepStatus;
  pct: number;
  unlocked_at: string | null;
  criteria: SkillCriterion[];
  requires: string[];
  xp: number;
  uncertain: boolean;
  note: string;
}

export interface SkillSummary {
  key: string;
  name: string;
  family: SkillFamily;
  summary: string;
  stretch: boolean;
  current_step: string | null;
  current_step_name: string | null;
  next_step: string | null;
  next_step_name: string | null;
  pct_to_next: number | null;
  steps_unlocked: number;
  steps_total: number;
  acquired: boolean;
  last_trained: string | null;
  sessions_28d: number;
  rusty: boolean;
}

export interface SkillDetail extends SkillSummary {
  steps: SkillStep[];
  feeders: { exercise_id: number | null; name: string; measure: Measure; sets_28d: number }[];
  /** Always an estimate; days is null when there is not enough data (reason says why). */
  eta: { days: number | null; date: string | null; reason: string; is_estimate: boolean };
  sources: { key: string; title: string; url: string }[];
  engine_version: string;
}

export interface SkillUnlock {
  id: number;
  skill_key: string;
  skill_name: string;
  step_key: string;
  step_name: string;
  unlocked_at: string;
  xp: number;
  /** True when this completes the whole tree. */
  final: boolean;
  next_step_name: string | null;
  source: string;
}

export interface SkillTrainResult {
  skill_key: string;
  added: number;
  already_planned: number;
  items: string[];
  message: string;
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
  /** Calm the interface: no tilt, flips, count-ups or celebrations (the OS setting is honoured as well). */
  reduce_motion: boolean;
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
