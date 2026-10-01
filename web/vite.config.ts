import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";

// Pyodide lives under its version (scripts/assets.mjs), which the page and
// the worker need to find it.
const pyodide = JSON.parse(readFileSync(new URL("./node_modules/pyodide/package.json", import.meta.url), "utf8"));

// Which build this is, shown at the foot of the page and sent with feedback,
// so a report names the rules it was played under. Outside a git checkout it
// is "dev".
function build(): { commit: string; date: string } {
  try {
    const [commit, date] = execSync("git log -1 --format=%h%n%cs", { encoding: "utf8" }).trim().split("\n");
    return { commit, date };
  } catch {
    return { commit: "dev", date: "" };
  }
}

export default defineConfig({
  plugins: [react()],
  // Relative URLs throughout, so the built site works at any path: GitHub
  // Pages under /succession/, or copied into another site and iframed.
  base: "./",
  worker: { format: "es" },
  define: { __PYODIDE_VERSION__: JSON.stringify(pyodide.version), __BUILD__: JSON.stringify(build()) },
});
