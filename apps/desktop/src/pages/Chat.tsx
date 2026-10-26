/**
 * Chat (v1.3): the trainer full size. A large portrait of the trainer you picked (it
 * follows the mood of the latest reply) beside the same conversation the Ctrl+K drawer
 * shows. Everything the drawer can do works here: ask, log, and confirm or undo cards.
 *
 * v1.4: "Build my plan" starts the trainer's optional plan interview (goal, weight, kit,
 * sport, days, appetite) with tap-to-answer chips. It is optional: telling the trainer
 * things in normal chat ("I have a punching bag") offers a plan update on its own.
 *
 * Coaching team (item 13): the trainer you picked is the main one. When a specialist
 * answers, the big portrait and the name switch to them until the main trainer speaks
 * again; "Your team" lists who covers what (hidden when the team is off in Settings).
 */
import type { ChatAction } from "@ascend/shared";
import { useState } from "react";

import { TrainerChat } from "../components/TrainerChat";
import { useTrainer } from "../components/Trainer";
import { latestMood, latestSpeaker, useChatMessages } from "../lib/chatStore";
import { useOptionalPrefs } from "../lib/prefs";
import { moodLabel, teamFor, trainerById } from "../lib/trainer";

export function ChatPage({ onAction, onActionDone, onPickTrainer }: {
  onAction: (a: ChatAction) => void;
  onActionDone: () => void;
  onPickTrainer: () => void;
}) {
  const main = useTrainer();
  const teamOn = useOptionalPrefs()?.settings.team_handoff !== false;
  const [question, setQuestion] = useState<string | null>(null);
  const msgs = useChatMessages();
  const mood = latestMood(msgs);
  const speakerId = latestSpeaker(msgs);
  // The trainer on screen: the specialist answering right now, else your main trainer.
  const t = speakerId ? trainerById(speakerId) : main;
  const specialist = t.id !== main.id;
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
          <h2 className="text-lg font-semibold text-ink" data-testid="chat-speaker">{t.name}</h2>
          <p className="text-[11px] uppercase tracking-wider text-accent">{specialist ? `Specialist · ${main.short} runs your chat` : `${t.style} · main trainer`}</p>
          <p className="text-sm text-muted">{t.blurb}</p>
          <p className="text-xs text-ink">Best at: {t.specialty}</p>
          {teamOn && (
            <div className="pt-1" data-testid="team-row">
              <p className="text-[11px] uppercase tracking-wider text-faint">Your team</p>
              <ul className="mt-1 flex flex-wrap gap-1.5">
                {teamFor(main.id).map(({ trainer, area }) => (
                  <li key={trainer.id} title={`${trainer.name}: ${area}`} data-trainer={trainer.id}
                    className={`flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[11px] ${trainer.id === t.id ? "border-accent text-ink" : "border-line-2 text-muted"}`}>
                    <img src={trainer.icon} alt="" width={16} height={16} className="rounded-full" />
                    {trainer.short} <span className="text-faint">· {area}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" className="btn-primary px-3 py-1 text-xs" onClick={() => setQuestion("Build my plan")} data-testid="build-plan"
              title="A few quick questions, then a plan you can confirm or undo">Build my plan</button>
            <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={onPickTrainer}>Change main trainer</button>
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
