import { useEffect, useState } from "react";

import type { CoachReply } from "@ascend/shared";

import { api } from "../api/client";
import { CheckinCard } from "../components/CheckinCard";
import { FirstSteps } from "../components/FirstSteps";
import type { Page } from "../components/Layout";
import { IconSpark } from "../components/Icons";
import { MuscleMap } from "../components/MuscleMap";
import { QuestList } from "../components/QuestCard";
import { Rings } from "../components/Rings";
import { Delayed, LoadingLayout, Skeleton, SkeletonCard } from "../components/Skeleton";
import { ErrorState, StaleNotice } from "../components/States";
import { useToast } from "../components/Toast";
import { XpBar } from "../components/XpBar";
import { grams } from "../lib/format";
import { CountUp } from "../lib/motion";
import { isOffline, useApi } from "../lib/useApi";

export function DashboardPage({ onOpenCoach, refreshKey, onChanged, onNavigate }: {
  onOpenCoach: () => void;
  refreshKey: number;
  onChanged?: () => void;
  onNavigate?: (p: Page) => void;
}) {
  const { data, error, status, loading, reload } = useApi(api.dashboard, [refreshKey], { cacheKey: "dashboard" });
  const [tip, setTip] = useState<CoachReply | null>(null);
  const toast = useToast();

  useEffect(() => {
    api.coachTip().then(setTip).catch(() => setTip(null));
  }, [refreshKey]);

  // Cached data paints at once on return; a first load only shows the skeleton if it is slow.
  if (loading && !data) return <Delayed><DashboardSkeleton /></Delayed>;
  if (!data) return <ErrorState message={error ?? "No data"} onRetry={reload} offline={isOffline(status)} />;

  async function complete(id: number) {
    try {
      const item = await api.completeQuest(id);
      toast(`Quest item complete · +${item.xp} XP`, "xp");
      // Refreshes the whole shell, so the header XP chip animates the gain too.
      if (onChanged) onChanged();
      else reload();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  const n = data.nutrition;
  return (
    <div className="grid grid-cols-12 gap-5">
      {error && <div className="col-span-12"><StaleNotice message={error} onRetry={reload} /></div>}
      {onNavigate && data.game.xp.total === 0 && <FirstSteps onNavigate={onNavigate} />}
      <section className="card card-hover col-span-12 p-5 xl:col-span-8"><XpBar xp={data.game.xp} streak={data.game.streak} /></section>
      <section className="card card-hover card-lift col-span-12 flex flex-col justify-between p-5 xl:col-span-4">
        <div className="flex items-center justify-between">
          <h2 className="card-title">Coach</h2>
          {tip && (
            <span className="flex items-center gap-1 text-[11px] text-faint">
              <IconSpark width={12} height={12} /> {tip.source === "ollama" ? `Local AI · ${tip.model}` : "Rule-based tip"}
            </span>
          )}
        </div>
        <p className="mt-2 text-sm leading-relaxed text-ink">{tip ? tip.text : "…"}</p>
        <button type="button" className="mt-3 self-start text-xs text-accent hover:underline" onClick={onOpenCoach}>Ask the coach →</button>
      </section>

      <section className="card card-hover col-span-12 p-5" aria-labelledby="checkin-title">
        <h2 id="checkin-title" className="card-title mb-3">Morning check-in</h2>
        <CheckinCard refreshKey={refreshKey} onSaved={reload} />
      </section>

      <section className="card card-hover card-lift col-span-12 p-5 lg:col-span-5">
        <h2 className="card-title mb-4">Today</h2>
        <Rings tasks={data.rings.tasks} kcalIn={data.rings.kcal_in} kcalOut={data.rings.kcal_out} />
        <div className="mt-5 grid grid-cols-3 gap-2 border-t border-line pt-4 text-center text-xs">
          <Macro label="Protein" value={n.protein_g} />
          <Macro label="Carbs" value={n.carbs_g} />
          <Macro label="Fat" value={n.fat_g} />
        </div>
      </section>
      <section className="card card-hover col-span-12 p-5 lg:col-span-7">
        <QuestList items={data.game.quest} onComplete={complete} />
      </section>

      <section className="card col-span-12 p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="card-title">Muscle recovery</h2>
          <span className="text-[11px] text-faint">Hover a muscle for sets, volume and last trained · click for details (estimates)</span>
        </div>
        <MuscleMap muscles={data.muscles} refreshKey={refreshKey} />
      </section>
    </div>
  );
}

function Macro({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-faint">{label}</div>
      <div className="mt-0.5 font-semibold text-ink"><CountUp value={value} format={grams} /></div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <LoadingLayout label="Loading your day…">
      <div className="grid grid-cols-12 gap-5">
        <SkeletonCard className="col-span-12 xl:col-span-8" lines={2} />
        <SkeletonCard className="col-span-12 xl:col-span-4" lines={2} />
        <div className="card col-span-12 flex items-center gap-6 p-5 lg:col-span-5" aria-hidden="true">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-24 w-24 rounded-full" />)}
        </div>
        <SkeletonCard className="col-span-12 lg:col-span-7" lines={3} />
        <div className="card col-span-12 flex gap-5 p-5" aria-hidden="true">
          <Skeleton className="h-64 w-40" />
          <Skeleton className="h-64 w-40" />
          <div className="flex-1 space-y-3">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-4 w-full" />)}
          </div>
        </div>
      </div>
    </LoadingLayout>
  );
}
