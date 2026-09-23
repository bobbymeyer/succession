// Runs the Python rules engine in Pyodide, off the page's main thread. Bot
// turns take milliseconds, but loading the interpreter does not, and nothing
// here should ever stall the page.

import type { PyodideAPI } from "pyodide";
import type { Request, WorkerMessage } from "./protocol";

type PyTable = {
  new_game(request: string): string;
  answer(choice: number): string;
  load(record: string): string;
  export(records: string): string;
};

let table: PyTable | null = null;
let ready: Promise<void> | null = null;

function post(message: WorkerMessage) {
  self.postMessage(message);
}

async function boot(base: string) {
  // Pyodide is hosted with the site (public/pyodide), so the game works
  // offline and inside an embedding page without a CDN.
  const indexURL = new URL("pyodide/", base).href;
  const { loadPyodide } = (await import(/* @vite-ignore */ `${indexURL}pyodide.mjs`)) as typeof import("pyodide");
  const [pyodide, engine] = await Promise.all([
    loadPyodide({ indexURL }) as Promise<PyodideAPI>,
    fetch(new URL("engine.zip", base)).then((r) => {
      if (!r.ok) throw new Error(`engine.zip: HTTP ${r.status}`);
      return r.arrayBuffer();
    }),
  ]);
  pyodide.unpackArchive(engine, "zip");
  table = pyodide.runPython("from succession.webapi import Table\nTable()") as PyTable;
  const options = JSON.parse(pyodide.runPython("from succession.webapi import options\noptions()") as string);
  const python = pyodide.runPython("import sys\nsys.version.split()[0]") as string;
  post({ type: "ready", options, python });
}

// A Python exception arrives as a PythonError whose message is the whole
// traceback; the last line is the part worth showing.
function describe(error: unknown): string {
  const text = error instanceof Error ? error.message : String(error);
  const lines = text.trim().split("\n");
  return lines[lines.length - 1];
}

self.onmessage = async (event: MessageEvent) => {
  const data = event.data as { type: "boot"; base: string } | (Request & { id: number });
  if (data.type === "boot") {
    ready = boot(data.base).catch((error) => post({ type: "error", id: null, message: describe(error) }));
    return;
  }
  await ready;
  if (!table) return; // boot failed and already said so
  try {
    if (data.type === "export") {
      post({ type: "text", id: data.id, text: table.export(JSON.stringify(data.records)) });
      return;
    }
    let json: string;
    if (data.type === "new") json = table.new_game(JSON.stringify({ players: data.players, seed: data.seed }));
    else if (data.type === "answer") json = table.answer(data.choice);
    else json = table.load(JSON.stringify(data.record));
    post({ type: "updates", id: data.id, updates: JSON.parse(json) });
  } catch (error) {
    post({ type: "error", id: data.id, message: describe(error) });
  }
};
