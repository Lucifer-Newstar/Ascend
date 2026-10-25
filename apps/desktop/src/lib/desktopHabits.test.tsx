import type { AscendBridge, TrayAction } from "@ascend/shared";
import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useDesktopHabits } from "./desktopHabits";

function Probe(props: { tray: boolean; startWithWindows: boolean; onTrayAction: (a: TrayAction) => void }) {
  useDesktopHabits(props);
  return null;
}

describe("useDesktopHabits", () => {
  afterEach(() => {
    delete (window as { ascend?: AscendBridge }).ascend;
  });

  it("hands both switches to the shell and follows tray picks", () => {
    let listener: ((a: TrayAction) => void) | null = null;
    const off = vi.fn();
    const setDesktopHabits = vi.fn().mockResolvedValue({ tray: true, openAtLogin: false });
    window.ascend = {
      setDesktopHabits,
      onTrayAction: (cb: (a: TrayAction) => void) => { listener = cb; return off; },
    } as unknown as AscendBridge;
    const onTrayAction = vi.fn();
    const { rerender, unmount } = render(<Probe tray startWithWindows={false} onTrayAction={onTrayAction} />);
    expect(setDesktopHabits).toHaveBeenLastCalledWith({ tray: true, openAtLogin: false });
    rerender(<Probe tray={false} startWithWindows onTrayAction={onTrayAction} />);
    expect(setDesktopHabits).toHaveBeenLastCalledWith({ tray: false, openAtLogin: true });
    listener!("start-workout");
    expect(onTrayAction).toHaveBeenCalledWith("start-workout");
    unmount();
    expect(off).toHaveBeenCalledTimes(1);
  });

  it("does nothing without the desktop shell", () => {
    expect(() => render(<Probe tray startWithWindows onTrayAction={vi.fn()} />)).not.toThrow();
  });
});
