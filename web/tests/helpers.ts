// Playing a game through from a test, one decision at a time.
import { test as base, type Frame, type FrameLocator, type Locator, type Page } from "@playwright/test";

export { expect } from "@playwright/test";

/**
 * Tests start as a returning player, past the introduction, unless they ask
 * for a first visit with `test.use({ firstVisit: true })`. The init script
 * runs in every frame, so an embedded game skips it too.
 */
export const test = base.extend<{ firstVisit: boolean }>({
  firstVisit: [false, { option: true }],
  page: async ({ page, firstVisit }, use) => {
    if (!firstVisit) await page.addInitScript(() => localStorage.setItem("succession.introSeen", "1"));
    await use(page);
  },
});

type Surface = Page | Frame | FrameLocator;

/** Wait until the page is asking for a decision, or the game is over. */
export async function settle(surface: Surface) {
  const ready = "[data-testid=game-over], .all-moves, [data-testid=block]";
  // A new round opens on your agenda, and an event stops play until it has
  // been read: begin, or carry on, until the page asks for a decision. An
  // event that asks you something is announced first; it closes by itself.
  // A turn that ends over the hand limit says so before the discard.
  const buttons = "[data-testid=begin], [data-testid=event-continue], [data-testid=limit-continue]";
  const announce = surface.locator("[data-testid=event-announce]");
  for (let i = 0; i < 50; i++) {
    await surface.locator(`${ready}, ${buttons}, [data-testid=event-announce]`).first().waitFor({ timeout: 60_000 });
    if (await announce.count()) {
      // Click it away, unless it is already on its way out.
      await surface.locator("[data-testid=event-announce]:not(.closing)").click({ timeout: 1_000 }).catch(() => {});
      await announce.waitFor({ state: "detached", timeout: 15_000 });
      continue;
    }
    const button = surface.locator(buttons).first();
    if (await button.isVisible()) {
      await button.click();
      continue;
    }
    if (await surface.locator(ready).first().isVisible()) return;
  }
}

/** Take one decision from the folded-away list of legal moves. False once the game is over. */
export async function playFromList(surface: Surface, choose: <T>(items: T[]) => T = (items) => items[0]): Promise<boolean> {
  await settle(surface);
  if (await surface.locator("[data-testid=game-over]").isVisible()) return false;
  // A rival attacks a courtier your Defense covers: block, or let it land.
  const block = surface.locator("[data-testid=block]");
  if (await block.isVisible()) {
    await choose(await block.getByRole("button").all()).click();
    return true;
  }
  await surface.locator(".all-moves summary").click();
  const options = await surface.locator("[data-testid=move-option], [data-testid=pick-option]").all();
  await choose(options).click();
  return true;
}

export function random<T>(items: T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}

// -- one test for every screen: where a phone keeps what a desktop shows ----

/** On a phone, open the ☰ menu, where the rail's controls live. */
export async function openMenu(page: Page) {
  const menu = page.getByTestId("menu");
  if ((await menu.isVisible()) && (await menu.getAttribute("aria-expanded")) !== "true") await menu.click();
}

/** Click one of the table's controls (Rules, New game), through the menu on a phone. */
export async function fromMenu(page: Page, control: Locator) {
  await openMenu(page);
  await control.click();
}

/** Show your agenda or the log: a tab on a desktop, a sheet from the dock on a phone. */
export async function showPanel(page: Page, which: "agenda" | "log") {
  const dock = page.getByTestId(`dock-${which}`);
  if (await dock.isVisible()) {
    if ((await dock.getAttribute("aria-expanded")) !== "true") await dock.click();
  } else {
    const tab = page.getByRole("tab", { name: which === "log" ? "Log" : /Agenda/ });
    // The rail is sticky and scrolls on its own; Playwright's scrolling lands
    // the click beside it, where a person would simply scroll the rail.
    await tab.evaluate((el) => el.scrollIntoView({ block: "center" }));
    await tab.click();
  }
}

/** Type a seed on the title screen: the field sits under "Custom table". */
export async function setSeed(page: Page, seed: string | number) {
  const custom = page.getByTestId("custom-table");
  if (!(await custom.evaluate((d) => (d as HTMLDetailsElement).open))) await custom.locator("summary").click();
  await page.fill("input[placeholder=random]", String(seed));
}
