/**
 * Renderer-side API client.
 *
 * Inside Electron every call goes through `window.ascend.request` (preload ->
 * IPC -> main -> sidecar), so the renderer never sees the auth token.
 * In plain-browser development (`npm run dev` + `python -m app --dev`) it
 * falls back to fetch() against http://127.0.0.1:8765 with the dev token.
 */
import type {
  AscendBridge,
  CoachReply,
  CoachStatus,
  Dashboard,
  DayLog,
  Exercise,
  FinishedWorkout,
  Food,
  GameSummary,
  HistoryDay,
  HttpMethod,
  LoggedSet,
  MealType,
  MuscleState,
  Profile,
  ProfileIn,
  QuestItem,
  Workout,
} from "@ascend/shared";

declare global {
  interface Window {
    ascend?: AscendBridge;
  }
}

const DEV_URL: string = import.meta.env.VITE_SIDECAR_URL ?? "http://127.0.0.1:8765";
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
  if (res.status === 204) return null as T;
  const type = res.headers.get("content-type") ?? "";
  const data: unknown = type.includes("json") ? await res.json() : await res.text();
  if (!res.ok) throw new ApiError(res.status, errorMessage(data));
  return data as T;
}

export const api = {
  dashboard: () => call<Dashboard>("GET", "/dashboard"),
  profile: () => call<Profile>("GET", "/profile"),
  saveProfile: (p: ProfileIn) => call<Profile>("PUT", "/profile", p),
  settings: () => call<{ ai_enabled: boolean }>("GET", "/settings"),
  setAi: (enabled: boolean) => call<{ ai_enabled: boolean }>("PUT", "/settings", { ai_enabled: enabled }),
  muscles: () => call<MuscleState[]>("GET", "/muscles"),

  exercises: (q = "") => call<Exercise[]>("GET", `/exercises?q=${encodeURIComponent(q)}`),
  activeWorkout: () => call<Workout | null>("GET", "/workouts/active"),
  startWorkout: () => call<Workout>("POST", "/workouts"),
  logSet: (workoutId: number, s: { exercise_id: number; weight_kg: number; reps: number; rpe: number | null }) =>
    call<LoggedSet>("POST", `/workouts/${workoutId}/sets`, s),
  finishWorkout: (workoutId: number) => call<FinishedWorkout>("POST", `/workouts/${workoutId}/finish`),

  foods: (q = "") => call<Food[]>("GET", `/foods?q=${encodeURIComponent(q)}`),
  dayLog: () => call<DayLog>("GET", "/meals/day"),
  logMeal: (meal_type: MealType, items: { food_id: number; portions: number }[]) =>
    call<{ meal: unknown; xp_awarded: number }>("POST", "/meals", { meal_type, items }),
  deleteMeal: (id: number) => call<null>("DELETE", `/meals/${id}`),

  game: () => call<GameSummary>("GET", "/game/summary"),
  completeQuest: (id: number) => call<QuestItem>("POST", `/game/quests/${id}/complete`),

  coachStatus: () => call<CoachStatus>("GET", "/coach/status"),
  coachTip: () => call<CoachReply>("GET", "/coach/tip"),
  coachAsk: (question: string) => call<CoachReply>("POST", "/coach/ask", { question }),

  history: (days = 30) => call<HistoryDay[]>("GET", `/history?days=${days}`),
  exportJson: () => call<unknown>("GET", "/export/json"),
  exportCsv: (kind: "workouts" | "meals") => call<string>("GET", `/export/csv/${kind}`),
};
