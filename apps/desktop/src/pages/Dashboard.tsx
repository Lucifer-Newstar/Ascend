import { useEffect, useState } from "react";

import type { CoachReply } from "@ascend/shared";

import { api } from "../api/client";
import { IconSpark } from "../components/Icons";
import { MuscleMap } from "../components/MuscleMap";
import { QuestList } from "../components/QuestCard";
import { Rings } from "../components/Rings";
import { ErrorState, Loading } from "../components/States";
import { useToast } from "../components/Toast";
import { XpBar } from "../components/XpBar";
import { grams } from "../lib/format";
import { useApi } from "../lib/useApi";

export function DashboardPage({ onOpenCoach, refreshKey }: { onOpenCoach: () => void; refreshKey: number }) {
  const { data, error, loading, reload } = useApi(api.dashboard, [refreshKey]);
  const [tip, setTip] = useState<CoachReply | null>(null);
  const toast = useToast();

  useEffect(() => {
    api.coachTip().then(setTip).catch(() => setTip(null));
  }, [refreshKey]);

  if (loading && !data) return <Loading label="Loading your day…" />;
  if (error || !data) return <ErrorState message={error ?? "No data"} onRetry={reload} />;

  async function complete(id: number) {
    try {
      const item = await api.completeQuest(id);
      toast(`Quest item complete · +${item.xp} XP`, "xp");
      reload();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  const n = data.nutrition;
  return (
    <div className="grid grid-cols-12 gap-5">
      <section className="card col-span-12 p-5 xl:col-span-8"><XpBar xp={data.game.xp} streak={data.game.streak} /></section>
      <section className="card col-span-12 flex flex-col justify-between p-5 xl:col-span-4">
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

      <section className="card col-span-12 p-5 lg:col-span-5">
        <h2 className="card-title mb-4">Today</h2>
        <Rings tasks={data.rings.tasks} kcalIn={data.rings.kcal_in} kcalOut={data.rings.kcal_out} />
        <div className="mt-5 grid grid-cols-3 gap-2 border-t border-line pt-4 text-center text-xs">
          <Macro label="Protein" value={grams(n.protein_g)} />
          <Macro label="Carbs" value={grams(n.carbs_g)} />
          <Macro label="Fat" value={grams(n.fat_g)} />
        </div>
      </section>
      <section className="card col-span-12 p-5 lg:col-span-7">
        <QuestList items={data.game.quest} onComplete={complete} />
      </section>

      <section className="card col-span-12 p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="card-title">Muscle recovery</h2>
          <span className="text-[11px] text-faint">7-day effective sets vs target band · recovery decay (estimates)</span>
        </div>
        <MuscleMap muscles={data.muscles} />
      </section>
    </div>
  );
}

function Macro({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-faint">{label}</div>
      <div className="mt-0.5 font-semibold text-ink">{value}</div>
    </div>
  );
}
