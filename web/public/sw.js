// Court of Succession, offline.
//
// Once the game has been opened, everything it needs is kept here: the page,
// its scripts, Pyodide, the rules engine and the card art. With no network it
// plays from this cache; with one, it stays current:
//
//   the page, engine.zip, the card manifest   network first (they change
//                                            without changing their names)
//   assets/ (Vite's hashed files), and        cache first (a new build has
//   pyodide/<version>/                        new names; an upgrade, a new
//                                            version folder)
//   everything else (cards, art, icons)      from the cache at once, refreshed
//                                            behind it for the next visit
//
// The page asks for the rest to be fetched ahead ("warm"), so a first visit
// that never opened, say, the inspector still has every card offline.

const CACHE = "succession-v1";
const scope = new URL(self.registration.scope);

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      for (const key of await caches.keys()) {
        if (key.startsWith("succession-") && key !== CACHE) await caches.delete(key);
      }
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "warm") event.waitUntil(warm(event.data.urls));
});

async function warm(urls) {
  const cache = await caches.open(CACHE);
  // An upgraded Pyodide leaves the old version's 13 MB behind: drop it.
  const pyodide = urls.find((url) => url.includes("/pyodide/"));
  if (pyodide) {
    const current = pyodide.slice(0, pyodide.lastIndexOf("/") + 1);
    for (const request of await cache.keys()) {
      if (request.url.startsWith(scope.href + "pyodide/") && !request.url.startsWith(current)) await cache.delete(request);
    }
  }
  for (const url of urls) {
    if (!url.startsWith(scope.href) || (await cache.match(url))) continue;
    try {
      const response = await fetch(url);
      if (response.ok) await cache.put(url, response);
    } catch {
      // offline, or gone: it is fetched again next time
    }
  }
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || !request.url.startsWith(scope.href)) return;
  const path = new URL(request.url).pathname.slice(scope.pathname.length);

  if (request.mode === "navigate" || path === "" || path === "index.html") {
    event.respondWith(networkFirst(request, scope.href));
  } else if (path === "engine.zip" || path.endsWith("manifest.json") || path === "manifest.webmanifest" || path === "sw.js") {
    event.respondWith(networkFirst(request));
  } else if (path.startsWith("assets/") || path.startsWith("pyodide/")) {
    event.respondWith(cacheFirst(request));
  } else {
    event.respondWith(staleWhileRevalidate(event, request));
  }
});

/** The network, keeping a copy; the copy when there is no network. */
async function networkFirst(request, key = request.url) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) await cache.put(key, response.clone());
    return response;
  } catch (error) {
    const kept = (await cache.match(key)) ?? (await cache.match(request, { ignoreSearch: true }));
    if (kept) return kept;
    throw error;
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const kept = await cache.match(request);
  if (kept) return kept;
  const response = await fetch(request);
  if (response.ok) await cache.put(request, response.clone());
  return response;
}

async function staleWhileRevalidate(event, request) {
  const cache = await caches.open(CACHE);
  const kept = await cache.match(request);
  const fresh = fetch(request)
    .then(async (response) => {
      if (response.ok) await cache.put(request, response.clone());
      return response;
    })
    .catch(() => undefined);
  if (kept) {
    event.waitUntil(fresh);
    return kept;
  }
  return (await fresh) ?? Response.error();
}
