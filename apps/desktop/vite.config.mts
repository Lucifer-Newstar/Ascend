import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

import pkg from "./package.json" with { type: "json" };

// Renderer build. `base: "./"` makes the built index.html load assets with
// relative paths, which is what Electron needs when it opens file://.../index.html.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  // One version source: apps/desktop/package.json (bumped with the sidecar's pyproject).
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  server: { port: 5173, strictPort: true },
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 900 },
  test: {
    setupFiles: ["src/test/setup.ts"],
    // Pure logic tests run in node; component tests (*.test.tsx) get a DOM from jsdom.
    // (Vitest 3+ dropped environmentMatchGlobs; projects are the replacement.)
    projects: [
      { extends: true, test: { name: "logic", environment: "node", include: ["src/**/*.test.ts", "electron/**/*.test.ts"] } },
      { extends: true, test: { name: "dom", environment: "jsdom", include: ["src/**/*.test.tsx"] } },
    ],
  },
});
