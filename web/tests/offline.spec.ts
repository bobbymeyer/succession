// Once visited, the game plays with no network at all: the service worker
// (public/sw.js) keeps the page, Pyodide, the engine and the art.
import { expect, playFromList, settle, test } from "./helpers";

test("once opened, the game plays offline", async ({ page, context }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem("succession.speed", "Instant"));
  await page.goto("./");
  await page.getByTestId("deal").waitFor({ timeout: 90_000 });

  // Wait for the cache to hold what a game needs.
  await expect
    .poll(
      () =>
        page.evaluate(async () => {
          const here = new URL("./", document.baseURI).href;
          const need = ["", "engine.zip", "cards/manifest.json", "cards/00-cardback.webp"];
          const found = await Promise.all(need.map((p) => caches.match(here + p)));
          const kept = await Promise.all((await caches.keys()).map(async (k) => (await caches.open(k)).keys()));
          const wasm = kept.flat().some((r) => r.url.endsWith("pyodide.asm.wasm"));
          return found.every(Boolean) && wasm;
        }),
      { timeout: 90_000 },
    )
    .toBe(true);

  await context.setOffline(true);
  await page.reload();
  await page.getByTestId("deal").click({ timeout: 90_000 });
  await settle(page);
  expect(await playFromList(page)).toBe(true);
  await settle(page);
  await expect(page.locator(".dock .mine .card, .board .mine .card").first()).toBeVisible();
  // The art came from the cache too.
  const drawn = await page.locator(".mine .card img").first().evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0);
  expect(drawn).toBe(true);
  expect(errors).toEqual([]);
});
