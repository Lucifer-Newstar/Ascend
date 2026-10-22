/**
 * Insights on Today: at most three short notes, each with a "Why?" that shows where it
 * came from. Today's tip comes from the coach (rules, or worded by the local model from
 * the rules' numbers); the others are the weekly review's top findings.
 * v8: with the trainer on, Instructor Iskra Vey speaks each one (lib/trainer.ts: a fixed
 * opener around the engine's own sentence, so no number changes). "Why?" is unchanged.
 */
import type { CoachReply, WeeklyReview } from "@ascend/shared";
import { useId, useState } from "react";

import { moodFor, trainerLine, TRAINER_SHORT } from "../lib/trainer";
import { IconSpark } from "./Icons";
import { TrainerSays, useTrainerOn } from "./Trainer";

interface Insight {
  key: string;
  /** The engine's code, used to pick the trainer's expression. */
  code: string;
  severity: number;
  title: string;
  why: string;
  source: string;
}

export function buildInsights(tip: CoachReply | null, review: WeeklyReview | null): Insight[] {
  const out: Insight[] = [];
  if (tip) {
    out.push({
      key: `tip-${tip.tip_code}`,
      code: tip.tip_code,
      severity: 0,
      title: tip.text,
      why: tip.source === "ollama"
        ? `The rule "${tip.tip_code}" picked this topic and its numbers; the local model (${tip.model ?? "local"}) worded it, and every number was checked against the rule's.`
        : `Rule "${tip.tip_code}" from the rule-based coach${tip.fallback_reason ? ` (AI not used: ${tip.fallback_reason.replace(/_/g, " ")})` : ""}.`,
      source: tip.source === "ollama" ? `Local AI · ${tip.model ?? ""}`.trim() : "Rule-based tip",
    });
  }
  for (const f of review?.top ?? []) {
    if (out.length >= 3) break;
    out.push({
      key: `review-${f.code}-${f.title}`,
      code: f.code,
      severity: 0,
      title: f.title,
      why: `${f.detail}${f.proposal ? ` Suggestion: ${f.proposal}` : ""} (weekly review ${review?.week_start} to ${review?.week_end}, ${review?.algo_version}).`,
      source: "Weekly review",
    });
  }
  return out;
}

function InsightRow({ insight, trainer }: { insight: Insight; trainer: boolean }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const mood = moodFor(insight.code, insight.severity);
  return (
    <li className={trainer ? "py-1" : "rounded-md border border-line bg-panel-2/60 p-3"} data-mood={trainer ? mood : undefined}>
      {trainer ? (
        <TrainerSays mood={mood} size={44}>
          <p className="text-sm leading-relaxed text-ink">{trainerLine(insight.key, insight.title, mood)}</p>
        </TrainerSays>
      ) : (
        <p className="text-sm leading-relaxed text-ink">{insight.title}</p>
      )}
      <div className="mt-1.5 flex items-center justify-between gap-3 text-[11px] text-faint">
        <span className="flex items-center gap-1"><IconSpark width={12} height={12} aria-hidden="true" /> {insight.source}</span>
        <button type="button" className="text-xs text-accent hover:underline" aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}>
          Why?
        </button>
      </div>
      {open && <p id={id} className="panel-in mt-2 border-t border-line pt-2 text-xs text-muted">{insight.why}</p>}
    </li>
  );
}

export function InsightsCard({ tip, review, onOpenCoach }: { tip: CoachReply | null; review: WeeklyReview | null; onOpenCoach: () => void }) {
  const items = buildInsights(tip, review);
  const trainer = useTrainerOn();
  return (
    <section className="card h-full p-5" aria-labelledby="insights-title">
      <div className="mb-3 flex items-center justify-between">
        <h2 id="insights-title" className="card-title">{trainer ? `${TRAINER_SHORT}'s briefing` : "Insights"}</h2>
        <button type="button" className="text-xs text-accent hover:underline" onClick={onOpenCoach}>Ask the coach →</button>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-muted">Nothing to flag yet. Insights appear once there is a week of logs.</p>
      ) : (
        <ul className="space-y-2">{items.map((i) => <InsightRow key={i.key} insight={i} trainer={trainer} />)}</ul>
      )}
    </section>
  );
}
