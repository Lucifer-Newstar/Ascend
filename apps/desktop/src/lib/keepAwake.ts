/**
 * Keep the screen awake while the full-screen timer runs (v1.2). In the desktop app this
 * asks Electron's power-save blocker (no dimming, no sleep); in a plain browser it uses
 * the Screen Wake Lock API when there is one. Released when the timer ends or closes.
 */
import { useEffect } from "react";

type WakeLock = { release(): Promise<void> };
type WakeNavigator = Navigator & { wakeLock?: { request(kind: "screen"): Promise<WakeLock> } };

export async function setKeepAwake(on: boolean): Promise<() => void> {
  const bridge = typeof window !== "undefined" ? window.ascend : undefined;
  if (bridge?.keepAwake) {
    await bridge.keepAwake(on).catch(() => false);
    return () => void bridge.keepAwake(false).catch(() => false);
  }
  const nav = (typeof navigator !== "undefined" ? navigator : undefined) as WakeNavigator | undefined;
  if (on && nav?.wakeLock) {
    try {
      const lock = await nav.wakeLock.request("screen");
      return () => void lock.release().catch(() => undefined);
    } catch {
      return () => undefined;
    }
  }
  return () => undefined;
}

/** Holds the screen awake while `active` is true. */
export function useKeepAwake(active: boolean): void {
  useEffect(() => {
    if (!active) return;
    let release: (() => void) | null = null;
    let gone = false;
    void setKeepAwake(true).then((r) => {
      if (gone) r();
      else release = r;
    });
    return () => {
      gone = true;
      release?.();
    };
  }, [active]);
}
