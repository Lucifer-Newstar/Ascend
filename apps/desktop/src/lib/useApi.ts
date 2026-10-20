import { useCallback, useEffect, useRef, useState } from "react";

export interface ApiState<T> {
  data: T | null;
  error: string | null;
  /** HTTP status of the last failure; 0 = the engine could not be reached. */
  status: number | null;
  loading: boolean;
  reload: () => void;
}

/** True when a failure means the local engine is down rather than a bad request. */
export const isOffline = (status: number | null): boolean => status === 0 || status === 503;

/**
 * Load data on mount (and when `deps` change). `reload()` refetches without clearing,
 * and a failed refresh keeps the last good data so screens can show it as stale.
 */
// Last good result per cacheKey, so a screen opened again (or the app reloaded within
// the session) paints its previous content at once and refreshes in the background.
const cache = new Map<string, unknown>();

/** Test helper: forget cached results. */
export function clearApiCache(): void {
  cache.clear();
}

export function useApi<T>(fn: () => Promise<T>, deps: unknown[] = [], opts: { cacheKey?: string } = {}): ApiState<T> {
  const { cacheKey } = opts;
  const [data, setData] = useState<T | null>(() => (cacheKey && cache.has(cacheKey) ? (cache.get(cacheKey) as T) : null));
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    fnRef
      .current()
      .then((d) => {
        if (cacheKey) cache.set(cacheKey, d);
        if (!alive) return;
        setData(d);
        setError(null);
        setStatus(null);
      })
      .catch((e: Error) => {
        if (!alive) return;
        setError(e.message);
        // ApiError carries the HTTP status (duck-typed so mocked clients work too).
        const code = (e as { status?: unknown }).status;
        setStatus(typeof code === "number" ? code : null);
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, ...deps]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, status, loading, reload };
}
