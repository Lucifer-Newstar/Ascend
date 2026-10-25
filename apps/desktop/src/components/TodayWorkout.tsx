/**
 * Today's workout (v1.2, on Today): the next session of the program the player follows,
 * with a Start button, or a nudge to pick a program that fits their kit.
 *
 * v1.4: a "10-minute version" button for a short day. It keeps the first moves at two sets
 * each; any logged set counts for the streak, and the full session stays next.
 */
import type { ShortSession } from "@ascend/shared";
import { useState } from "react";

import { api } from "../api/client";
import type { Page } from "./Layout";
import { planTarget } from "./ProgramCard";
import { rememberShort, shortTarget } from "../lib/shortSession";
import { useApi } from "../lib/useApi";
import { useToast } from "./Toast";

export function TodayWorkout({ refreshKey = 0, onNavigate }: { refreshKey?: number; onNavigate?: (p: Page) => void }) {
  const plan = useApi(api.currentPlan, [refreshKey], { cacheKey: "plan" });
  const p = plan.data;
  const toast = useToast();
  const [short, setShort] = useState<ShortSession | null>(null);

  async function showShort() {
    try {
      const s = await api.shortSession(10);
      if (s) setShort(s);
      else toast("Today's session has no moves that shrink to ten minutes.", "info");
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }
  return (
    <section className="card card-hover p-5" aria-labelledby="today-workout-title" data-testid="today-workout">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 id="today-workout-title" className="card-title">Today&apos;s workout</h2>
        {p && <span className="text-xs text-muted">{p.name}</span>}
      </div>
      {plan.loading && p === undefined ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : p ? (
        <>
          <p className="text-h3 text-ink">{p.next.name}</p>
          <p className="text-xs text-muted">{p.next.focus} · {p.next.items.length} exercises</p>
          <ul className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
            {p.next.items.slice(0, 6).map((it) => (
              <li key={it.exercise} className="flex justify-between gap-3">
                <span className="truncate text-ink">{it.exercise}</span>
                <span className="shrink-0 text-xs text-muted">{planTarget(it)}</span>
              </li>
            ))}
          </ul>
          {short && (
            <div className="mt-4 rounded-lg border border-accent/40 p-3" data-testid="short-session">
              <p className="text-sm text-ink">{short.minutes}-minute version</p>
              <ul className="mt-1 space-y-0.5 text-sm">
                {short.items.map((i) => (
                  <li key={i.exercise} className="flex justify-between gap-3">
                    <span className="truncate text-ink">{i.exercise}</span>
                    <span className="shrink-0 text-xs text-muted">{shortTarget(i)}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-1 text-[11px] text-muted">{short.note}</p>
            </div>
          )}
          {onNavigate && (
            <div className="mt-4 flex flex-wrap gap-2">
              {short ? (
                <>
                  <button type="button" className="btn-primary" onClick={() => { rememberShort(short); onNavigate("workout"); }}>Start {short.minutes}-minute session</button>
                  <button type="button" className="btn-ghost" onClick={() => setShort(null)}>Full session instead</button>
                </>
              ) : (
                <>
                  <button type="button" className="btn-primary" onClick={() => onNavigate("workout")}>Start workout</button>
                  <button type="button" className="btn-ghost" onClick={() => void showShort()}>Short on time? 10-minute version</button>
                </>
              )}
            </div>
          )}
        </>
      ) : (
        <>
          <p className="text-sm text-ink">No program yet.</p>
          <p className="text-xs text-muted">Pick one that fits your kit on Train; your trainer then lays out each day for you.</p>
          {onNavigate && <button type="button" className="btn-primary mt-4" onClick={() => onNavigate("workout")}>Pick a program</button>}
        </>
      )}
    </section>
  );
}
