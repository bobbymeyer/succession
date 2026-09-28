import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";

// Pyodide lives under its version (scripts/assets.mjs), which the page and
// the worker need to find it.
const pyodide = JSON.parse(readFileSync(new URL("./node_modules/pyodide/package.json", import.meta.url), "utf8"));

export default defineConfig({
  plugins: [react()],
  // Relative URLs throughout, so the built site works at any path: GitHub
  // Pages under /succession/, or copied into another site and iframed.
  base: "./",
  worker: { format: "es" },
  define: { __PYODIDE_VERSION__: JSON.stringify(pyodide.version) },
});
