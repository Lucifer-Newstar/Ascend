/**
 * Guided tours: the app tour (first run) and one per section, on demand from the trainer
 * chat ("tour me through skills"). A step points at an element marked data-tour="…"; a
 * step whose element isn't on screen is skipped, so a tour never points at nothing.
 */
import type { Page } from "../components/Layout";

export interface TourStep {
  /** data-tour value of the element to highlight; null = a centred card. */
  target: string | null;
  title: string;
  body: string;
}

export interface Tour {
  id: string;
  /** The page the tour runs on (the app tour stays where it is). */
  page: Page | null;
  steps: TourStep[];
}

const nav = (id: Page, title: string, body: string): TourStep => ({ target: `nav-${id}`, title, body });

export const APP_TOUR: Tour = {
  id: "app",
  page: "dashboard",
  // Five steps at most (scope review): the rest is one "tour me through …" away.
  steps: [
    nav("dashboard", "Today", "Your daily quests, rings, streak and the weekly boss. Start here each day. Next to continue, Esc to stop."),
    nav("workout", "Train", "Log sets here. Every set is saved instantly and the engine suggests your next target."),
    nav("diet", "Fuel", "Log meals with Indian portions; calories and protein update straight away."),
    { target: "ai", title: "Local AI (optional)", body: "The app works fully without AI. With Ollama installed, a local model words answers on this PC. Settings > AI setup checks your PC." },
    { target: "trainer", title: "Ask me anything", body: "Open the chat for help, a tour of any page (\"tour me through skills\"), or to check a goal. Ctrl+K jumps anywhere." },
  ],
};

const main = (title: string, body: string): TourStep => ({ target: "main", title, body });

export const SECTION_TOURS: Record<string, Tour> = {
  dashboard: { id: "dashboard", page: "dashboard", steps: [
    main("Today", "Quests sized to your recovery, your rings for training, food and habits, and the boss raid."),
    main("Daily check-in", "Rate sleep, energy, soreness and mood; the training quest adapts to your readiness."),
    main("Boss raid", "Every set you log is one hit on this week's boss. Beat it by Sunday for a title."),
  ] },
  workout: { id: "workout", page: "workout", steps: [
    main("Train", "Pick a section (gym, calisthenics, cardio, flexibility) and an exercise."),
    main("Logging", "Type weight and reps, press Enter. The set is saved immediately."),
    main("Targets", "The suggestion card shows the next target; Why? explains the numbers."),
  ] },
  library: { id: "library", page: "library", steps: [
    main("Exercises", "Search the library by name, muscle or equipment."),
    main("Your own", "Add a custom exercise; it works everywhere a built-in one does."),
  ] },
  skills: { id: "skills", page: "skills", steps: [
    main("Skill trees", "Each skill is a ladder of progressions, from the easiest step up."),
    main("Unlocking", "A step unlocks when your logged sets meet its target, like 3x8 of the step before."),
    main("Training a step", "Open a skill and press Train on the current step to log it."),
  ] },
  progress: { id: "progress", page: "progress", steps: [
    main("Weight trend", "A smoothed line, so daily water swings don't mislead you."),
    main("Muscle map", "Each muscle's weekly load: under, optimal, recovering or over."),
    main("Records", "PRs by estimated one-rep max, and your goal estimate with its range."),
  ] },
  diet: { id: "diet", page: "diet", steps: [
    main("Fuel", "Search a food, pick pieces, katori or tbsp, and log it to a meal."),
    main("Targets", "Calories and protein targets adapt to your real weigh-ins over a few weeks."),
  ] },
  history: { id: "history", page: "history", steps: [main("History", "Every past day: sessions, sets, meals and weigh-ins. Click a day to edit.")] },
  data: { id: "data", page: "data", steps: [main("Import & export", "Bring in Strong or Hevy CSVs (with a dry run first) or export everything.")] },
  settings: { id: "settings", page: "settings", steps: [
    main("Settings", "Profile and targets, AI setup, appearance, units and backups."),
    main("Start fresh", "Erase my data deletes your logs after a backup and keeps the exercise library."),
  ] },
};

export function tourFor(target: string | null | undefined): Tour | null {
  if (!target || target === "app") return APP_TOUR;
  const t = SECTION_TOURS[target];
  if (!t) return null;
  // A section tour starts by pointing at the page in the sidebar.
  return { ...t, steps: [{ target: `nav-${t.page}`, title: t.steps[0].title, body: t.steps[0].body }, ...t.steps.slice(1)] };
}
