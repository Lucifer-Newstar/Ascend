/**
 * Ctrl+K command bar: type what you did or where you want to go.
 *
 * "bench 80x5 @8" logs a set (starting today's session if needed), "plank 45s" a hold,
 * "weight 81.4" a weigh-in, "lunch chicken rice" a meal, "train front lever" adds the
 * skill to today's quest, "dark"/"light" switch the theme, a page name opens it, and
 * anything else is asked to your trainer in the chat. Arrow keys pick a row, Enter runs it, Esc closes.
 * The parser is rule-based (lib/commands.ts); nothing here calls a model.
 */
import type { Exercise, Food, SkillSummary } from "@ascend/shared";
import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";

import { api } from "../api/client";
import { parseCommand, PAGE_WORDS, rankExercises, type Command } from "../lib/commands";
import { usePrefs } from "../lib/prefs";
import { play } from "../lib/sound";
import { formatWeight } from "../lib/units";
import type { Page } from "./Layout";
import { IconSearch } from "./Icons";
import { useToast } from "./Toast";

interface Row {
  id: string;
  group: string;
  title: string;
  hint?: string;
  run: () => Promise<void> | void;
}

const EXAMPLES = ["bench 80x5 @8", "plank 45s", "weight 81.4", "lunch chicken rice", "train front lever"];

