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
  /** Onboarding answers (optional for older clients). */
  focus?: Focus | null;
  /** Equipment checklist; empty = not stated (nothing is filtered). */
  equipment?: EquipmentChoice[];
}

export type Focus = "strength" | "muscle" | "skills" | "fat_loss";
export type EquipmentChoice = "none" | "pullup_bar" | "rings" | "dumbbells" | "gym";

/** POST /profile/baseline: the Awakening baseline test. 0 or null = not done. */
export interface BaselineIn {
  pushups?: number | null;
  pullups?: number | null;
  dead_hang_s?: number | null;
  plank_s?: number | null;
  squats_60s?: number | null;
  bodyweight_kg?: number | null;
}

export interface BaselineResult extends BaselineIn {
  taken_at: string;
}

export interface BaselineOut {
  baseline: BaselineResult;
  workout_id: number;
  sets_logged: number;
  xp_awarded: number;
  level: number;
  rank: string;
  /** Skill-tree steps the baseline sets unlocked ("Skill: Step"); often none. */
  steps_unlocked: string[];
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
  baseline?: BaselineResult | null;
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
  /** recovery-v2 readiness with the population decay (k = 1): "population vs you". */
  readiness_population?: number;
  algo_version?: string;
  /** taxonomy v2: region (Chest, Back...), the muscle a head belongs to, deep layer, and
   * whether the muscle only shows recovery (no weekly set target). */
  region?: string;
  parent?: string;
  deep?: boolean;
  readiness_only?: boolean;
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

/** GET /exercises/{id}/previous: the last finished session's sets (the logger's grey "last time"). */
export interface PreviousSession {
  workout_id: number;
  day: string;
  source: WorkoutSource;
  sets: WorkoutSet[];
}

export interface LoggedSet {
  set: WorkoutSet;
  xp_awarded: number;
  previous_best_e1rm: number | null;
  /** Skill-tree steps this set unlocked ("Skill acquired" moments); usually empty. */
  unlocks?: SkillUnlock[];
}

// ---- custom exercises --------------------------------------------------------

export interface ExerciseProposal {
  section: Section;
  equipment: string;
  measure: Measure;
  pattern: string;
  difficulty: Difficulty | null;
  muscles: { muscle: string; weight: number }[];
  rep_low: number | null;
  rep_high: number | null;
  met: number | null;
  instructions: string[];
  aliases: string[];
}

export interface ExerciseMatch {
  id: number;
  name: string;
  score: number;
  via: "exact" | "alias" | "fuzzy";
  section: Section;
  image: string | null;
}

export interface StageStatus {
  status: string;
  detail: string;
  model: string | null;
  applied: string[];
}

export interface ExerciseAnalysis {
  name: string;
  proposal: ExerciseProposal;
  field_sources: Record<string, FieldSource>;
  attribution: Attribution[];
  matches: ExerciseMatch[];
  duplicate_of: ExerciseMatch | null;
  /** local model: ok | off | unavailable | error | invalid */
  ai: StageStatus;
  /** Online research: off | not_requested | ok | not_found | offline | timeout | rate_limited | error */
  online: StageStatus;
  /** field -> how far the proposal can be trusted. */
  confidence: Record<string, Confidence>;
  /** Core fields the offline stages could not support: non-empty = "not enough offline data". */
  insufficient: string[];
  /** The proposal before online research changed it, to compare or keep the offline guess. */
  offline: ExerciseProposal | null;
  offline_sources: Record<string, FieldSource>;
  research: ResearchReport | null;
}

export type Confidence = "high" | "medium" | "low";

export interface ResearchCall {
  source: "wger" | "wikipedia" | string;
  url: string;
  /** ok | not_found | offline | timeout | rate_limited | error | skipped */
  status: string;
}

export interface ResearchField {
  field: string;
  label: string;
  value: string;
  source: string;
  url: string;
  offline_value: string;
  offline_source: string;
  conflict: boolean;
}

export interface ResearchReport {
  query: string;
  /** How the lookup was allowed: the Settings toggle, or allow once. */
  consent: "setting" | "once";
  outcome: string;
  calls: ResearchCall[];
  fields: ResearchField[];
  summary: string;
  summary_url: string;
}

export interface OnlineLogEntry {
  id: number;
  at: string;
  query: string;
  sources: ResearchCall[];
  outcome: string;
  consent: "setting" | "once";
}

export interface CustomExerciseIn extends ExerciseProposal {
  name: string;
  field_sources: Record<string, FieldSource>;
  attribution: Attribution[];
}

// ---- skill trees ------------------------------------------------------------

export type SkillFamily = "pull" | "push" | "core" | "balance" | "legs" | "levers";
export type StepStatus = "unlocked" | "next" | "locked" | "start";

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
  /** A tree the user made (v1.1); it tracks like the built-in ones and pays no XP. */
  custom?: boolean;
  /** v1.2: whether the player's equipment covers this tree's moves. */
  fits_equipment?: boolean;
}

