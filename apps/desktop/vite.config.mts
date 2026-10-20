import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Renderer build. `base: "./"` makes the built index.html load assets with
// relative paths, which is what Electron needs when it opens file://.../index.html.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  server: { port: 5173, strictPort: true },
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 900 },
  test: {
    // Pure logic tests run in node; component tests (*.test.tsx) get a DOM from jsdom.
    environment: "node",
    environmentMatchGlobs: [["src/**/*.test.tsx", "jsdom"]],
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["src/test/setup.ts"],
  },
} as import("vite").UserConfig & { test?: unknown });
