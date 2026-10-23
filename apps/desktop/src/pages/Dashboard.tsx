/**
 * Today ("Hunter HQ"): the Daily Quest window and the Status panel lead (both above the
 * fold at 1280×720), then insights and the morning check-in (which collapses to a
 * one-line summary once done), then fuel and the muscle recovery map. 12-column grid.
 */
import { useEffect, useRef, useState } from "react";

import type { CoachReply, WeeklyReview } from "@ascend/shared";

import { api } from "../api/client";
import { BossRaidCard } from "../components/BossRaid";
import { CheckinCard } from "../components/CheckinCard";
import { FirstSteps } from "../components/FirstSteps";
import { InsightsCard } from "../components/Insights";
import type { Page } from "../components/Layout";
import { MuscleMap } from "../components/MuscleMap";
import { DeloadCard } from "../components/PlanCards";
import { QuestWindow } from "../components/QuestWindow";
import { NotLoggedBanner, QuickLogCard } from "../components/QuickLog";
import { Rings } from "../components/Rings";
import { Delayed, LoadingLayout, Skeleton, SkeletonCard } from "../components/Skeleton";
import { StatusPanel } from "../components/StatusPanel";
import { ErrorState, StaleNotice } from "../components/States";
import { useToast } from "../components/Toast";
import { grams } from "../lib/format";
import { CountUp } from "../lib/motion";
import { isOffline, useApi } from "../lib/useApi";

export function DashboardPage({ onOpenChat, refreshKey, onChanged, onNavigate }: {
  onOpenChat: () => void;
  refreshKey: number;
  onChanged?: () => void;
  onNavigate?: (p: Page) => void;
}) {
  const { data, error, status, loading, reload } = useApi(api.dashboard, [refreshKey], { cacheKey: "dashboard" });
  const stats = useApi(api.stats, [refreshKey], { cacheKey: "stats" });
  const boss = useApi(api.boss, [refreshKey], { cacheKey: "boss" });
  const titles = useApi(api.titles, [refreshKey], { cacheKey: "titles" });
  const profile = useApi(api.profile, [], { cacheKey: "profile" });
  const [tip, setTip] = useState<CoachReply | null>(null);
  const [review, setReview] = useState<WeeklyReview | null>(null);
  const toast = useToast();
  const quickLog = useRef<HTMLElement>(null);

  useEffect(() => {
    api.coachTip().then(setTip).catch(() => setTip(null));
    api.weeklyReview().then(setReview).catch(() => setReview(null));
  }, [refreshKey]);

  // Cached data paints at once on return; a first load only shows the skeleton if it is slow.
  if (loading && !data) return <Delayed><DashboardSkeleton /></Delayed>;
  if (!data) return <ErrorState message={error ?? "No data"} onRetry={reload} offline={isOffline(status)} />;

  function openQuickLog() {
    quickLog.current?.scrollIntoView({ block: "center", behavior: "smooth" });
    quickLog.current?.querySelector<HTMLInputElement>("input")?.focus({ preventScroll: true });
  }

  async function complete(id: number) {
    try {
      const item = await api.completeQuest(id);
      toast(`Quest item complete · +${item.xp} XP`, "xp");
      // Refreshes the whole shell, so the top bar animates the gain too.
      if (onChanged) onChanged();
      else reload();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  const n = data.nutrition;
  return (
    <div className="grid grid-cols-12 gap-6">
      {error && <div className="col-span-12"><StaleNotice message={error} onRetry={reload} /></div>}
      {onNavigate && data.game.xp.total === 0 && <FirstSteps onNavigate={onNavigate} />}
      {data.has_profile && data.game.xp.total > 0 && !data.game.streak.active_today && (
        <div className="col-span-12"><NotLoggedBanner onOpen={openQuickLog} /></div>
      )}
      <div className="col-span-12 lg:col-span-8">
        <QuestWindow items={data.game.quest} rank={data.game.xp.rank} onComplete={complete} onStart={onNavigate ? () => onNavigate("workout") : undefined} />
      </div>
      <div className="col-span-12 lg:col-span-4">
        <StatusPanel game={data.game} stats={stats.data} title={titles.data?.[0]?.title ?? null} titlesEarned={titles.data?.length ?? 0} name={profile.data?.name ?? null} />
      </div>

      {boss.data && <div className="col-span-12"><BossRaidCard boss={boss.data} /></div>}

      <DeloadCard refreshKey={refreshKey} onlyWhenRecommended className="col-span-12" />

      <div className="col-span-12 lg:col-span-7">
        <InsightsCard tip={tip} review={review} onOpenChat={onOpenChat} />
      </div>
      <div className="col-span-12 space-y-6 self-start lg:col-span-5">
        <section className="card card-hover p-5" aria-labelledby="checkin-title">
          <h2 id="checkin-title" className="card-title mb-3">Morning check-in</h2>
          <CheckinCard refreshKey={refreshKey} onSaved={reload} />
        </section>
        <QuickLogCard ref={quickLog} onLogged={(what) => { toast(`${what} · logged`, "info"); if (onChanged) onChanged(); else reload(); }} />
      </div>


      <section className="card card-hover col-span-12 self-start p-5 lg:col-span-4" aria-labelledby="fuel-title">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="fuel-title" className="card-title">Fuel</h2>
          {onNavigate && <button type="button" className="text-xs text-accent hover:underline" onClick={() => onNavigate("diet")}>Log a meal →</button>}
        </div>
        <Rings tasks={data.rings.tasks} kcalIn={data.rings.kcal_in} kcalOut={data.rings.kcal_out} />
        <div className="mt-5 grid grid-cols-3 gap-2 border-t border-line pt-4 text-center text-xs">
          <Macro label="Protein" value={n.protein_g} />
          <Macro label="Carbs" value={n.carbs_g} />
          <Macro label="Fat" value={n.fat_g} />
        </div>
      </section>
      <section className="card col-span-12 p-5 lg:col-span-8" aria-labelledby="recovery-title">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="recovery-title" className="card-title">Muscle recovery</h2>
          <span className="text-[11px] text-faint">Hover for sets and last trained · click for details (estimates)</span>
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
      <div className="grid grid-cols-12 gap-6">
        <SkeletonCard className="col-span-12 lg:col-span-8" lines={4} />
        <SkeletonCard className="col-span-12 lg:col-span-4" lines={4} />
        <SkeletonCard className="col-span-12 lg:col-span-7" lines={3} />
        <SkeletonCard className="col-span-12 lg:col-span-5" lines={3} />
        <div className="card col-span-12 flex items-center gap-6 p-5 lg:col-span-4" aria-hidden="true">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-20 w-20 rounded-full" />)}
        </div>
        <div className="card col-span-12 flex gap-5 p-5 lg:col-span-8" aria-hidden="true">
          <Skeleton className="h-64 w-40" />
          <div className="flex-1 space-y-3">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-4 w-full" />)}
          </div>
        </div>
      </div>
    </LoadingLayout>
  );
}
