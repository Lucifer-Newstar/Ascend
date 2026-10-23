import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Tone = "info" | "xp" | "pr" | "error";
interface ToastItem {
  id: number;
  text: string;
  tone: Tone;
}

const ToastCtx = createContext<(text: string, tone?: Tone) => void>(() => undefined);

export function useToast() {
  return useContext(ToastCtx);
}

const TONES: Record<Tone, string> = {
  info: "border-line-2 text-ink",
  xp: "border-xp/40 text-xp",
  pr: "border-warn/50 text-warn",
  error: "border-bad/50 text-bad",
};

/** Errors stay longer: they usually need reading, not just noticing. */
export const TOAST_MS: Record<Tone, number> = { info: 3500, xp: 3500, pr: 4500, error: 7000 };

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const dismiss = useCallback((id: number) => setItems((xs) => xs.filter((x) => x.id !== id)), []);
  const push = useCallback(
    (text: string, tone: Tone = "info") => {
      const id = Date.now() + Math.random();
      // The same message again replaces the old one instead of stacking ("Set logged" x3
      // covered the session log's Edit buttons).
      setItems((xs) => [...xs.filter((x) => x.text !== text || x.tone !== tone), { id, text, tone }]);
      setTimeout(() => dismiss(id), TOAST_MS[tone]);
    },
    [dismiss],
  );
  const polite = items.filter((t) => t.tone !== "error");
  const errors = items.filter((t) => t.tone === "error");
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-5 right-5 z-50 flex flex-col items-end gap-2">
        {/* Two live regions: errors interrupt (assertive), everything else waits its turn. */}
        <div role="alert" aria-live="assertive" className="flex flex-col items-end gap-2">
          {errors.map((t) => <ToastCard key={t.id} item={t} onDismiss={dismiss} />)}
        </div>
        <div role="status" aria-live="polite" className="flex flex-col items-end gap-2">
          {polite.map((t) => <ToastCard key={t.id} item={t} onDismiss={dismiss} />)}
        </div>
      </div>
    </ToastCtx.Provider>
  );
}

function ToastCard({ item, onDismiss }: { item: ToastItem; onDismiss: (id: number) => void }) {
  return (
    <div className={`pointer-events-auto flex items-center gap-3 rounded-lg border bg-panel-2/95 py-2.5 pl-4 pr-2 text-sm font-medium shadow-xl shadow-black/40 ${TONES[item.tone]}`}>
      <span>{item.text}</span>
      <button
        type="button"
        onClick={() => onDismiss(item.id)}
        aria-label="Dismiss notification"
        className="rounded px-1.5 text-base leading-none text-muted hover:text-ink"
      >
        ×
      </button>
    </div>
  );
}
