import { act, render, renderHook, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Transient, useRise } from "./Celebrate";

describe("useRise", () => {
  it("treats the first value as a baseline and reports a rise in the same render", () => {
    const seen: number[] = [];
    const { result, rerender } = renderHook(({ v }: { v: number | undefined }) => {
      const r = useRise(v);
      seen.push(r.riseKey);
      return r;
    }, { initialProps: { v: undefined as number | undefined } });
    expect(result.current).toEqual({ riseKey: 0, delta: 0 });
    rerender({ v: 1 });
    expect(result.current.riseKey).toBe(0);
    seen.length = 0;
    rerender({ v: 2 });
    // The committed render that shows 2 already has the new key (no effect, no second commit).
    expect(result.current).toEqual({ riseKey: 1, delta: 1 });
    expect(seen.at(-1)).toBe(1);
  });

  it("ignores drops and a value going back to loading", () => {
    const { result, rerender } = renderHook(({ v }: { v: number | undefined }) => useRise(v), { initialProps: { v: 5 as number | undefined } });
    rerender({ v: 3 });
    expect(result.current.riseKey).toBe(0);
    rerender({ v: undefined });
    rerender({ v: 4 });
    expect(result.current).toEqual({ riseKey: 1, delta: 1 });
  });
});

describe("Transient", () => {
  it("shows its children for `ms` after each new trigger", () => {
    vi.useFakeTimers();
    try {
      const { rerender } = render(<Transient trigger={0} ms={1000}>hi</Transient>);
      expect(screen.queryByText("hi")).toBeNull();
      rerender(<Transient trigger={1} ms={1000}>hi</Transient>);
      expect(screen.getByText("hi")).toBeTruthy();
      act(() => vi.advanceTimersByTime(600));
      rerender(<Transient trigger={2} ms={1000}>hi</Transient>);
      act(() => vi.advanceTimersByTime(600));
      expect(screen.getByText("hi")).toBeTruthy(); // the new trigger restarted the timer
      act(() => vi.advanceTimersByTime(500));
      expect(screen.queryByText("hi")).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });
});
