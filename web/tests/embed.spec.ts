// The game inside another site's iframe, using the exact snippet in
// docs/EMBED.md. The parent page is served from a different origin, as
// bobbymeyer.com would be, so this is the cross-origin case: the worker,
// Pyodide, storage and downloads all have to work from inside the frame.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { playFromList } from "./helpers";

// Served by the second web server in playwright.config.ts: a different origin
// from the game's, and a real server -- Chrome will not let a page it cannot
// place on the local network frame a local one.
const PARENT = "http://localhost:4174/index.html";

function snippet(src: string): string {
  const guide = readFileSync(new URL("../../docs/EMBED.md", import.meta.url), "utf8");
  const html = /```html\n([\s\S]*?)```/.exec(guide)?.[1];
  if (!html) throw new Error("no iframe snippet in docs/EMBED.md");
  return html.replace("https://bobbymeyer.github.io/succession/", src);
}

test("a whole game inside another site's iframe", async ({ page, baseURL }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  await page.addInitScript(() => localStorage.setItem("succession.speed", "Instant"));
  const parent = new URL("../.embed-parent/", import.meta.url);
  mkdirSync(parent, { recursive: true });
  writeFileSync(
    new URL("index.html", parent),
    `<!doctype html><title>Parent</title><h1>Someone's site</h1>${snippet(baseURL!)}`,
  );
  await page.goto(PARENT);

  const frame = page.frameLocator("iframe");
  await frame.getByTestId("deal").click({ timeout: 90_000 });
  await expect(frame.getByText("Open in a new tab").first()).toBeVisible();
  await expect(frame.getByRole("button", { name: "Full screen" })).toBeVisible();

  for (let i = 0; i < 400 && (await playFromList(frame)); i++);

  const dialog = frame.getByTestId("game-over");
  await expect(dialog).toBeVisible();
  await dialog.getByText("Save this game").click();
  const [file] = await Promise.all([page.waitForEvent("download"), dialog.getByTestId("export").click()]);
  expect(file.suggestedFilename()).toBe("succession-games.csv");
  expect(errors).toEqual([]);
});
