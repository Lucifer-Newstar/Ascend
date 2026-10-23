/**
 * Settings → Today's numbers (v8 hardening): an audit of every number Today shows, with
 * the engine and version that computed it, how it is computed and how much data it rests
 * on. Numbers from too little data are marked "rough". Read-only: it calls the same
 * endpoints Today does and adds nothing of its own.
 */
import type { Dashboard, Stats, TdeeReport } from "@ascend/shared";
import type { ReactNode } from "react";

import { api } from "../api/client";
import { kcal, num } from "../lib/format";
import { useApi } from "../lib/useApi";
import { RoughBadge } from "./RoughBadge";
import { ErrorState, Loading } from "./States";

interface Row {
  key: string;
  name: string;
  value: string;
  how: string;
  data: ReactNode;
}

const inputsText = (inputs: Record<string, number | string | null>) =>
  Object.entries(inputs).map(([k, v]) => `${k.replace(/_/g, " ")} ${v ?? "–"}`).join(" · ");

export function todaysRows(d: Dashboard, stats: Stats | null, tdee: TdeeReport | null): Row[] {
  const x = d.game.xp;
  const s = d.game.streak;
  const rows: Row[] = [
    { key: "level", name: "Level and rank", value: `Level ${x.level} · ${x.rank} (${x.rank_title})`, how: `Level from total XP (${x.formula_version}); rank from level.`, data: `${num(x.total)} XP in total · ${num(x.xp_into_level)} of ${num(x.xp_for_next)} into this level` },
    { key: "xp-today", name: "XP today", value: `${x.today}`, how: `Sum of today's XP events, capped at ${x.daily_cap} a day.`, data: `daily cap ${x.daily_cap}` },
    { key: "streak", name: "Streak", value: `${s.current} days`, how: "Days in a row with a finished workout, a completed quest item, or any quick log (a set, a meal or a weigh-in). A missed day is kept with a reason given by the next day; two missed days in a row reset it.", data: `best ${s.best} · ${s.excused} kept with a reason · ${s.active_today ? "today counts" : "nothing logged today yet"}` },
  ];
  for (const q of d.game.quest) {
    rows.push({ key: `quest-${q.id}`, name: `Quest: ${q.title}`, value: `${q.progress} / ${q.target}`, how: `Progress read from your logs (metric "${q.metric}"); +${q.xp} XP when done.`, data: q.completed_at ? "completed" : q.detail });
  }
  const ring = (key: string, name: string, r: Dashboard["rings"]["tasks"], how: string) =>
    rows.push({ key, name, value: `${kcalOr(r.value)} of ${kcalOr(r.target)}`, how, data: r.is_estimate ? "estimate" : "from your logs" });
  ring("ring-tasks", "Ring: quest tasks", d.rings.tasks, "Quest items completed today out of today's items.");
  ring("ring-in", "Ring: kcal eaten", d.rings.kcal_in, "Sum of today's logged meals against this week's calorie target (adaptive when tdee-v1 has enough data, else the formula).");
  ring("ring-out", "Ring: kcal burned", d.rings.kcal_out, "Estimated kcal of today's workouts (session length, lifting sets, and MET × body weight × time for timed activities) against a fixed goal.");
  for (const st of stats?.stats ?? []) {
    rows.push({ key: `stat-${st.key}`, name: `Stat ${st.label}`, value: `${st.value}`, how: `${st.formula} (${stats?.version}, last ${stats?.window_days} days)`, data: inputsText(st.inputs) });
  }
  const tracked = d.muscles.filter((m) => !m.readiness_only);
  const by = (st: string) => tracked.filter((m) => m.status === st).length;
  rows.push({
    key: "muscles", name: "Muscle map", value: `${by("optimal")} in band · ${by("under")} under · ${by("over")} over · ${by("recovering")} recovering`,
    how: `recovery-v2 per muscle: effective sets in 7 days against the weekly band, readiness from each set's dose decayed by the muscle's half-life. ${d.muscles.length - tracked.length} small muscles show readiness only.`,
    data: `${d.muscles.length} muscles and heads (taxonomy v2)`,
  });
  if (tdee) {
    rows.push({
      key: "tdee", name: "Energy burned per day", value: `${kcal(tdee.tdee_kcal)} kcal (${kcal(tdee.low_kcal)}–${kcal(tdee.high_kcal)})`,
      how: `${tdee.algo_version}: ${tdee.status === "adaptive" ? "from your weigh-in trend and logged intake" : "mostly the Mifflin-St Jeor formula until there is enough data"}.`,
      data: <>{tdee.days_of_data} days of data · {tdee.weigh_ins} weigh-ins {tdee.status !== "adaptive" && <RoughBadge n={tdee.days_of_data} unit="days" enough={14} className="ml-1" />}</>,
    });
  }
  return rows;
}

const kcalOr = (n: number) => (Number.isInteger(n) ? `${n}` : n.toFixed(1));

export function TodaysNumbers() {
  const dash = useApi(api.dashboard, [], { cacheKey: "dashboard" });
  const stats = useApi(api.stats, [], { cacheKey: "stats" });
  const tdee = useApi(() => api.tdee(56), []);
  if (dash.loading && !dash.data) return <Loading label="Reading today's numbers…" />;
  if (!dash.data) return <ErrorState message={dash.error ?? "No data"} onRetry={dash.reload} />;
  const rows = todaysRows(dash.data, stats.data ?? null, tdee.data ?? null);
  return (
    <div className="max-h-[28rem] overflow-y-auto">
      <table className="w-full text-left text-xs">
        <caption className="sr-only">Every number on Today, how it is computed and the data behind it</caption>
        <thead className="sticky top-0 bg-panel text-[11px] uppercase tracking-wide text-faint">
          <tr><th scope="col" className="py-1.5 pr-3">Number</th><th scope="col" className="py-1.5 pr-3">Value</th><th scope="col" className="py-1.5">How and from what</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} className="border-t border-line/60 align-top">
              <th scope="row" className="py-2 pr-3 font-medium text-ink">{r.name}</th>
              <td className="py-2 pr-3 tabular-nums text-ink">{r.value}</td>
              <td className="py-2 text-muted">{r.how}<div className="mt-0.5 text-faint">{r.data}</div></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
