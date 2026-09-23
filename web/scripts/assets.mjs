// Stage what the game loads at runtime into public/: Pyodide itself, copied out
// of node_modules so the site hosts its own copy (no CDN, works offline and
// embedded), and the rules engine zipped from ../succession.
import { copyFileSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const from = join(web, "node_modules", "pyodide");
const to = join(web, "public", "pyodide");

// Only what loading the interpreter and the standard library needs.
const PYODIDE = [
  "pyodide.mjs",
  "pyodide.asm.mjs",
  "pyodide.asm.wasm",
  "python_stdlib.zip",
  "pyodide-lock.json",
];
mkdirSync(to, { recursive: true });
for (const name of PYODIDE) copyFileSync(join(from, name), join(to, name));
console.log(`copied ${PYODIDE.length} Pyodide files to public/pyodide`);

const python = process.env.PYTHON ?? "python3";
const zip = spawnSync(python, [join(web, "..", "tools", "webbundle.py"), join(web, "public", "engine.zip")], {
  stdio: "inherit",
});
if (zip.status !== 0) process.exit(zip.status ?? 1);