export function CommandBar({ open, onClose, onNavigate, onChanged, onAsk = () => undefined }: {
  open: boolean;
  onClose: () => void;
  onNavigate: (p: Page) => void;
  onChanged: () => void;
  /** Open the trainer chat, with a question to ask when one is given. */
  onAsk?: (question?: string) => void;
}) {
  const { settings, update } = usePrefs();
  const toast = useToast();
  const units = settings.units;
  const [text, setText] = useState("");
  const [active, setActive] = useState(0);
  const [busy, setBusy] = useState(false);
  const [exercises, setExercises] = useState<Exercise[] | null>(null);
  const [skills, setSkills] = useState<SkillSummary[] | null>(null);
  const [foods, setFoods] = useState<{ q: string; list: Food[] } | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const returnTo = useRef<HTMLElement | null>(null);
  const listId = useId();

  // Load the library and skills the first time the bar opens; reset on each open.
  useEffect(() => {
    if (!open) return;
    returnTo.current = document.activeElement as HTMLElement | null;
    setText("");
    setActive(0);
    if (!exercises) api.exercises().then(setExercises).catch(() => setExercises([]));
    if (!skills) api.skills().then(setSkills).catch(() => setSkills([]));
    // The field exists by the time effects run: focus it at once, so keys typed right after
    // Ctrl+K (including Esc) land in the bar.
    input.current?.focus();
    // Esc closes even if focus is somewhere else in the dialog.
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key !== "Escape" || e.defaultPrevented) return;
      e.preventDefault();
      onClose();
      returnTo.current?.focus?.();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const commands = useMemo(() => parseCommand(text, units), [text, units]);
  const mealQuery = commands.find((c): c is Extract<Command, { kind: "meal" }> => c.kind === "meal")?.query ?? null;

  // Food search for "lunch chicken rice", debounced.
  useEffect(() => {
    if (!mealQuery) return;
    const t = setTimeout(() => {
      api.foods(mealQuery).then((list) => setFoods({ q: mealQuery, list })).catch(() => setFoods({ q: mealQuery, list: [] }));
    }, 150);
    return () => clearTimeout(t);
  }, [mealQuery]);

  function close() {
    onClose();
    returnTo.current?.focus?.();
  }

  const rows = useMemo<Row[]>(() => {
    if (!text.trim()) {
      const quick: Row[] = [
        { id: "q-train", group: "Quick actions", title: "Start or continue today's session", run: () => onNavigate("workout") },
        { id: "q-set", group: "Quick actions", title: "Log a set…", hint: "bench 80x5 @8", run: () => fill("bench 80x5 @8") },
        { id: "q-sets", group: "Quick actions", title: "Log several sets…", hint: "log 3x8 pull-up", run: () => fill("log 3x8 pull-up") },
        { id: "q-hold", group: "Quick actions", title: "Log a hold…", hint: "plank 45s", run: () => fill("plank 45s") },
        { id: "q-weight", group: "Quick actions", title: "Log body weight…", hint: "weight 81.4", run: () => fill("weight ") },
        { id: "q-food", group: "Quick actions", title: "Log food…", hint: "add 2 eggs", run: () => fill("add 1 ") },
        { id: "q-checkin", group: "Quick actions", title: "Morning check-in", run: () => onNavigate("dashboard") },
        { id: "q-skill", group: "Quick actions", title: "Train a skill…", hint: "train front lever", run: () => fill("train ") },
        { id: "q-ask", group: "Quick actions", title: "Ask your trainer", run: () => onAsk() },
        { id: "q-theme", group: "Quick actions", title: `Switch to the ${settings.theme === "light" ? "dark" : "light"} theme`, run: async () => { await update({ theme: settings.theme === "light" ? "dark" : "light" }); } },
      ];
      return [...quick, ...PAGE_WORDS.map((p) => ({ id: `nav-${p.page}`, group: "Go to", title: p.label, run: () => onNavigate(p.page) }))];
    }
    const out: Row[] = [];
    for (const c of commands) {
      if (c.kind === "set") {
        for (const ex of rankExercises(c.query, exercises ?? [], 3, { weighted: c.weightKg > 0 })) {
          const n = c.sets ?? 1;
          const what = `${n > 1 ? `${n} sets of ` : ""}${c.weightKg > 0 ? formatWeight(c.weightKg, units) : "bodyweight"} × ${c.reps}${c.rpe !== null ? ` @${c.rpe}` : ""}`;
          out.push({ id: `set-${ex.id}`, group: n > 1 ? "Log sets" : "Log a set", title: `${ex.name} · ${what}`, hint: "Adds to today's session", run: () => logSet(ex, { weight_kg: c.weightKg, reps: c.reps, rpe: c.rpe }, what, n) });
        }
      } else if (c.kind === "hold") {
        const ranked = rankExercises(c.query, exercises ?? [], 6).sort((a, b) => Number(b.measure === "hold") - Number(a.measure === "hold")).slice(0, 3);
        for (const ex of ranked) {
          const what = ex.time_based ? `${Math.round(c.seconds / 60) || 1} min` : `${c.seconds} s`;
          out.push({ id: `hold-${ex.id}`, group: "Log a set", title: `${ex.name} · ${what}`, hint: "Adds to today's session",
            run: () => logSet(ex, ex.measure === "hold" ? { duration_s: c.seconds, weight_kg: 0, reps: 1, rpe: c.rpe } : { duration_s: c.seconds, rpe: c.rpe }, what) });
        }
      } else if (c.kind === "weight") {
        out.push({ id: "weight", group: "Body", title: `Log body weight ${formatWeight(c.kg, units)}`, run: async () => {
          await api.logWeight(c.kg);
          toast(`Weight logged: ${formatWeight(c.kg, units)}`, "info");
          onChanged();
        } });
      } else if (c.kind === "meal") {
        const list = foods?.q === c.query ? foods.list : [];
        const portions = c.portions ?? 1;
        for (const f of list.slice(0, 3)) {
          out.push({ id: `meal-${f.id}`, group: "Log food", title: `${portions !== 1 ? `${portions} × ` : ""}${f.name} as ${c.mealType}`, hint: `${portions} × ${f.portion_label} · ${Math.round(f.kcal * portions)} kcal`, run: async () => {
            await api.logMeal(c.mealType, [{ food_id: f.id, portions }]);
            toast(`${f.name} logged as ${c.mealType}`, "info");
            onChanged();
          } });
        }
        if (foods?.q === c.query && list.length === 0) out.push({ id: "meal-none", group: "Log food", title: `No food matches “${c.query}”`, hint: "Open Fuel to add it", run: () => onNavigate("diet") });
      } else if (c.kind === "train") {
        const q = c.query.toLowerCase();
        for (const s of (skills ?? []).filter((s) => s.name.toLowerCase().includes(q) || s.key.replace(/_/g, " ").includes(q)).slice(0, 3)) {
          out.push({ id: `train-${s.key}`, group: "Skills", title: `Train ${s.name}`, hint: "Adds its next step to today's quest", run: async () => {
            const r = await api.trainSkill(s.key);
            toast(r.message, r.added ? "xp" : "info");
            onChanged();
          } });
        }
      } else if (c.kind === "theme") {
        out.push({ id: `theme-${c.theme}`, group: "Settings", title: `Switch to the ${c.theme} theme`, run: async () => { await update({ theme: c.theme }); } });
      } else if (c.kind === "ai") {
        out.push({ id: `ai-${c.on}`, group: "Settings", title: `Turn the local AI ${c.on ? "on" : "off"}`, run: async () => { await update({ ai_enabled: c.on }); onChanged(); } });
      } else if (c.kind === "nav") {
        out.push({ id: `nav-${c.page}`, group: "Go to", title: c.label, run: () => onNavigate(c.page) });
      } else if (c.kind === "ask") {
        out.push({ id: "ask", group: "Trainer", title: `Ask your trainer: “${c.question}”`, hint: "Not a command, so it goes to the trainer chat", run: () => onAsk(c.question) });
      }
    }
    return out;
    // logSet is stable enough for a render; the rows rebuild on every input change anyway.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, commands, exercises, skills, foods, units, settings.theme]);

  useEffect(() => setActive(0), [text]);

  async function logSet(ex: Exercise, body: { weight_kg?: number; reps?: number; rpe?: number | null; duration_s?: number }, what: string, times = 1) {
    let w = await api.activeWorkout();
    if (!w) w = await api.startWorkout(ex.section);
    let xp = 0;
    let pr = false;
    for (let i = 0; i < times; i += 1) {
      const r = await api.logSet(w.id, { exercise_id: ex.id, ...body });
      xp += r.xp_awarded;
      pr = pr || r.set.is_pr;
    }
    toast(`${ex.name} · ${what} logged · +${xp} XP`, "xp");
    play("set");
    if (pr) toast(`New PR on ${ex.name}`, "pr");
    onChanged();
  }

  /** Quick actions that need details put a template in the field instead of running. */
  const filling = useRef(false);
  function fill(t: string) {
    filling.current = true;
    setText(t);
    input.current?.focus();
  }

  async function run(row: Row | undefined) {
    if (!row || busy) return;
    setBusy(true);
    try {
      filling.current = false;
      await row.run();
      if (!filling.current) close();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(rows.length - 1, a + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    else if (e.key === "Enter") { e.preventDefault(); void run(rows[active]); }
    else if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "Tab") e.preventDefault(); // focus stays in the bar while it is open
  }

  if (!open) return null;
  let lastGroup = "";
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-bg/70 px-4 pt-[12vh] backdrop-blur-[2px]" onMouseDown={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div role="dialog" aria-modal="true" aria-label="Command bar" className="card dialog-in w-full max-w-xl overflow-hidden p-0" data-testid="command-bar">
        <div className="flex items-center gap-2 border-b border-line px-4 transition-colors duration-150 focus-within:border-accent">
          <IconSearch className="shrink-0 text-faint" width={18} height={18} />
          <input
            ref={input}
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-activedescendant={rows[active] ? `${listId}-${active}` : undefined}
            aria-autocomplete="list"
            aria-label="Command"
            className="cmd-input h-14 min-w-0 flex-1 bg-transparent text-base text-ink placeholder:text-faint outline-none"
            placeholder="Log a set, a meal, your weight… or ask your trainer"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKey}
          />
          <kbd className="chip shrink-0">Esc</kbd>
        </div>
        <ul id={listId} role="listbox" aria-label="Results" className="max-h-[50vh] overflow-y-auto p-2">
          {rows.map((r, i) => {
            const header = r.group !== lastGroup ? r.group : null;
            lastGroup = r.group;
            return (
              <li key={r.id} role="presentation">
                {header && <div className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-faint" aria-hidden="true">{header}</div>}
                <div
                  id={`${listId}-${i}`}
                  role="option"
                  aria-selected={i === active}
                  onMouseMove={() => { if (active !== i) setActive(i); }}
                  onClick={() => void run(r)}
                  className={`flex cursor-pointer items-baseline justify-between gap-3 rounded-md px-3 py-2 text-sm transition-colors duration-100 ${i === active ? "bg-accent/12 text-ink" : "text-muted"}`}
                >
                  <span className="min-w-0 truncate">{r.title}</span>
                  {r.hint && <span className="shrink-0 text-xs text-faint">{r.hint}</span>}
                </div>
              </li>
            );
          })}
        </ul>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line px-4 py-2 text-[11px] text-faint">
          <span>Try:</span>
          {EXAMPLES.map((x) => (
            <button key={x} type="button" tabIndex={-1} className="font-mono text-muted hover:text-ink" onClick={() => { setText(x); input.current?.focus(); }}>{x}</button>
          ))}
          <span className="ml-auto">↑↓ pick · Enter run</span>
        </div>
      </div>
    </div>
  );
}

/** The header button that opens the bar. */
export function CommandButton({ onOpen }: { onOpen: () => void }) {
  return (
    <button type="button" onClick={onOpen} aria-keyshortcuts="Control+K"
      className="hidden items-center gap-2 rounded-md border border-line bg-panel-2 px-3 py-1.5 text-xs text-muted transition-colors duration-150 hover:border-line-2 hover:text-ink md:flex">
      <IconSearch width={14} height={14} aria-hidden="true" />
      <span>Log or ask…</span>
      <kbd className="rounded border border-line px-1 font-sans text-[10px] text-faint">Ctrl K</kbd>
    </button>
  );
}

/** Ctrl+K / Cmd+K anywhere toggles the bar. */
export function isCommandKey(e: Pick<globalThis.KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "altKey" | "shiftKey">): boolean {
  return (e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey && e.key.toLowerCase() === "k";
}
