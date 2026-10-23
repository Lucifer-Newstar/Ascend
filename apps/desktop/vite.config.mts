import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

import pkg from "./package.json" with { type: "json" };
import { devCsp } from "./src/lib/csp";
import { sidecarProxy } from "./src/lib/dev-proxy";

// Renderer build. `base: "./"` makes the built index.html load assets with
// relative paths, which is what Electron needs when it opens file://.../index.html.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss(), devCsp()],
  // One version source: apps/desktop/package.json (bumped with the sidecar's pyproject).
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  server: { port: 5173, strictPort: true, proxy: sidecarProxy() },
  preview: { proxy: sidecarProxy() },
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 900 },
  test: {
    setupFiles: ["src/test/setup.ts"],
    // Windows CI runners render jsdom pages several times slower than Linux: the big
    // page tests (Dashboard, AddExercise) passed in about 0.9 s locally and hit the 5 s
    // default there. A longer limit on CI only; locally a stuck test still fails fast.
    testTimeout: process.env.CI ? 30_000 : 10_000,
    hookTimeout: process.env.CI ? 30_000 : 10_000,
    // Pure logic tests run in node; component tests (*.test.tsx) get a DOM from jsdom.
    // (Vitest 3+ dropped environmentMatchGlobs; projects are the replacement.)
    projects: [
      { extends: true, test: { name: "logic", environment: "node", include: ["src/**/*.test.ts", "electron/**/*.test.ts"] } },
      { extends: true, test: { name: "dom", environment: "jsdom", include: ["src/**/*.test.tsx"] } },
    ],
  },
});
