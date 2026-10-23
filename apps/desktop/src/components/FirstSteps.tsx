/**
 * First-run guide on the Dashboard: shown until the first XP is earned, so a new
 * user sees where to start instead of empty rings and a grey muscle map.
 */
import type { Page } from "./Layout";
import { IconBowl, IconDumbbell, IconSpark } from "./Icons";

export function FirstSteps({ onNavigate }: { onNavigate: (p: Page) => void }) {
  return (
    <section className="card card-hover panel-in col-span-12 p-5" aria-labelledby="first-steps-title">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 id="first-steps-title" className="flex items-center gap-2 text-base font-semibold text-ink">
            <IconSpark width={16} height={16} className="text-accent" /> Welcome to ASCEND
          </h2>
          <p className="mt-1 text-sm text-muted">Log one set and one meal to earn your first XP and hit this week's boss.</p>
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn-primary" onClick={() => onNavigate("workout")}>
            <IconDumbbell width={16} height={16} /> Log a set
          </button>
          <button type="button" className="btn-ghost" onClick={() => onNavigate("diet")}>
            <IconBowl width={16} height={16} /> Log a meal
          </button>
        </div>
      </div>
    </section>
  );
}
