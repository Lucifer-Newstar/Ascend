/**
 * Browser dev mode (no Electron): the Vite dev and preview servers forward /api/* to the
 * sidecar. The renderer then talks to its own origin, the sidecar sends no CORS headers
 * at all, and a different project served on localhost:5173 can no longer read the dev
 * database with the static "dev" token (review L22).
 */
export const SIDECAR_PROXY_PREFIX = "/api";

export function sidecarProxy(target = process.env.ASCEND_SIDECAR_PROXY ?? "http://127.0.0.1:8765") {
  return {
    [SIDECAR_PROXY_PREFIX]: {
      target,
      rewrite: (path: string) => path.slice(SIDECAR_PROXY_PREFIX.length) || "/",
      // The sidecar only answers Host 127.0.0.1/localhost (DNS-rebinding guard); in
      // Docker the target is the "sidecar" service, so name the host explicitly.
      headers: { host: "127.0.0.1" },
    },
  };
}
