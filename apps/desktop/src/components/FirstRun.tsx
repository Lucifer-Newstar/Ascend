/**
 * The 1.1 welcome for an existing install, shown once (until /trainer/state says onboarded).
 * A brand-new user never sees it: onboarding (profile, baseline, trainer) runs straight into
 * the app tour, one first-run flow. Here an upgrader is offered the tour. When data is already here (an upgrade, or demo data from a development
 * build) it also offers "start fresh", which backs up and erases it.
 */
import type { EraseResult, TrainerState } from "@ascend/shared";
import { useEffect, useRef, useState } from "react";

import { EraseDialog } from "./EraseData";
import { TrainerPortrait, useTrainer } from "./Trainer";

export function FirstRunCard({
  state,
  onTour,
  onDone,
  onErased,
}: {
  state: TrainerState;
  onTour: () => void;
  onDone: () => void;
  onErased: (r: EraseResult) => void;
}) {
  const trainer = useTrainer();
  const [erasing, setErasing] = useState(false);
  const first = useRef<HTMLButtonElement>(null);
  useEffect(() => first.current?.focus(), []);
  const hasData = state.has_history;
  return (
    <div className="fixed inset-0 z-40 flex overflow-y-auto bg-[rgba(3,7,18,0.6)] p-4" onMouseDown={(e) => { if (e.target === e.currentTarget && !erasing) onDone(); }}>
      <div role="dialog" aria-modal="true" aria-labelledby="welcome-title" className="m-auto w-full max-w-lg rounded-xl border border-accent/50 bg-panel p-6 shadow-2xl">
        <div className="flex items-start gap-4">
          <TrainerPortrait mood="hyped" size={88} />
          <div className="min-w-0">
            <h2 id="welcome-title" className="text-lg font-semibold text-ink">{hasData ? "Welcome to ASCEND" : "You're set up"}</h2>
            <p className="mt-1 text-sm text-muted">
              I&apos;m {trainer.name}, your trainer. I watch your log, answer questions and show you around. Open the chat any time from Trainer in the top bar.
            </p>
            {hasData && (
              <p className="mt-2 text-sm text-ink" data-testid="welcome-data-note">
                {state.demo_data
                  ? "This copy has demo data in it, not yours."
                  : "There is already data here."}{" "}
                If it isn&apos;t yours, start fresh: I back it up first and keep the exercise library.
              </p>
            )}
          </div>
        </div>
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          {hasData && (
            <button type="button" className="btn-ghost border-bad/60 text-bad hover:border-bad hover:text-bad" onClick={() => setErasing(true)}>
              Start fresh…
            </button>
          )}
          <button type="button" className="btn-ghost" onClick={onDone}>{hasData ? "Keep my data" : "Maybe later"}</button>
          <button ref={first} type="button" className="btn-primary" onClick={onTour}>Take the tour</button>
        </div>
      </div>
      {erasing && <EraseDialog onClose={() => setErasing(false)} onErased={(r) => { setErasing(false); onErased(r); }} />}
    </div>
  );
}
