/**
 * Today (v1.2): only what matters today. The daily quest and your status (rank and streak)
 * lead, then today's workout, the morning check-in (mornings only) and the weekly boss.
 * Insights, the muscle map and fuel live on their own pages. 12-column grid.
 */
import type { Page } from "../components/Layout";
import { api } from "../api/client";
import { BossRaidCard } from "../components/BossRaid";
import { CheckinCard } from "../components/CheckinCard";
import { FirstSteps } from "../components/FirstSteps";
import { StreakReasonCard } from "../components/StreakReason";
import { QuestWindow } from "../components/QuestWindow";
import { Delayed, LoadingLayout, SkeletonCard } from "../components/Skeleton";
import { StatusPanel } from "../components/StatusPanel";
import { ErrorState, StaleNotice } from "../components/States";
import { useToast } from "../components/Toast";
import { TodayWorkout } from "../components/TodayWorkout";
import { isOffline, useApi } from "../lib/useApi";

/** The morning check-in shows until noon (local time). */
export const isMorning = (d: Date = new Date()): boolean => d.getHours() < 12;

export function DashboardPage({ refreshKey, onChanged, onNavigate, now }: {
  /** Kept for callers; the trainer chat is opened from the top bar. */
  onOpenChat?: () => void;
  refreshKey: number;
  onChanged?: () => void;
  onNavigate?: (p: Page) => void;
  /** For tests: the clock that decides whether it is still morning. */
  now?: () => Date;
}) {
  const { data, error, status, loading, reload } = useApi(api.dashboard, [refreshKey], { cacheKey: "dashboard" });
  const stats = useApi(api.stats, [refreshKey], { cacheKey: "stats" });
  const boss = useApi(api.boss, [refreshKey], { cacheKey: "boss" });
  const titles = useApi(api.titles, [refreshKey], { cacheKey: "titles" });
  const profile = useApi(api.profile, [], { cacheKey: "profile" });
  const toast = useToast();

  // Cached data paints at once on return; a first load only shows the skeleton if it is slow.
  if (loading && !data) return <Delayed><DashboardSkeleton /></Delayed>;
  if (!data) return <ErrorState message={error ?? "No data"} onRetry={reload} offline={isOffline(status)} />;

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

  const morning = isMorning(now ? now() : new Date());
  return (
    <div className="grid grid-cols-12 gap-6">
      {error && <div className="col-span-12"><StaleNotice message={error} onRetry={reload} /></div>}
      {onNavigate && data.game.xp.total === 0 && <FirstSteps onNavigate={onNavigate} />}
      {data.game.streak.reason_due && (
        <div className="col-span-12"><StreakReasonCard streak={data.game.streak} onSaved={onChanged ?? reload} /></div>
      )}
      <div className="col-span-12 lg:col-span-8">
        <QuestWindow items={data.game.quest} rank={data.game.xp.rank} onComplete={complete} onStart={onNavigate ? () => onNavigate("workout") : undefined} />
      </div>
      <div className="col-span-12 lg:col-span-4">
        <StatusPanel game={data.game} stats={stats.data} title={titles.data?.[0]?.title ?? null} titlesEarned={titles.data?.length ?? 0} name={profile.data?.name ?? null} />
      </div>
      <div className={`col-span-12 ${morning ? "lg:col-span-8" : ""}`}>
        <TodayWorkout refreshKey={refreshKey} onNavigate={onNavigate} />
      </div>
      {morning && (
        <section className="card card-hover col-span-12 self-start p-5 lg:col-span-4" aria-labelledby="checkin-title">
          <h2 id="checkin-title" className="card-title mb-3">Morning check-in</h2>
          <CheckinCard refreshKey={refreshKey} onSaved={reload} />
        </section>
      )}
      {boss.data && <div className="col-span-12"><BossRaidCard boss={boss.data} /></div>}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <LoadingLayout label="Loading your day…">
      <div className="grid grid-cols-12 gap-6">
        <SkeletonCard className="col-span-12 lg:col-span-8" lines={4} />
        <SkeletonCard className="col-span-12 lg:col-span-4" lines={4} />
        <SkeletonCard className="col-span-12 lg:col-span-8" lines={3} />
        <SkeletonCard className="col-span-12 lg:col-span-4" lines={3} />
      </div>
    </LoadingLayout>
  );
}
