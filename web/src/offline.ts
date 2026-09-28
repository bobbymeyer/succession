// Offline play: register the service worker (public/sw.js) and, once the game
// has loaded, have it fetch ahead whatever a game can still ask for.

/** The Pyodide files scripts/assets.mjs hosts; the worker loads them all. */
const PYODIDE = ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"];

export function registerOffline() {
  if (!import.meta.env.PROD || !("serviceWorker" in navigator)) return;
  // Inside another site's frame the browser may refuse; the game plays anyway.
  navigator.serviceWorker.register("./sw.js").catch(() => {});
}

/** Everything a game needs, fetched into the offline cache if it is not there yet. */
export function warmOffline(extra: string[]) {
  if (!import.meta.env.PROD || !("serviceWorker" in navigator)) return;
  const here = new URL("./", document.baseURI);
  const at = (path: string) => new URL(path, here).href;
  const loaded = performance
    .getEntriesByType("resource")
    .map((e) => e.name)
    .filter((u) => u.startsWith(here.href));
  const urls = [
    here.href,
    at("engine.zip"),
    at("manifest.webmanifest"),
    at("cards/manifest.json"),
    ...PYODIDE.map((f) => at(`pyodide/${__PYODIDE_VERSION__}/${f}`)),
    ...["eclipse", "outmaneuver", "promotion", "assassination", "emblem", "tyrant", "mob", "ruin"].map((n) => at(`intro/${n}.webp`)),
    ...loaded,
    ...extra,
  ];
  navigator.serviceWorker.ready
    .then((registration) => registration.active?.postMessage({ type: "warm", urls: [...new Set(urls)] }))
    .catch(() => {});
}
