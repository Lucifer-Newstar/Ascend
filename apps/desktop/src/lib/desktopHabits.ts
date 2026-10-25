/**
 * The desktop side of the habit engine (v1.4, review 2.2): hands the tray and
 * start-with-Windows switches to the Electron shell, and turns a tray menu pick into
 * navigation. Both switches are opt-in; in a plain browser (no bridge) this does nothing.
 */
import type { AscendBridge, TrayAction } from "@ascend/shared";
import { useEffect, useRef } from "react";

const bridge = (): AscendBridge | undefined => (typeof window !== "undefined" ? window.ascend : undefined);

export function useDesktopHabits({ tray, startWithWindows, onTrayAction }: {
  tray: boolean;
  startWithWindows: boolean;
  onTrayAction: (a: TrayAction) => void;
}): void {
  useEffect(() => {
    const b = bridge();
    if (!b?.setDesktopHabits) return;
    void b.setDesktopHabits({ tray, openAtLogin: startWithWindows }).catch(() => undefined);
  }, [tray, startWithWindows]);

  // The latest handler, without re-subscribing on every render.
  const handler = useRef(onTrayAction);
  useEffect(() => {
    handler.current = onTrayAction;
  }, [onTrayAction]);
  useEffect(() => {
    const b = bridge();
    if (!b?.onTrayAction) return;
    return b.onTrayAction((a) => handler.current(a));
  }, []);
}
