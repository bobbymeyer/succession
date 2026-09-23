// Whole games in a real browser: Pyodide boots, the engine deals, and a
// player gets from the first move to the end.
import { expect, test, type Page } from "@playwright/test";

async function start(page: Page, errors: string[]) {
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  await page.addInitScript(() => localStorage.setItem("succession.speed", "Instant"));
  await page.goto("./");
  await page.getByTestId("deal").click({ timeout: 90_000 }); // Pyodide boot
}

// Wait for the page to settle on something a player can act on.
async function settled(page: Page) {
  const ready = page.locator("[data-testid=game-over], [data-testid=pick-option], [data-testid=confirm], .all-moves");
  await ready.first().waitFor();
}

function pick<T>(items: T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}

test("a game played from the move list", async ({ page }) => {
  const errors: string[] = [];
  await start(page, errors);
  for (let i = 0; i < 400; i++) {
    await settled(page);
    if (await page.getByTestId("game-over").isVisible()) break;
    const picks = await page.getByTestId("pick-option").all();
    if (picks.length) {
      await pick(picks).click();
    } else {
      await page.locator(".all-moves summary").click();
      await pick(await page.getByTestId("move-option").all()).click();
    }
    await page.getByTestId("confirm").click();
  }
  await expect(page.getByTestId("game-over")).toBeVisible();
  expect(errors).toEqual([]);
});

test("a game played by clicking the board", async ({ page }) => {
  const errors: string[] = [];
  await start(page, errors);
  // Anything lit up is a real choice; keep clicking until a move is built.
  const choices = page.locator(
    ".card.live > button.face, button.chair:not(:disabled), .seat-take, .prompt .buttons button:not(.primary):not(:text-is('Back')), [data-testid=pick-option]",
  );
  for (let i = 0; i < 2000; i++) {
    await settled(page);
    if (await page.getByTestId("game-over").isVisible()) break;
    const confirm = page.getByTestId("confirm");
    if (await confirm.isVisible()) {
      await confirm.click();
      continue;
    }
    const live = await choices.all();
    expect(live.length, "something must be clickable").toBeGreaterThan(0);
    await pick(live).click();
  }
  await expect(page.getByTestId("game-over")).toBeVisible();
  expect(errors).toEqual([]);
});

test("the end of a game: results, export, play again", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  // Fast rather than Instant, so every move is animated on the way.
  await page.addInitScript(() => localStorage.setItem("succession.speed", "Fast"));
  await page.goto("./");
  await page.getByTestId("deal").click({ timeout: 90_000 });

  const dialog = page.getByTestId("game-over-dialog");
  for (let i = 0; i < 400; i++) {
    await page.locator("[data-testid=game-over], [data-testid=pick-option], .all-moves").first().waitFor({ timeout: 60_000 });
    if (await page.getByTestId("game-over").isVisible()) break;
    const picks = await page.getByTestId("pick-option").all();
    if (picks.length) {
      await picks[0].click();
    } else {
      await page.locator(".all-moves summary").click();
      await page.getByTestId("move-option").first().click();
    }
    await page.getByTestId("confirm").click();
  }

  // The results come up on their own, with every agenda turned over.
  await expect(dialog).toBeVisible();
  await expect(dialog.locator(".standings li")).toHaveCount(4);
  await expect(dialog.locator(".standings li.won")).not.toHaveCount(0);

  // The finished game downloads as a log `analyze` reads.
  await dialog.getByText("Save this game").click();
  const [file] = await Promise.all([page.waitForEvent("download"), dialog.getByTestId("export").click()]);
  const text = await (await file.createReadStream()).toArray();
  const csv = Buffer.concat(text).toString();
  expect(csv.split("\n")[0].startsWith("game_id,seed,turns")).toBe(true);
  expect(csv.trim().split("\n")).toHaveLength(2);
  expect(csv).toContain("human");

  // Play again deals a fresh game at the same table.
  await dialog.getByTestId("play-again").click();
  await expect(dialog).toBeHidden();
  await page.locator("[data-testid=pick-option], .all-moves, [data-testid=game-over]").first().waitFor();
  await expect(page.locator(".opponent")).toHaveCount(3);

  // And the game is remembered on the setup screen.
  await page.getByRole("button", { name: "New game" }).click();
  await expect(page.getByText("Your games (1 finished in this browser)")).toBeVisible();
  expect(errors).toEqual([]);
});
