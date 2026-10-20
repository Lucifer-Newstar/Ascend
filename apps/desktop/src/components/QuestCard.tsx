import type { QuestItem } from "@ascend/shared";

import { IconCheck } from "./Icons";

const KIND_LABEL: Record<QuestItem["kind"], string> = {
  training: "Training",
  nutrition: "Nutrition",
  recovery: "Recovery",
};

export function QuestList({ items, onComplete }: { items: QuestItem[]; onComplete: (id: number) => void }) {
  const done = items.filter((i) => i.completed_at).length;
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="card-title">Daily quest</h2>
        <span className="text-xs text-muted">{done}/{items.length} complete</span>
      </div>
      <ul className="space-y-2">
        {items.map((q) => {
          const complete = Boolean(q.completed_at);
          const manual = q.metric === "manual";
          return (
            <li key={q.id} className={`flex items-center gap-3 rounded-lg border px-3 py-2.5 ${complete ? "border-accent/25 bg-accent/[0.06]" : "border-line bg-panel-2"}`}>
              <button
                type="button"
                aria-label={complete ? "Completed" : manual ? `Mark "${q.title}" done` : "Completes automatically"}
                disabled={complete || !manual}
                onClick={() => onComplete(q.id)}
                className={`grid h-6 w-6 shrink-0 place-items-center rounded-md border ${complete ? "border-accent bg-accent text-on-accent" : manual ? "border-line-2 hover:border-accent" : "border-dashed border-line-2"}`}
              >
                {complete && <IconCheck width={14} height={14} />}
              </button>
              <div className="min-w-0 flex-1">
                <div className={`truncate text-sm font-medium ${complete ? "text-muted line-through decoration-faint" : "text-ink"}`}>{q.title}</div>
                <div className="truncate text-xs text-muted">
                  {KIND_LABEL[q.kind]} · {manual ? q.detail : `${q.progress}/${q.target} · auto-tracked`}
                </div>
              </div>
              <span className="shrink-0 rounded-md bg-xp/10 px-2 py-0.5 text-xs font-semibold text-xp">+{q.xp} XP</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
