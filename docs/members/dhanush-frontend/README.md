# Dhanush Kumar S — Frontend Developer

> **Member 1** — Frontend track: everything the user sees and the Electron shell around it.

## Role

Build the ASCEND desktop app's face: a fast, keyboard-first Windows app with the three
rings, the anatomical muscle map, the workout logger, the meal-scan review and the coach
chat — and the secure Electron shell that hosts it.

## Primary responsibilities

- Electron main + preload: secure window defaults, IPC bridge (`window.ascend`), sidecar
  supervisor (`apps/desktop/electron/sidecar.ts`), Windows title bar, tray, toasts
- Design system: Tailwind tokens + shadcn/ui components, dark theme (light in v1.1), motion rules
- Screens: onboarding, dashboard (rings, quest card, coach notice), logger, history, diet
  + scan review, coach chat, progress, quests & rank, settings, diagnostics
- **Muscle map:** 19-region front/back SVG from MIT paths, heat colours + hatching,
  tooltip, keyboard navigation, drill-down (1 D → 30 D)
- Empty / loading / error states on every data view; accessibility (keyboard, reduce motion)
- UI tests (Vitest + Testing Library) and Playwright journeys with Gokul

## Repo areas owned

- `apps/desktop/` (all), `packages/shared/src/ipc.ts`
- `docs/contracts/ipc-contract.md`
- `docs/members/dhanush-frontend/` (this folder)

## Contracts I consume

| Contract | Provided by | Available |
|---|---|---|
| OpenAPI per module + Prism mock | Jegatheesan | Phase 0 (core), Phase 1–2 (rest) |
| SSE event names | Jegatheesan | Phase 1 |
| Formula outputs (status colours, readiness) | Jegatheesan (from Navin's specs) | Phase 1 |
| Installer / updater hooks | Gokul | Phase 0 / 3 |

## Contracts I provide

| Contract | Consumers | Available |
|---|---|---|
| IPC contract (`window.ascend`, channels) | Navin (review), Gokul (E2E) | Phase 0 |
| Sidecar launch protocol (port, token on stdin, data dir, ready) | Jegatheesan, Gokul | Phase 0 (exists in v0.1) |
| Design tokens + component list | everyone (screenshots, docs) | Phase 1 |

> Until each API lands I build against the Prism mock — my track never blocks
> ([phases.md §4](../../planning/phases.md#4-non-blocking-work-and-handoffs)).

## My commitments

- Every screen ships with its empty, loading and error state.
- No colour is the only signal (hatching, labels, icons).
- The renderer never gets Node, the token or the port.
- I can explain the supervisor state machine and the IPC security model in an interview.
