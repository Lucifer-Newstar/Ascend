/**
 * Fuel's food guide (v1.2, item 14): India's food guidelines (ICMR-NIN 2024) in plain
 * words, and a rough check of today's plate by food group. Guidance only: it never changes
 * the calorie or protein targets and never talks about the body.
 */
import type { FoodGuide } from "@ascend/shared";

import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import { Panel } from "./Page";

export function FoodGuidePanel({ refreshKey = 0, index = 6 }: { refreshKey?: number; index?: number }) {
  const r = useApi(api.foodGuide, [refreshKey]);
  return (
    <Panel id="food-guide" index={index} className="col-span-12" title="India's food guide"
      hint="From the ICMR-NIN 2024 Dietary Guidelines for Indians. A rough guide from food names, not medical advice."
      loading={r.loading && !r.data} error={!r.data ? r.error ?? null : null} onRetry={r.reload}>
      {r.data && <FoodGuideBody guide={r.data} />}
    </Panel>
  );
}

export function FoodGuideBody({ guide }: { guide: FoodGuide }) {
  return (
    <div className="space-y-4" data-testid="food-guide">
      <div>
        <h3 className="text-sm font-semibold text-ink">Today&apos;s plate</h3>
        <ul className="mt-2 flex flex-wrap gap-2" aria-label="Food groups today">
          {guide.groups.map((g) => {
            const on = g.count > 0;
            return (
              <li key={g.key} data-testid={`group-${g.key}`} data-on={on}
                className={`rounded-full border px-3 py-1 text-xs ${on ? "border-good bg-panel-2 text-ink" : "border-line-2 bg-panel text-muted"}`}>
                <span aria-hidden>{on ? "✓ " : ""}</span>
                {g.label}
                {!g.core && <span className="text-faint"> (optional)</span>}
                <span className="sr-only">{on ? `: ${g.count} logged` : ": none yet"}</span>
              </li>
            );
          })}
        </ul>
        {guide.hfss.length > 0 && (
          <p className="mt-2 text-xs text-muted" data-testid="food-guide-hfss">
            High in fat, salt or sugar today: {guide.hfss.join(", ")}.
          </p>
        )}
      </div>
      <ul className="space-y-1.5" aria-label="Tips for today">
        {guide.tips.map((t) => (
          <li key={t} className="rounded-lg border border-line bg-panel-2 px-3 py-2 text-sm text-ink">{t}</li>
        ))}
      </ul>
      <details className="text-sm">
        <summary className="cursor-pointer text-accent">The {guide.guidelines.length} guidelines</summary>
        <ol className="mt-2 space-y-2">
          {guide.guidelines.map((g) => (
            <li key={g.title} className="rounded-lg border border-line bg-panel-2 px-3 py-2">
              <div className="font-medium text-ink">{g.title}</div>
              <div className="text-xs text-muted">{g.detail}</div>
            </li>
          ))}
        </ol>
        <p className="mt-2 text-xs text-faint">Source: {guide.source}.</p>
      </details>
    </div>
  );
}
