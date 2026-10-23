/**
 * Renderer-side API client.
 *
 * Inside Electron every call goes through `window.ascend.request` (preload ->
 * IPC -> main -> sidecar), so the renderer never sees the auth token.
 * In plain-browser development (`npm run dev` + `python -m app --dev`) it
 * falls back to fetch() against http://127.0.0.1:8765 with the dev token.
 */
import type {
  FoodGuide,
  AscendBridge,
  BackupInfo,
  BossRaid,
  EarnedTitle,
  RestoreResult,
  BodyMetric,
  Checkin,
  CheckinIn,
  DeloadAdvice,
  Explanation,
  ProgressionDecision,
  ProgressionTarget,
  RecoveryReport,
  StalledLift,
  SystemNotice,
  DietInsights,
  Plan,
  ProgramSummary,
  TdeeReport,
  Eta,
  Measurement,
  MeasurementSite,
  MuscleActivity,
  MuscleHistory,
  PersonalRecord,
  Section,
  SetIn,
  SetPatch,
  Settings,
  WeekRecap,
  WeekSummary,
  WeeklyReview,
  WorkoutSummary,
  WorkoutSet,
  CoachReply,
  CoachStatus,
  CoachWarm,
  ChatReply,
  ActionProposal,
  PhotoFeedback,
  PhotoFeedbackStatus,
  PhotoPose,
  ProgressPhoto,
  ShareCardText,
  CustomProgram,
  DietKind,
  DietPlan,
  GoalCheck,
  GoalCheckIn,
  ProgramDraft,
  SavedDiet,
  WorkoutPlan,
  WorkoutPlanIn,
  TrainerFeed,
  TrainerState,
  KbEntry,
  AiSetup,
  AiTest,
  EraseResult,
  Dashboard,
  DayLog,
  Exercise,
  ExerciseDetail,
  ExerciseAnalysis,
  CustomExerciseIn,
  OnlineLogEntry,
  SkillDetail,
  SkillFamily,
  CustomSkill,
  CustomSkillStepIn,
  SkillSummary,
  SkillTrainResult,
  SkillUnlock,
  FinishedWorkout,
  Food,
  FoodIn,
  BossLadderEntry,
  GameSummary,
  StreakInfo,
  ThemeInfo,
  HistoryDay,
  ImportIn,
  ImportReport,
  ImportSource,
  HttpMethod,
  LoggedSet,
  MealType,
  MuscleState,
  Profile,
  PreviousSession,
  BaselineIn,
  BaselineOut,
  Stats,
  ProfileIn,
  QuestItem,
  Workout,
} from "@ascend/shared";

declare global {
  interface Window {
    ascend?: AscendBridge;
  }
}

// Browser dev mode: the Vite dev/preview server proxies /api to the sidecar, so requests
// are same-origin and the sidecar needs no CORS (see vite.config.mts).
const DEV_URL: string = import.meta.env.VITE_SIDECAR_URL ?? "/api";
const DEV_TOKEN: string = import.meta.env.VITE_SIDECAR_TOKEN ?? "dev";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

/** FastAPI errors are {detail: string} or {detail: [{msg}]} (validation). */
export function errorMessage(data: unknown): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: string; loc?: unknown[] };
      const field = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1]) : "";
      return field ? `${field}: ${first.msg}` : (first.msg ?? "invalid input");
    }
  }
  return "request failed";
}

