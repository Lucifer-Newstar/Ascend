# ADR-0001: Electron + React + TypeScript Desktop Shell

- **Status:** Proposed (to ratify at the Phase 0 kickoff)
- **Date:** 2026-10-20
- **Deciders:** Navin Jairam M (lead); ratified by the team at kickoff

## Context

ASCEND must be a Windows desktop app that works offline, with a dense, polished UI
(rings, an interactive SVG muscle map, charts, a streaming chat). The v2 mockups are
already real HTML/CSS. The team knows web technology better than native Windows
toolkits, and the frontend owner (Dhanush) used TypeScript/React in AegisDeploy. We
need native touches: Windows 11 title bar and snap layouts, tray, toasts, auto-update.

## Decision

Use **Electron** (current supported major) with **React 18+ and TypeScript (strict)**,
built with **Vite**; main and preload live in `apps/desktop/electron/`, the renderer in
`apps/desktop/src/`, shared types in `packages/shared/` (npm workspaces).

- UI: **Tailwind CSS** tokens + **shadcn/ui** (Radix primitives), **lucide** icons,
  **Recharts** for charts, the muscle map as React SVG components from MIT-licensed paths.
- State/data: **TanStack Query** for sidecar calls; small **Zustand** stores for UI state.
- Security defaults per [security-privacy.md §3](../security-privacy.md#3-electron-hardening-checklist).
- Windows integration: `titleBarOverlay`, `AppUserModelID`, tray, `Notification`.
- Tests: **Vitest** + Testing Library; **Playwright for Electron** for E2E.

## Consequences

### Positive

- HTML mockups become components with little rewriting.
- Largest ecosystem for charts, SVG and accessible components.
- Same language as the IPC contract types generated from OpenAPI.
- electron-builder/electron-updater give a mature Windows installer and updates.

### Negative / Trade-offs

- Bundle size (~100+ MB installed) and memory use (~150–300 MB, estimate) are higher than a native app.
- Electron security needs care; mitigated by sandbox, contextIsolation, fuses and an IPC allow-list.
- Two runtimes (Node + Python) to package; see ADR-0008.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Tauri (Rust + WebView2) | Smaller binaries, but Rust in main adds a third language; sidecar support exists but the team has no Rust experience. |
| WinUI 3 / .NET MAUI | Native look, but no web reuse of the mockups and C# is new to the team. |
| Flutter desktop | Good UI toolkit, but Dart is new and SVG/muscle-map interactivity is harder. |
| PyQt / PySide | One language with the backend, but dated look and harder to reach the mockup quality. |
