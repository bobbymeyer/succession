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

test("a new player's first game is the kind deal, unless they choose a seed", async ({ page }) => {
  await page.goto("./");
  await page.getByTestId("deal").waitFor({ timeout: 90_000 });
  await expect(page.getByTestId("first-deal")).toBeVisible();
  await page.fill("input[placeholder=random]", "7");
  await expect(page.getByTestId("first-deal")).toBeHidden();
  await page.fill("input[placeholder=random]", "");
  await page.getByTestId("deal").click();
  // You move first, with House Rising: Mitreas.
  await expect(page.getByTestId("briefing").locator("h2")).toHaveText("House Rising: Mitreas");
  await expect(page.getByTestId("briefing")).toContainText("You move first.");
});

test("an event stops play and says what it did", async ({ page }) => {
  // Seed 18: a bot draws Caravan before your first turn, and it plays at once.
  const errors: string[] = [];
  await start(page, errors, 18);
  await page.getByTestId("begin").click();
  const event = page.getByTestId("event");
  await expect(event).toBeVisible({ timeout: 30_000 });
  await expect(event.locator("h2")).toHaveText("Caravan");
  await expect(event).toContainText("drew it");
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

test("an event that asks you something is announced first", async ({ page }) => {
  // Seed 6: a bot draws Debasement of the Coinage before your first turn.
  const errors: string[] = [];
  await start(page, errors, 6);
  await page.getByTestId("begin").click();
  const announce = page.getByTestId("event-announce");
  await expect(announce).toBeVisible({ timeout: 30_000 });
  await expect(announce.locator("h2")).toHaveText("Debasement of the Coinage");
  await expect(announce).toContainText("drew it");
  await expect(announce).toContainText("Choose what to discard.");
  // It goes by itself, and the question is waiting behind it.
  await expect(announce).toBeHidden({ timeout: 6_000 });
  await expect(page.locator(".prompt")).toContainText("every player discards, all at once");
  await page.locator(".mine .card.live > button.face").first().click();
  await page.getByTestId("offer").first().click();
  // Then the whole event, resolved together.
  await expect(page.getByTestId("event")).toBeVisible();
  await expect(page.getByTestId("event").locator(".event-effects li")).toHaveCount(4);
  expect(errors).toEqual([]);
});

test("a hand over the limit is trimmed as your turn ends", async ({ page }) => {
  // Seed 1683: taking the first move each time, your hand passes 7 on the
  // sixteenth decision.
  const errors: string[] = [];
  await start(page, errors, 1683);
  for (let i = 0; i < 15; i++) await playFromList(page);
  await settle(page);
  await expect(page.locator(".prompt")).toContainText("Your hand is over the limit of 7");
  expect(await page.locator(".mine .card").count()).toBeGreaterThan(7);
  await playFromList(page);
  await settle(page);
  await page.mouse.move(0, 0); // no card preview over the tabs
  await page.getByRole("tab", { name: "Log" }).click();
  await expect(page.getByRole("list", { name: "Game log" })).toContainText("You discard");
  await expect(page.getByRole("list", { name: "Game log" })).toContainText("to the hand limit");
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
  // Tall enough that the whole hand and the board are on screen to drag across.
  await page.setViewportSize({ width: 1280, height: 1000 });
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
    // On the table: in the outer circle, or already moved into a seat by
    // the time the bots have played.
    await expect(page.locator(`section.outer [data-uid="${uid}"], section.court [data-uid="${uid}"]`)).toBeVisible();
    expect(errors).toEqual([]);
    return;
  }
  throw new Error("no courtier in the opening hand to drag");
});

test("a card dragged onto the discard pile is discarded and replaced", async ({ page }) => {
  const errors: string[] = [];
  // Tall enough that the whole hand and the board are on screen to drag across.
  await page.setViewportSize({ width: 1280, height: 1000 });
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

test("the rules open from the setup screen and from the table", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("./");
  await page.getByTestId("show-rules").click({ timeout: 90_000 });
  const rules = page.getByTestId("rules");
  await expect(rules).toBeVisible();
  // The agendas and events are the engine's own.
  await expect(rules).toContainText("1 more waiting in the outer circle");
  await expect(rules).toContainText("7 of 7 seats filled");
  await expect(rules).toContainText("Poisoning at the Feast");
  await expect(rules).not.toContainText("Plague");
  await page.keyboard.press("Escape");
  await expect(rules).toBeHidden();

  await page.getByTestId("deal").click();
  await settle(page);
  await page.getByTestId("show-rules").click();
  await expect(rules).toBeVisible();
  await rules.getByRole("button", { name: "Close the rules" }).click();
  await expect(rules).toBeHidden();
  expect(errors).toEqual([]);
});

test("the tutorial teaches a short game and ends in a win", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem("succession.speed", "Instant"));
  await page.goto("./");
  await page.getByTestId("tutorial").click({ timeout: 90_000 });
  await page.getByTestId("begin").click();
  // The first draw is a Caravan, and it plays at once.
  await expect(page.getByTestId("event").locator("h2")).toHaveText("Caravan");
  await page.getByTestId("event-continue").click();
  const coach = page.getByTestId("coach");
  await expect(coach).toContainText("An event, and a threat");
  // Only the lesson's moves are on offer: Apostasy on a seated Old Gods courtier.
  await page.locator(".all-moves summary").click();
  await expect(page.getByTestId("move-option")).toHaveCount(3);
  await expect(page.getByTestId("move-option").first()).toContainText("Apostasy");
  await page.getByTestId("move-option").first().click();
  await settle(page);
  await expect(coach).toContainText("Thwarted");
  await playFromList(page);
  await settle(page);
  await expect(coach).toContainText("Take the seat");
  await playFromList(page);
  await expect(page.getByTestId("game-over")).toContainText("You win");
  await expect(coach).toContainText("The court is yours");
  // Not kept among your finished games.
  await page.getByRole("button", { name: "New game" }).click();
  await expect(page.getByText(/Your games/)).toHaveCount(0);
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
