// The table on a phone held upright: one screen, the hand in a dock at the
// bottom, everything else a tap away.
import type { Page } from "@playwright/test";
import { expect, playFromList, random, settle, test } from "./helpers";

test.use({ viewport: { width: 390, height: 664 }, isMobile: true, hasTouch: true });

async function deal(page: Page, errors: string[], seed = "3") {
  page.on("pageerror", (e) => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem("succession.speed", "Instant"));
  await page.goto("./");
  await page.getByTestId("deal").waitFor({ timeout: 90_000 });
  await page.fill("input[placeholder=random]", seed);
  await page.getByTestId("deal").tap();
  await settle(page);
}

test("the table fits one screen, with the hand in the dock", async ({ page }) => {
  const errors: string[] = [];
  await deal(page, errors);
  // Nothing scrolls the page itself.
  const [scroll, height] = await page.evaluate(() => [document.documentElement.scrollHeight, window.innerHeight]);
  expect(scroll).toBeLessThanOrEqual(height);
  await expect(page.locator(".board .mine")).toHaveCount(0);
  const hand = page.locator(".dock .mine .card");
  await expect(hand.first()).toBeInViewport();
  await expect(page.locator(".seat").last()).toBeInViewport();
  await expect(page.getByText("Tap a card to pick it up, or hold one to read it.")).toBeVisible();

  // A card picked up offers what it can do in the dock, never over the
  // question, and can be put down again.
  await page.locator(".dock .mine .card.live > button.face").first().tap();
  await expect(page.locator(".dock-offers").getByTestId("offer").first()).toBeInViewport();
  await expect(page.locator(".popover")).toHaveCount(0);
  await page.getByTestId("put-down").tap();
  await expect(page.getByTestId("offer")).toHaveCount(0);
  await page.locator(".dock .mine .card.live > button.face").first().tap();
  await page.locator(".dock .mine .card.selected > button.face").tap();
  await expect(page.getByTestId("offer")).toHaveCount(0);
  // The strip is one line, clear of the menu.
  const strip = await page.locator(".opponents").boundingBox();
  const menu = await page.getByTestId("menu").boundingBox();
  expect(strip!.height).toBeLessThan(50);
  expect(strip!.x + strip!.width).toBeLessThanOrEqual(menu!.x);

  // The dock's tabs pull up the agenda, the log and the discard pile.
  await page.getByTestId("dock-agenda").tap();
  await expect(page.getByTestId("sheet").getByTestId("agenda-tracker")).toBeVisible();
  await page.getByTestId("dock-log").tap();
  await expect(page.getByTestId("sheet").getByRole("list", { name: "Game log" })).toBeVisible();
  await page.locator(".scrim").tap({ position: { x: 20, y: 60 } });
  await expect(page.getByTestId("sheet")).toHaveCount(0);

  // The menu holds the rules and a new game.
  await page.getByTestId("menu").tap();
  await page.getByTestId("show-rules").tap();
  await expect(page.getByTestId("rules")).toBeVisible();
  expect(errors).toEqual([]);
});

test("a whole game played on a phone", async ({ page }) => {
  const errors: string[] = [];
  await deal(page, errors, "");
  for (let i = 0; i < 400 && (await playFromList(page, random)); i++);
  const over = page.getByTestId("game-over");
  await expect(over).toBeVisible();
  await expect(over.getByTestId("play-again")).toBeInViewport();
  // Revealed agendas make the strip taller; the board makes room.
  const [inner, outer] = await page.locator(".opponents").evaluate((o) => [o.scrollHeight, o.clientHeight]);
  expect(inner).toBeLessThanOrEqual(outer + 1);
  expect(errors).toEqual([]);
});

test("the tutorial's coach folds away to give the board room", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem("succession.speed", "Instant"));
  await page.goto("./");
  await page.getByTestId("tutorial").tap({ timeout: 90_000 });
  await settle(page);
  const coach = page.getByTestId("coach");
  await expect(coach).toContainText("Four Old Gods seats");
  await coach.getByRole("button").tap();
  await expect(coach).not.toContainText("Four Old Gods seats");
  await expect(coach).toContainText("An event, and a threat");
  // The next step opens it again.
  await playFromList(page);
  await settle(page);
  await expect(coach).toContainText("Thwarted");
  await expect(coach).toContainText("Now build your own");
  expect(errors).toEqual([]);
});

// A finger, through the browser's own touch input: hold, move, lift.
async function finger(page: Page) {
  const cdp = await page.context().newCDPSession(page);
  const at = (x: number, y: number) => [{ x, y, id: 1 }];
  return {
    down: (x: number, y: number) => cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: at(x, y) }),
    move: (x: number, y: number) => cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: at(x, y) }),
    up: () => cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }),
  };
}

async function centre(locator: import("@playwright/test").Locator) {
  const b = (await locator.boundingBox())!;
  return [b.x + b.width / 2, b.y + b.height / 2] as const;
}

test("holding a card opens it to read, without picking it up", async ({ page }) => {
  const errors: string[] = [];
  await deal(page, errors);
  const card = page.locator(".dock .mine .card.live").first();
  const [x, y] = await centre(card.locator("> button.face"));
  const f = await finger(page);
  await f.down(x, y);
  await page.waitForTimeout(700);
  await f.up();
  await expect(page.locator("dialog.inspect[open]")).toBeVisible();
  await expect(page.locator(".card.selected")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("a quick swipe across a card never drags it", async ({ page }) => {
  const errors: string[] = [];
  await deal(page, errors, "4");
  const card = page.locator(".dock .mine .card.grab").first();
  const [x, y] = await centre(card.locator("> button.face"));
  const f = await finger(page);
  await f.down(x, y);
  for (let i = 1; i <= 6; i++) await f.move(x, y - i * 30);
  await f.up();
  await expect(page.locator(".card.ghost")).toHaveCount(0);
  await expect(page.locator(".drop-live")).toHaveCount(0);
  await expect(page.locator(".card.selected")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("a courtier held, then dragged to the outer circle, is played there", async ({ page }) => {
  const errors: string[] = [];
  await deal(page, errors, "4");
  const outer = page.locator("section.outer");
  const f = await finger(page);
  for (const card of await page.locator(".dock .mine .card.grab").all()) {
    const uid = await card.getAttribute("data-uid");
    const [x, y] = await centre(card.locator("> button.face"));
    await f.down(x, y);
    await page.waitForTimeout(320); // held: now it drags
    await expect(card).toHaveClass(/armed/);
    for (let i = 1; i <= 3; i++) await f.move(x + i * 4, y - i * 8);
    if (!(await outer.evaluate((el) => el.classList.contains("drop-live")))) {
      await f.up(); // not a courtier: dropped nowhere
      continue;
    }
    const [tx, ty] = await centre(outer);
    for (let i = 1; i <= 8; i++) await f.move(x + ((tx - x) * i) / 8, y + ((ty - y) * i) / 8);
    await f.up();
    await expect(page.locator(`section.outer [data-uid="${uid}"], section.court [data-uid="${uid}"]`)).toBeVisible();
    expect(errors).toEqual([]);
    return;
  }
  throw new Error("no courtier in the opening hand to drag");
});