export interface CustomSkillStepIn {
  name?: string;
  exercise_id: number;
  sets: number;
  reps?: number | null;
  hold_s?: number | null;
  added_kg?: number;
}

export interface CustomSkill {
  id: number;
  key: string;
  name: string;
  family: string;
  summary: string;
  steps: { name: string; exercise: string; exercise_id: number; sets: number; reps: number | null; hold_s: number | null; added_kg: number }[];
  created_at: string;
  updated_at: string;
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

/** POST /foods (v1.2): a food of the player's own. */
export interface FoodIn {
  name: string;
  portion_label?: string;
  portion_g?: number;
  kcal: number;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
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
  /** "adaptive" once tdee-v1 has set this week's target (ADR-0018), else "formula". */
  kcal_target_source?: "formula" | "adaptive" | null;
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

/** v1.2: a missed day is kept with a reason given by the next day (no more freezes). */
export interface StreakInfo {
  current: number;
  best: number;
  /** Missed days kept with a reason in the current streak. */
  excused: number;
  active_today: boolean;
  /** Yesterday was missed and can still get its reason today (ISO date), else null. */
  reason_due: string | null;
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

/** GET /game/boss: this week's boss raid (boss-v1, ADR-0022). */
export interface BossRaid {
  week_start: string;
  week_end: string;
  name: string;
  title: string;
  hp: number;
  damage: number;
  hp_left: number;
  days_left: number;
  defeated: boolean;
  defeated_at: string | null;
  bonus_xp: number;
  hp_source: "program" | "history" | "starter";
  hp_note: string;
  titles_earned: number;
  algo_version: string;
  why: Why;
  /** boss-v2 (v1.2): tier E to S (a seasonal boss follows your level) and category. */
  tier?: string;
  category?: BossCategory;
  seasonal?: boolean;
  season?: string | null;
  season_ends?: string | null;
  /** The cosmetic a seasonal boss drops (catalog id). */
  drop?: string | null;
}

export type BossCategory = "strength" | "calisthenics" | "cardio" | "martial_arts";

/** GET /game/bosses: the boss ladder, E to S, then the seasonal bosses. */
export interface BossLadderEntry {
  name: string;
  title: string;
  /** "E".."S", or "level" for a seasonal boss (it follows your level). */
  tier: string;
  category: BossCategory;
  min_level: string;
  seasonal: boolean;
  season: string | null;
  months: number[];
  drop: string | null;
  beaten: number;
}

/** GET /game/titles: a title earned by beating a weekly boss (the only title source). */
export interface EarnedTitle {
  title: string;
  boss: string;
  week_start: string;
  earned_at: string;
}

/** GET /game/stats: one computed hunter stat (0-100) and the numbers behind it (stats-v1). */
export interface Stat {
  key: "str" | "agi" | "end" | "vit" | "int";
  label: string;
  value: number;
  formula: string;
  inputs: Record<string, number | string | null>;
}

export interface Stats {
  stats: Stat[];
  version: string;
  window_days: number;
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
  /**
   * Why a rule-based answer stands in for the model's: "ai_disabled", "ollama_unavailable",
   * "timeout", "model_error" or "guard_rejected". A tip_code starting "trainer:" means the
   * question was answered by the trainer's rules (not a training question).
   */
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
/** v1.2: dark / light / system are the 1.1 looks (free); the rest are the v1.2 themes. */
export type AppTheme = "shadow" | "crimson" | "frost" | "emerald" | "solar";
export type ThemePref = "dark" | "light" | "system" | AppTheme;
export type BackgroundArt = "on" | "dim" | "off";

/** GET /game/themes */
export interface ThemeInfo {
  key: AppTheme | "dark" | "light";
  name: string;
  tagline: string;
  free: boolean;
  unlocked: boolean;
  requirement: string;
  progress: string;
}

export interface Settings {
  ai_enabled: boolean;
  units: Units;
  theme: ThemePref;
  sessions_per_week: number;
  /** Calm the interface: no tilt, flips, count-ups or celebrations (the OS setting is honoured as well). */
  reduce_motion: boolean;
  /** Allow "Add your own exercise" to look names up on wger.de when asked. Off by default. */
  online_lookup?: boolean;
  /** v8: insights spoken by the trainer character; false = plain System mode. Default true. */
  trainer?: boolean;
  /** v1.1: which trainer speaks. */
  trainer_id?: TrainerId;
  /** v1.1: hide calorie numbers across the app (targets still work underneath). */
  hide_calories?: boolean;
  /** v1.1: local AI feedback on progress photos. Off by default; always off under 18. */
  photo_feedback?: boolean;
  /** v1.2: the theme's background art behind the pages. Default "on". */
  background_art?: BackgroundArt;
  /** v1.2: the avatar's look (body-neutral; rank shows as gear and aura). */
  avatar?: "male" | "female";
  /** v1.2: worn cosmetics, catalog ids ("" = nothing). */
  outfit?: string;
  relic?: string;
  pet?: string;
  weapon?: string;
  /** v1.2: show the optional faith-flavoured themed cosmetics. Default true. */
  themed_cosmetics?: boolean;
  /** v1.2: the trainer's reminders (desktop notification + Today bubble). Default true. */
  reminders?: boolean;
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
  /** v1.2: the anatomical name, shown only in the drill-down. */
  latin?: string;
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

// --- intelligence layer (docs/contracts/intelligence.yaml) ---------------------------

/** The "Why?" of one number: the formula in words and every input with its value. */
export interface Why {
  formula: string;
  inputs: Record<string, number | string | null>;
}

export interface MuscleRecovery {
  key: string;
  label: string;
  group: string;
  status: MuscleStatus;
  readiness: number;
  readiness_population: number;
  fatigue: number;
  capacity: number;
  half_life_h: number;
  prior_half_life_h: number;
  k: number;
  modifier: number;
  es_7d: number;
  ready_at: string | null;
  last_trained: string | null;
  top_sets: { exercise: string; dose_now: number; hours_ago: number }[];
  why: Why;
}

export interface RecoveryGroup {
  group: string;
  k: number;
  k_low: number;
  k_high: number;
  n: number;
  personal: boolean;
  alpha: number | null;
  updated_at: string | null;
}

/** GET /intelligence/recovery */
export interface RecoveryReport {
  algo_version: string;
  formula: string;
  checkin: { sleep: number; soreness: string } | null;
  groups: RecoveryGroup[];
  muscles: MuscleRecovery[];
}

/** GET /intelligence/progression/{exercise_id}: prog-v1's next target for one exercise. */
export interface ProgressionTarget {
  exercise_id: number;
  exercise: string;
  kind: "reps" | "hold" | "none";
  sets: number;
  reps: number | null;
  seconds: number | null;
  weight_kg: number;
  rpe: number | null;
  /** first | up_load | up_reps | up_time | hold | down | reset | advance | none */
  change: string;
  reason: string;
  why: string;
  explanation: Why;
  rep_range: number[] | null;
  increment_kg: number | null;
  e1rm: {
    unit: "kg" | "reps" | "s";
    current: number | null;
    best: number | null;
    last: number | null;
    trend_pct_week: number | null;
    series: { at: string; value: number }[];
  } | null;
  stalled: boolean;
  stall_sessions: number;
  skill: {
    skill_name: string;
    step_name: string;
    criterion: string;
    sessions_met: number;
    confirm_sessions: number;
  } | null;
  readiness: number | null;
  kept_until: string | null;
  deload_week: boolean;
  phrasing: "template" | "model";
  algo_version: string;
}

/** POST /intelligence/progression/{exercise_id}/decision */
export interface ProgressionDecision {
  id: number;
  exercise_id: number;
  decided_at: string;
  choice: "accepted" | "kept";
  reason: string;
  kept_until: string | null;
  algo_version: string;
}

/** GET /intelligence/stalls */
export interface StalledLift {
  exercise_id: number;
  exercise: string;
  sessions_flat: number;
  best: number | null;
  unit: "kg" | "reps" | "s";
}

/** GET /intelligence/.../explanation: a plain-language sentence for one engine number.
 * `text` is the local model's sentence only when it passed the number and phrase checks. */
export interface Explanation {
  text: string;
  template: string;
  phrasing: "model" | "template";
  model: string | null;
  fallback: string | null;
  checks: Record<string, string> | null;
  facts: string;
  version: string;
}

/** GET /intelligence/notices: the System's rare notices; `id` is stable (show once). */
export interface SystemNotice {
  id: string;
  code: "deload" | "raised" | "recovered";
  title: string;
  text: string;
  at: string;
}

// ---- diet intelligence: adaptive TDEE and weekly insights (ADR-0018, ADR-0019) ----------

/** One day of tdee-v1: the morning state after that day's weigh-in. */
export interface TdeePoint {
  day: string;
  weight_kg: number | null;
  intake_kcal: number | null;
  intake_used: boolean;
  trend_kg: number;
  tdee_kcal: number;
  sd_kcal: number;
}

export interface TdeeWeek {
  week_start: string;
  target_kcal: number;
  tdee_kcal: number;
  sd_kcal: number;
  intake_days: number;
  changed: boolean;
  from_estimate: boolean;
  reason: string;
}

/** GET /intelligence/tdee */
export interface TdeeReport {
  algo_version: string;
  status: "cold_start" | "learning" | "adaptive";
  tdee_kcal: number;
  sd_kcal: number;
  low_kcal: number;
  high_kcal: number;
  formula_tdee_kcal: number;
  formula_target_kcal: number;
  target_kcal: number;
  target_source: "formula" | "adaptive";
  target_week_start: string;
  trend_kg: number | null;
  days_of_data: number;
  weigh_ins: number;
  intake_days_7: number;
  weigh_ins_7: number;
  gate_days: number;
  paused: boolean;
  reason: string;
  series: TdeePoint[];
  weeks: TdeeWeek[];
  why: Why;
}

export interface InsightFinding {
  code: string;
  title: string;
  text: string;
  severity: number;
  numbers: Record<string, number | string>;
  why: Why;
}

export interface InsightCheck {
  code: string;
  outcome: "fired" | "quiet" | "not_enough_data";
  detail: string;
}

/** GET /intelligence/insights */
export interface DietInsights {
  algo_version: string;
  week_end: string;
  findings: InsightFinding[];
  checks: InsightCheck[];
}

// ---- workout programs (programs-v1, ADR-0020) ------------------------------------------

export interface PlanItem {
  exercise_id: number | null;
  exercise: string;
  sets: number;
  rep_low: number;
  rep_high: number;
  target_rpe: number;
  rest_s: number;
  /** prog-v1's target for the next session, e.g. "3 × 8 @ 60 kg, RPE 8". */
  target?: string | null;
  target_reason?: string | null;
  done_sets?: number;
  /** v1.2: reps, hold (rep_low/rep_high are seconds), time or distance. */
  measure?: Measure;
  /** v1.2: the logger section the exercise lives in (gym, calisthenics, ...). */
  section?: string;
}

export interface PlanDay {
  key: string;
  name: string;
  focus: string;
  /** Suggested weekday, 0 = Monday. */
  weekday: number;
  items: PlanItem[];
}

/** GET /plans/programs */
export interface ProgramSummary {
  key: string;
  name: string;
  summary: string;
  level: string;
  equipment: string;
  days_per_week: number;
  fits_equipment: boolean;
  days: PlanDay[];
  /** v1.2: gym, calisthenics, cardio, martial_arts, flexibility or meditation. */
  section?: ProgramSection;
}

export type ProgramSection = "gym" | "calisthenics" | "cardio" | "martial_arts" | "flexibility" | "meditation";

/** GET /plans/current */
export interface Plan {
  id: number;
  source: string;
  algo_version: string;
  program_key: string;
  name: string;
  started_on: string;
  days_per_week: number;
  days: PlanDay[];
  next: PlanDay;
  sessions_done: number;
  this_week_done: number;
  last_trained: string | null;
  deload_week: boolean;
  recent: { day: string; key: string; name: string }[];
  reason: string;
  why: Why;
}

/** GET /backups, POST /backup. reason: manual | daily | pre-migration | pre-restore */
export interface BackupInfo {
  path: string;
  size_bytes: number;
  sha256: string;
  created_at: string;
  schema_revision: string;
  app_version: string;
  reason: string;
  /** v1.2: how many progress photos the backup carries, and whether they were left out. */
  photos?: number;
  photos_included?: boolean;
}

/** POST /restore */
export interface RestoreResult {
  restored_from: string;
  backup_created_at: string;
  schema_revision: string;
  safety_backup: string;
}

// --- trainer (v1.1) ------------------------------------------------------------------

export type TrainerId = "iskra" | "vera" | "kai" | "dario";
export type TrainerMoodName = "neutral" | "proud" | "warning" | "hyped";
export type FallbackReason = "ai_disabled" | "ollama_unavailable" | "timeout" | "model_error" | "guard_rejected";

export interface ChatAction {
  kind: "navigate" | "tour" | "planner" | "trainer_picker" | "proposal" | "share";
  target: string | null;
  label: string;
}

export interface ChatReply {
  reply: string;
  mood: TrainerMoodName;
  intent: string;
  source: "rules" | "faq" | "ollama";
  fallback_reason: FallbackReason | null;
  actions: ChatAction[];
  suggestions: string[];
  faq_id: string | null;
  /** An action the chat proposes (actions-v1); it runs only after Confirm on its card. */
  proposal: ActionProposal | null;
}

export interface FeedMessage {
  id: number;
  kind: string;
  mood: TrainerMoodName;
  text: string;
  action_kind: string | null;
  action_target: string | null;
  share: Record<string, unknown> | null;
  created_at: string;
  read: boolean;
}

export interface TrainerFeed {
  messages: FeedMessage[];
  unread: number;
  algo_version: string;
}

export interface TrainerState {
  onboarded: boolean;
  has_profile: boolean;
  has_history: boolean;
  demo_data: boolean;
  trainer_id: TrainerId;
  tours_done: string[];
}

export interface KbEntry {
  id: string;
  question: string;
  section: string | null;
}

export interface EraseResult {
  erased: Record<string, number>;
  /** The "pre-erase" safety backup's file name (null for an in-memory database). */
  safety_backup: string | null;
}

// --- in-app actions (actions-v1, docs/contracts/actions.yaml) --------------------------

export type ActionStatus = "proposed" | "executed" | "cancelled" | "undone" | "failed";

export interface ActionProposal {
  id: number;
  kind: string;
  label: string;
  risk: string;
  params: Record<string, unknown>;
  /** Plain lines: what will happen, shown on the confirm card. */
  summary: string[];
  status: ActionStatus | string;
  source: string;
  origin_text: string | null;
  /** A word to type before a risky action runs (erase: "erase"). */
  confirm_word: string | null;
  undoable: boolean;
  auto_ok: boolean;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  executed_at: string | null;
  undone_at: string | null;
}

// --- planner (docs/contracts/planner.yaml) ------------------------------------------------

export type PlanFocus = "strength" | "muscle" | "fat_loss" | "skills" | "general";
export type PlanExperience = "beginner" | "intermediate" | "advanced";
export type PlanEquipment = "none" | "pullup_bar" | "rings" | "dumbbells" | "gym";
export type DietKind = "veg" | "egg" | "nonveg";

export interface PlanFlag {
  code: string;
  severity: "info" | "warn" | "block";
  message: string;
  numbers?: Record<string, number>;
}

export interface GoalCheckIn {
  weight_kg?: number | null;
  target_weight_kg?: number | null;
  weeks?: number | null;
  kcal?: number | null;
  protein_g?: number | null;
  days_per_week?: number | null;
  minutes?: number | null;
  experience?: PlanExperience | null;
}

export interface GoalCheck {
  flags: PlanFlag[];
  worst: "info" | "warn" | "block" | null;
  algo_version: string;
}

export interface PlanSlot {
  exercise: string;
  exercise_id?: number | null;
  sets: number;
  rep_low: number;
  rep_high: number;
  target_rpe?: number;
  rest_s?: number;
}

export interface PlanDayDraft {
  key: string;
  name: string;
  focus?: string;
  weekday: number;
  slots: PlanSlot[];
}

export interface ProgramDraft {
  name: string;
  summary?: string;
  level?: string;
  equipment?: string;
  days: PlanDayDraft[];
  notes?: string[];
}

export interface WorkoutPlanIn {
  focus: PlanFocus;
  experience?: PlanExperience | null;
  days_per_week: number;
  minutes: number;
  equipment?: PlanEquipment[] | null;
  use_ai?: boolean;
  /** v1.2: generate for one section (cardio, martial arts, mobility and calm use section rules). */
  section?: ProgramSection | null;
}

export interface WorkoutPlan {
  draft: ProgramDraft;
  flags: PlanFlag[];
  phrased_by: string;
  algo_version: string;
}

export interface CustomProgram extends ProgramDraft {
  id: number;
  key: string;
  algo_version: string;
  created_at: string;
  updated_at: string;
  following: boolean;
}

export interface DietPlanFood {
  food: string;
  portions: number;
  portion_label: string;
  kcal: number;
  protein_g: number;
}

export interface DietPlanMeal {
  meal: string;
  items: DietPlanFood[];
  kcal: number;
  protein_g: number;
}

export interface DietPlanDay {
  day: number;
  meals: DietPlanMeal[];
  kcal: number;
  protein_g: number;
}

export interface DietPlan {
  kcal_target: number;
  protein_target_g: number;
  diet: DietKind;
  days: DietPlanDay[];
  notes: string[];
  flags: PlanFlag[];
  phrased_by: string;
  algo_version: string;
}

export interface SavedDiet {
  id: number;
  name: string;
  created_at: string;
  active: boolean;
  plan: DietPlan;
}

// --- progress photos and share cards (v1.1, docs/contracts/photos.yaml, share.yaml) ----

export type PhotoPose = "front" | "side" | "back" | "other";

export interface ProgressPhoto {
  id: number;
  taken_on: string;
  pose: PhotoPose | string;
  note: string;
  mime: string;
  bytes: number;
  created_at: string;
}

export interface PhotoFeedbackStatus {
  enabled: boolean;
  available: boolean;
  model: string;
  reason: string;
}

export interface PhotoFeedback {
  text: string;
  guarded: boolean;
  model: string;
  version: string;
  is_ai: boolean;
}

export interface ShareCardText {
  kind: string;
  title: string;
  headline: string;
  detail: string;
  caption: string;
  x_url: string;
  version: string;
}

// --- AI setup (ai-tiers-v1) ------------------------------------------------------------

export interface AiSetup {
  ai_enabled: boolean;
  tier: "rules" | "ai";
  ollama_installed: boolean;
  ollama_running: boolean;
  ollama_version: string | null;
  models: { name: string; size_gb: number }[];
  model: string;
  model_installed: boolean;
  recommended: { model: string | null; size_gb: number | null; reason: string; pull_command: string | null };
  hardware: { ram_gb: number | null; vram_gb: number | null; gpu: string | null };
  failures: number;
  suggestion: string | null;
  smaller_model: string | null;
  vision: { model: string; installed: boolean; pull_command: string };
  algo_version: string;
}

export interface AiTest {
  ok: boolean;
  model: string;
  seconds: number;
  reason: FallbackReason | null;
  reply: string;
}

export interface CoachWarm {
  loaded: boolean;
  model: string;
  seconds: number;
}

/** GET /meals/guide (v1.2): India's food guidelines (ICMR-NIN 2024) and the day's plate check. */
export interface FoodGuide {
  day: string;
  source: string;
  version: string;
  guidelines: { title: string; detail: string }[];
  foods_logged: number;
  groups: { key: string; label: string; count: number; core: boolean }[];
  missing: string[];
  hfss: string[];
  tips: string[];
}