async function call<T>(method: HttpMethod, path: string, body?: unknown): Promise<T> {
  if (window.ascend) {
    const res = await window.ascend.request<T>({ method, path, body });
    if (!res.ok) throw new ApiError(res.status, errorMessage(res.data));
    return res.data;
  }
  let res: Response;
  try {
    res = await fetch(DEV_URL + path, {
      method,
      headers: {
        Authorization: `Bearer ${DEV_TOKEN}`,
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Can't reach the local engine. Is the sidecar running?");
  }
  if (res.status === 204) {
    await res.text(); // drain the empty body; an unread stream shows up as an aborted request
    return null as T;
  }
  const type = res.headers.get("content-type") ?? "";
  const data: unknown = type.includes("json") ? await res.json() : await res.text();
  if (!res.ok) throw new ApiError(res.status, errorMessage(data));
  return data as T;
}

export const api = {
  backups: () => call<BackupInfo[]>("GET", "/backups"),
  backupNow: (includePhotos = true) => call<BackupInfo>("POST", "/backup", includePhotos ? undefined : { include_photos: false }),
  restoreBackup: (path: string) => call<RestoreResult>("POST", "/restore", { path }),
  dashboard: () => call<Dashboard>("GET", "/dashboard"),
  profile: () => call<Profile>("GET", "/profile"),
  saveProfile: (p: ProfileIn) => call<Profile>("PUT", "/profile", p),
  baseline: (b: BaselineIn) => call<BaselineOut>("POST", "/profile/baseline", b),
  settings: () => call<Settings>("GET", "/settings"),
  themes: () => call<ThemeInfo[]>("GET", "/game/themes"),
  setAi: (enabled: boolean) => call<Settings>("PUT", "/settings", { ai_enabled: enabled }),
  updateSettings: (patch: Partial<Settings>) => call<Settings>("PUT", "/settings", patch),
  muscles: () => call<MuscleState[]>("GET", "/muscles"),

  exercises: (q = "", section?: Section) =>
    call<Exercise[]>("GET", `/exercises?q=${encodeURIComponent(q)}${section ? `&section=${section}` : ""}`),
  exercise: (id: number) => call<ExerciseDetail>("GET", `/exercises/${id}`),
  previousSession: (id: number) => call<PreviousSession | null>("GET", `/exercises/${id}/previous`),
  analyzeExercise: (body: { name: string; equipment?: string | null; notes?: string; online?: boolean; allow_once?: boolean }) =>
    call<ExerciseAnalysis>("POST", "/exercises/analyze", body),
  onlineLog: (limit = 100) => call<OnlineLogEntry[]>("GET", `/exercises/online-log?limit=${limit}`),
  clearOnlineLog: () => call<void>("DELETE", "/exercises/online-log"),
  createExercise: (body: CustomExerciseIn) => call<ExerciseDetail>("POST", "/exercises", body),
  archiveExercise: (id: number) => call<void>("DELETE", `/exercises/${id}`),
  skills: () => call<SkillSummary[]>("GET", "/skills"),
  /** v1.2: every tree with its steps in one call. */
  skillDetails: () => call<SkillDetail[]>("GET", "/skills/details"),
  skill: (key: string) => call<SkillDetail>("GET", `/skills/${encodeURIComponent(key)}`),
  skillUnlocks: (limit = 10) => call<SkillUnlock[]>("GET", `/skills/unlocks?limit=${limit}`),
  customSkills: () => call<CustomSkill[]>("GET", "/skills/custom"),
  createCustomSkill: (body: { name: string; family: SkillFamily; summary?: string; steps: CustomSkillStepIn[] }) => call<CustomSkill>("POST", "/skills/custom", body),
  deleteCustomSkill: (id: number) => call<null>("DELETE", `/skills/custom/${id}`),
  trainSkill: (key: string) => call<SkillTrainResult>("POST", `/skills/${encodeURIComponent(key)}/train`),
  activeWorkout: () => call<Workout | null>("GET", "/workouts/active"),
  startWorkout: (section: Section = "gym") => call<Workout>("POST", `/workouts?section=${section}`),
  /** Next page: pass the last item's started_at and id (ids break ties between sessions
   *  that started in the same second). */
  workouts: (limit = 20, before?: string, beforeId?: number) =>
    call<WorkoutSummary[]>(
      "GET",
      `/workouts?limit=${limit}${before ? `&before=${encodeURIComponent(before)}` : ""}${
        before && beforeId ? `&before_id=${beforeId}` : ""
      }`,
    ),
  logSet: (workoutId: number, s: SetIn) => call<LoggedSet>("POST", `/workouts/${workoutId}/sets`, s),
  editSet: (workoutId: number, setId: number, patch: SetPatch) =>
    call<WorkoutSet>("PATCH", `/workouts/${workoutId}/sets/${setId}`, patch),
  deleteSet: (workoutId: number, setId: number) => call<null>("DELETE", `/workouts/${workoutId}/sets/${setId}`),
  prs: () => call<PersonalRecord[]>("GET", "/prs"),
  deload: () => call<DeloadAdvice>("GET", "/deload"),
  progression: (exerciseId: number) => call<ProgressionTarget>("GET", `/intelligence/progression/${exerciseId}`),
  decideProgression: (exerciseId: number, choice: "accepted" | "kept") =>
    call<ProgressionDecision>("POST", `/intelligence/progression/${exerciseId}/decision`, { choice }),
  recovery: () => call<RecoveryReport>("GET", "/intelligence/recovery"),
  stalls: () => call<StalledLift[]>("GET", "/intelligence/stalls"),
  notices: () => call<SystemNotice[]>("GET", "/intelligence/notices"),
  programs: () => call<ProgramSummary[]>("GET", "/plans/programs"),
  /** null when no program is chosen yet (v1.2: a normal answer, not a 404). */
  currentPlan: () => call<Plan | null>("GET", "/plans/current"),
  choosePlan: (program_key: string) => call<Plan>("PUT", "/plans/current", { program_key }),
  leavePlan: () => call<void>("DELETE", "/plans/current"),
  tdee: (days = 90) => call<TdeeReport>("GET", `/intelligence/tdee?days=${days}`),
  tdeeExplanation: () => call<Explanation>("GET", "/intelligence/tdee/explanation"),
  dietInsights: () => call<DietInsights>("GET", "/intelligence/insights"),
  insightExplanation: (code: string) => call<Explanation>("GET", `/intelligence/insights/${encodeURIComponent(code)}/explanation`),
  progressionExplanation: (exerciseId: number) => call<Explanation>("GET", `/intelligence/progression/${exerciseId}/explanation`),
  recoveryExplanation: (muscle: string) => call<Explanation>("GET", `/intelligence/recovery/${muscle}/explanation`),
  startDeload: () => call<DeloadAdvice>("POST", "/deload/start"),
  finishWorkout: (workoutId: number) => call<FinishedWorkout>("POST", `/workouts/${workoutId}/finish`),

  foods: (q = "") => call<Food[]>("GET", `/foods?q=${encodeURIComponent(q)}`),
  addFood: (body: FoodIn) => call<Food>("POST", "/foods", body),
  deleteFood: (id: number) => call<null>("DELETE", `/foods/${id}`),
  dayLog: () => call<DayLog>("GET", "/meals/day"),
  foodGuide: () => call<FoodGuide>("GET", "/meals/guide"),
  logMeal: (meal_type: MealType, items: { food_id: number; portions: number }[]) =>
    call<{ meal: unknown; xp_awarded: number }>("POST", "/meals", { meal_type, items }),
  deleteMeal: (id: number) => call<null>("DELETE", `/meals/${id}`),

  game: () => call<GameSummary>("GET", "/game/summary"),
  streakReason: (day: string, reason: string) => call<StreakInfo>("POST", "/game/streak/reason", { day, reason }),
  stats: () => call<Stats>("GET", "/game/stats"),
  boss: () => call<BossRaid>("GET", "/game/boss"),
  titles: () => call<EarnedTitle[]>("GET", "/game/titles"),
  bosses: () => call<BossLadderEntry[]>("GET", "/game/bosses"),
  completeQuest: (id: number) => call<QuestItem>("POST", `/game/quests/${id}/complete`),

  coachStatus: () => call<CoachStatus>("GET", "/coach/status"),
  coachTip: () => call<CoachReply>("GET", "/coach/tip"),
  coachAsk: (question: string) => call<CoachReply>("POST", "/coach/ask", { question }),
  coachWarm: () => call<CoachWarm>("POST", "/coach/warm"),

  trainerChat: (text: string) => call<ChatReply>("POST", "/trainer/chat", { text }),
  confirmAction: (id: number, typed: string | null = null) => call<ActionProposal>("POST", `/actions/${id}/confirm`, { typed }),
  cancelAction: (id: number) => call<ActionProposal>("POST", `/actions/${id}/cancel`),
  undoAction: (id: number) => call<ActionProposal>("POST", `/actions/${id}/undo`),
  actionLog: () => call<ActionProposal[]>("GET", "/actions/log"),
  goalCheck: (body: GoalCheckIn) => call<GoalCheck>("POST", "/planner/check", body),
  planWorkout: (body: WorkoutPlanIn) => call<WorkoutPlan>("POST", "/planner/workout", body),
  customPrograms: () => call<CustomProgram[]>("GET", "/planner/programs"),
  saveProgram: (draft: ProgramDraft) => call<CustomProgram>("POST", "/planner/programs", draft),
  followProgram: (id: number) => call<CustomProgram>("POST", `/planner/programs/${id}/follow`),
  deleteProgram: (id: number) => call<null>("DELETE", `/planner/programs/${id}`),
  planDiet: (body: { diet: DietKind; kcal_target?: number | null; use_ai?: boolean }) => call<DietPlan>("POST", "/planner/diet", body),
  savedDiets: () => call<SavedDiet[]>("GET", "/planner/diets"),
  saveDiet: (name: string, plan: DietPlan) => call<SavedDiet>("POST", "/planner/diets", { name, plan }),
  deleteDiet: (id: number) => call<null>("DELETE", `/planner/diets/${id}`),
  photos: () => call<ProgressPhoto[]>("GET", "/photos"),
  addPhoto: (body: { data_url: string; taken_on: string; pose: PhotoPose; note?: string }) => call<ProgressPhoto>("POST", "/photos", body),
  photoData: (id: number) => call<{ id: number; mime: string; data_url: string }>("GET", `/photos/${id}/data`),
  deletePhoto: (id: number) => call<null>("DELETE", `/photos/${id}`),
  deleteAllPhotos: () => call<{ deleted: number }>("DELETE", "/photos"),
  photoFeedbackStatus: () => call<PhotoFeedbackStatus>("GET", "/photos/feedback/status"),
  photoFeedback: (older_id: number, newer_id: number) => call<PhotoFeedback>("POST", "/photos/feedback", { older_id, newer_id }),
  shareCard: (payload: Record<string, unknown>) => call<ShareCardText>("POST", "/share/card", { payload }),
  trainerFeed: () => call<TrainerFeed>("GET", "/trainer/feed"),
  trainerFeedRead: (ids: number[] | null = null) => call<null>("POST", "/trainer/feed/read", { ids }),
  trainerState: () => call<TrainerState>("GET", "/trainer/state"),
  updateTrainerState: (patch: { onboarded?: boolean; tour_done?: string }) => call<TrainerState>("PUT", "/trainer/state", patch),
  trainerKb: () => call<KbEntry[]>("GET", "/trainer/kb"),

  aiSetup: () => call<AiSetup>("GET", "/ai/setup"),
  aiModel: (model: string | null) => call<AiSetup>("PUT", "/ai/model", { model }),
  aiTest: () => call<AiTest>("POST", "/ai/test"),
  /** "Start fresh": deletes the user's data after a safety backup; keeps the library. */
  eraseData: (keep_preferences = true) => call<EraseResult>("POST", "/data/erase", { confirm: "erase", keep_preferences }),

  bodyMetrics: (days = 90) => call<BodyMetric[]>("GET", `/body-metrics?days=${days}`),
  logWeight: (weight_kg: number, waist_cm?: number | null) =>
    call<BodyMetric>("POST", "/body-metrics", { weight_kg, waist_cm: waist_cm ?? null }),
  deleteWeight: (id: number) => call<null>("DELETE", `/body-metrics/${id}`),
  measurements: () => call<Measurement[]>("GET", "/measurements"),
  logMeasurement: (site: MeasurementSite, cm: number) => call<Measurement>("POST", "/measurements", { site, cm }),
  eta: () => call<Eta>("GET", "/progress/eta"),
  weekly: (weeks = 8) => call<WeekSummary[]>("GET", `/progress/weekly?weeks=${weeks}`),
  recap: (week?: string) => call<WeekRecap>("GET", week ? `/progress/recap?week=${week}` : "/progress/recap"),
  muscleActivity: (days: number) => call<MuscleActivity[]>("GET", `/muscles/activity?days=${days}`),
  muscleHistory: (code: string, days: number) =>
    call<MuscleHistory>("GET", `/muscles/${encodeURIComponent(code)}/history?days=${days}`),

  checkinToday: () => call<Checkin | null>("GET", "/checkins/today"),
  checkin: (c: CheckinIn) => call<Checkin>("POST", "/checkins", c),
  weeklyReview: () => call<WeeklyReview>("GET", "/coach/weekly-review/latest"),

  history: (days = 30) => call<HistoryDay[]>("GET", `/history?days=${days}`),
  exportJson: () => call<unknown>("GET", "/export/json"),
  exportCsv: (kind: "workouts" | "meals") => call<string>("GET", `/export/csv/${kind}`),
  /** Strong / Hevy CSV import. dry_run defaults to true on the sidecar: report only. */
  importCsv: (source: ImportSource, body: ImportIn) => call<ImportReport>("POST", `/import/${source}`, body),
};
