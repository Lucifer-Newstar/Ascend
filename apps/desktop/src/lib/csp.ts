/**
 * Content-Security-Policy helpers for index.html.
 *
 * The committed index.html carries the production policy, `connect-src 'self'`: inside
 * Electron the renderer talks to the sidecar over IPC only, so it needs no network
 * origin, and an injected script couldn't reach Ollama or any other localhost service.
 * Only the Vite dev server (`vite`, `npm run dev`) widens connect-src, for its HMR
 * websocket and for the browser-only mode that calls the sidecar on 127.0.0.1:8765.
 */
import type { Plugin } from "vite";

export const DEV_CONNECT_SOURCES = ["http://127.0.0.1:*", "http://localhost:*", "ws://127.0.0.1:*", "ws://localhost:*"];

/** Add `sources` to the connect-src directive of every CSP meta tag in `html`. */
export function widenConnectSrc(html: string, sources: string[] = DEV_CONNECT_SOURCES): string {
  return html.replace(/(content="[^"]*connect-src\s+)([^;"]*)/g, (_m, head: string, list: string) => `${head}${[list.trim(), ...sources].join(" ")}`);
}

/** Vite plugin: the dev-only connect-src sources. `apply: "serve"` keeps them out of builds. */
export function devCsp(): Plugin {
  return { name: "ascend-dev-csp", apply: "serve", transformIndexHtml: (html) => widenConnectSrc(html) };
}
