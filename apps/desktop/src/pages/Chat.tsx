/**
 * Chat (v1.3): the trainer full size. A large portrait of the trainer you picked (it
 * follows the mood of the latest reply) beside the same conversation the Ctrl+K drawer
 * shows. Everything the drawer can do works here: ask, log, and confirm or undo cards.
 *
 * v1.4: "Build my plan" starts the trainer's optional plan interview (goal, weight, kit,
 * sport, days, appetite) with tap-to-answer chips. It is optional: telling the trainer
 * things in normal chat ("I have a punching bag") offers a plan update on its own.
 */
import type { ChatAction } from "@ascend/shared";
import { useState } from "react";

import { TrainerChat } from "../components/TrainerChat";
import { useTrainer } from "../components/Trainer";
import { latestMood, useChatMessages } from "../lib/chatStore";
import { moodLabel } from "../lib/trainer";

export function ChatPage({ onAction, onActionDone, onPickTrainer }: {
  onAction: (a: ChatAction) => void;
  onActionDone: () => void;
  onPickTrainer: () => void;
}) {
  const t = useTrainer();
  const [question, setQuestion] = useState<string | null>(null);
  const mood = latestMood(useChatMessages());
  // The portrait is the big neutral picture; a reply with feeling swaps in that mood's art.
  const src = mood === "neutral" ? t.portrait : t.art[mood];
  return (
    <div className="grid h-[calc(100vh-180px)] min-h-[520px] grid-cols-12 gap-5" data-testid="chat-page">
      <section aria-label={`${t.name}, your trainer`} className="col-span-12 flex flex-col overflow-hidden rounded-xl border border-line-2 bg-panel md:col-span-5 xl:col-span-4">
        <div className="relative min-h-0 flex-1 bg-panel-3">
          <img src={src} alt={moodLabel(mood, t.name)} data-mood={mood} data-trainer={t.id}
            className="absolute inset-0 h-full w-full object-cover object-top" />
        </div>
        <div className="space-y-1 border-t border-line p-4">
          <h2 className="text-lg font-semibold text-ink">{t.name}</h2>
          <p className="text-[11px] uppercase tracking-wider text-accent">{t.style}</p>
          <p className="text-sm text-muted">{t.blurb}</p>
          <p className="text-xs text-ink">Best at: {t.specialty}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" className="btn-primary px-3 py-1 text-xs" onClick={() => setQuestion("Build my plan")} data-testid="build-plan"
              title="A few quick questions, then a plan you can confirm or undo">Build my plan</button>
            <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={onPickTrainer}>Change trainer</button>
          </div>
        </div>
      </section>
      <div className="col-span-12 min-h-0 md:col-span-7 xl:col-span-8">
        <TrainerChat variant="page" open onClose={() => undefined} onAction={onAction} onActionDone={onActionDone}
          question={question} onAsked={() => setQuestion(null)}
          supports={["navigate", "tour", "trainer_picker", "planner"]} />
      </div>
    </div>
  );
}
