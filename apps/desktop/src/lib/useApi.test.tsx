import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { isOffline, useApi } from "./useApi";

class FakeApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
  }
}

describe("useApi", () => {
  it("loads, then keeps the last good data when a refresh fails", async () => {
    const fn = vi.fn().mockResolvedValueOnce({ n: 1 }).mockRejectedValueOnce(new FakeApiError(0, "Can't reach the local engine"));
    const { result } = renderHook(() => useApi(fn, []));
    await waitFor(() => expect(result.current.data).toEqual({ n: 1 }));
    expect(result.current.error).toBeNull();
    act(() => result.current.reload());
    await waitFor(() => expect(result.current.error).toBe("Can't reach the local engine"));
    expect(result.current.data).toEqual({ n: 1 });
    expect(result.current.status).toBe(0);
    expect(isOffline(result.current.status)).toBe(true);
  });

  it("clears the error after a successful retry", async () => {
    const fn = vi.fn().mockRejectedValueOnce(new FakeApiError(404, "not found")).mockResolvedValueOnce([1, 2]);
    const { result } = renderHook(() => useApi(fn, []));
    await waitFor(() => expect(result.current.status).toBe(404));
    expect(isOffline(result.current.status)).toBe(false);
    act(() => result.current.reload());
    await waitFor(() => expect(result.current.data).toEqual([1, 2]));
    expect(result.current.error).toBeNull();
    expect(result.current.status).toBeNull();
  });

  it("refetches when a dependency changes", async () => {
    const fn = vi.fn().mockResolvedValue("ok");
    const { rerender } = renderHook(({ k }) => useApi(fn, [k]), { initialProps: { k: 1 } });
    await waitFor(() => expect(fn).toHaveBeenCalledTimes(1));
    rerender({ k: 2 });
    await waitFor(() => expect(fn).toHaveBeenCalledTimes(2));
  });
});
