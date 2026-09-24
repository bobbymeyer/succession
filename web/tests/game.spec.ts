// Whole games in a real browser: Pyodide boots, the engine deals, and a
// player gets from the first move to the end.
import type { Page } from "@playwright/test";
import { expect, playFromList, random, settle, test } from "./helpers";

async function start(page: Page, errors: string[], seed?: number) {
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  await page.addInitScript(() => localStorage.setItem("succession.speed", "Instant"));
  await page.goto("./");
  await page.getByTestId("deal").waitFor({ timeout: 90_000 }); // Pyodide boot
  if (seed !== undefined) await page.fill("input[placeholder=random]", String(seed));
  await page.getByTestId("deal").click();
}

test("a round opens on your agenda and waits for you to begin", async ({ page }) => {
  const errors: string[] = [];
  await start(page, errors, 3);
  const briefing = page.getByTestId("briefing");
  await expect(briefing).toBeVisible();
  const mine = await briefing.locator("h2").innerText();
  // Nobody has moved: the bots wait until you begin.
  await page.waitForTimeout(1500);
  await expect(page.locator(".status .turn")).toHaveText("Turn 0");
  await page.getByTestId("begin").click();
  await expect(briefing).toBeHidden();
  await settle(page);
  await expect(page.getByTestId("agenda-tracker").locator("strong").first()).toHaveText(mine);
  expect(errors).toEqual([]);
});

test("an event stops play and says what it did", async ({ page }) => {
  // Seed 15: a bot's Treasure Fleet before your first turn.
  const errors: string[] = [];
  await start(page, errors, 15);
  await page.getByTestId("begin").click();
  const event = page.getByTestId("event");
  await expect(event).toBeVisible({ timeout: 30_000 });
  await expect(event.locator("h2")).toHaveText("Treasure Fleet");
  await expect(event.locator(".event-effects li")).toHaveCount(4);
  await expect(event.locator(".event-effects")).toContainText("You draw");
  // Nothing moves on behind it until it has been read.
  const turn = await page.locator(".status .turn").innerText();
  await page.waitForTimeout(800);
  await expect(page.locator(".status .turn")).toHaveText(turn);
  await page.getByTestId("event-continue").click();
  await expect(event).toBeHidden();
  await settle(page);
  expect(errors).toEqual([]);
});

test("a game played from the move list", async ({ page }) => {
  const errors: string[] = [];
  await start(page, errors);
  for (let i = 0; i < 400 && (await playFromList(page, random)); i++);
  await expect(page.getByTestId("game-over")).toBeVisible();
  expect(errors).toEqual([]);
});

test("a game played by clicking the board", async ({ page }) => {
  const errors: string[] = [];
  await start(page, errors);
  // Anything lit up is a real choice. Prefer the buttons over a picked-up
  // card, then anything lit that is not already picked up.
  const offers = page.getByTestId("offer");
  const lit = page.locator(
    ".card.live:not(.selected) > button.face, .seat.live button.chair:not(:disabled), .seat-take, .opponent.live",
  );
  const pickedUp = page.locator(".card.live.selected > button.face");
  for (let i = 0; i < 3000; i++) {
    await settle(page);
    if (await page.getByTestId("game-over").isVisible()) break;
    const buttons = await offers.all();
    if (buttons.length && Math.random() < 0.8) {
      await random(buttons).click();
      continue;
    }
    const choices = await lit.all();
    if (choices.length) await random(choices).click();
    else await pickedUp.first().click(); // put it down and start again
  }
  await expect(page.getByTestId("game-over")).toBeVisible();
  expect(errors).toEqual([]);
});

