# @ascend/shared

TypeScript types shared across the desktop app:

- `src/api.ts`: request/response types of the sidecar API (mirrors the Pydantic schemas).
- `src/ipc.ts`: the typed IPC contract: channel names (`IPC`) and the `window.ascend` bridge
  (`AscendBridge`) exposed by the preload script.

No runtime code beyond the `IPC` constant. `npm run typecheck -w packages/shared` checks it.

Planned: generate `api.ts` from the sidecar's `/openapi.json` with `openapi-typescript` and
fail CI when the generated file drifts.
