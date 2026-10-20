/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SIDECAR_URL?: string;
  readonly VITE_SIDECAR_TOKEN?: string;
}

/** apps/desktop/package.json version, injected by vite.config.mts. */
declare const __APP_VERSION__: string;
