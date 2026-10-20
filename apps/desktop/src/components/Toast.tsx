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

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((text: string, tone: Tone = "info") => {
    const id = Date.now() + Math.random();
    setItems((xs) => [...xs, { id, text, tone }]);
    setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 3500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-5 right-5 z-50 flex flex-col items-end gap-2" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`rounded-lg border bg-panel-2/95 px-4 py-2.5 text-sm font-medium shadow-xl shadow-black/40 ${TONES[t.tone]}`}>
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