test("a card is picked up by clicking it and put down by clicking it again", async ({ page }) => {
  const errors: string[] = [];
  await start(page, errors, 4);
  await settle(page);
  const card = page.locator(".mine .card.live").first();
  await card.locator("> button.face").click();
  await expect(card).toHaveClass(/selected/);
  await expect(card.getByTestId("offer").first()).toBeVisible();
  await card.locator("> button.face").click();
  await expect(card).not.toHaveClass(/selected/);
  await expect(page.getByTestId("offer")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("a courtier dragged from the hand onto the outer circle is played there", async ({ page }) => {
  const errors: string[] = [];
  await start(page, errors, 4);
  await settle(page);
  const outer = page.locator("section.outer");
  for (const card of await page.locator(".mine .card.grab").all()) {
    const uid = await card.getAttribute("data-uid");
    const from = (await card.boundingBox())!;
    await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
    await page.mouse.down();
    await page.mouse.move(from.x + from.width / 2 + 20, from.y - 20, { steps: 4 });
    if (!(await outer.evaluate((el) => el.classList.contains("drop-live")))) {
      await page.mouse.up(); // not a courtier: dropped nowhere, nothing happens
      continue;
    }
    const to = (await outer.boundingBox())!;
    await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2, { steps: 8 });
    await page.mouse.up();
    await expect(page.locator(`section.outer [data-uid="${uid}"]`)).toBeVisible();
    expect(errors).toEqual([]);
    return;
  }
  throw new Error("no courtier in the opening hand to drag");
});

test("a card dragged onto the discard pile is discarded and replaced", async ({ page }) => {
  const errors: string[] = [];
  await start(page, errors, 4);
  await settle(page);
  const card = page.locator(".mine .card.grab").first();
  const uid = await card.getAttribute("data-uid");
  const handSize = await page.locator(".mine .card").count();
  const from = (await card.boundingBox())!;
  const pile = (await page.locator(".discard-pile").boundingBox())!;
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(pile.x + pile.width / 2, pile.y + pile.height / 2, { steps: 10 });
  await expect(page.locator(".discard-pile")).toHaveClass(/drop-live/);
  await page.mouse.up();
  await expect(page.locator(`.discard-pile [data-uid="${uid}"], .mine [data-uid="${uid}"]`)).toHaveCount(1);
  await expect(page.locator(`.mine [data-uid="${uid}"]`)).toHaveCount(0);
  await settle(page);
  expect(await page.locator(".mine .card").count()).toBeGreaterThanOrEqual(handSize);
  expect(errors).toEqual([]);
});

test("the end of a game: the reveal, export, play again", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  // Fast rather than Instant, so every move is animated on the way.
  await page.addInitScript(() => localStorage.setItem("succession.speed", "Fast"));
  await page.goto("./");
  await page.getByTestId("deal").click({ timeout: 90_000 });

  const dialog = page.getByTestId("game-over");
  for (let i = 0; i < 400 && (await playFromList(page)); i++);

  // No window in the way: the winner turns their agenda over in the rail,
  // and the courtiers who won it light up on the board.
  await expect(dialog).toBeVisible();
  await expect(page.locator("dialog[open]")).toHaveCount(0);
  const revealed = await dialog.getByTestId("revealed-agenda").count();
  if (revealed) await expect(page.locator(".seat.won-by")).not.toHaveCount(0);
  else await expect(dialog).toContainText("Chaos grips the empire");

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
  await settle(page);
  await expect(page.locator(".opponent")).toHaveCount(3);

  // And the game is remembered on the setup screen.
  await page.getByRole("button", { name: "New game" }).click();
  await expect(page.getByText("Your games (1 finished in this browser)")).toBeVisible();
  expect(errors).toEqual([]);
});

test("every screen credits bobbymeyer.com", async ({ page }) => {
  await page.goto("./");
  const credit = page.getByRole("link", { name: "designed by bobbymeyer." });
  await expect(credit).toBeVisible({ timeout: 90_000 });
  await expect(credit).toHaveAttribute("href", "https://bobbymeyer.com");
  await expect(credit).toHaveAttribute("target", "_top");
  await page.getByTestId("deal").click();
  await settle(page);
  await expect(page.getByRole("link", { name: "designed by bobbymeyer." })).toBeVisible();
});
