// Playing a game through from a test, one decision at a time.
import { test as base, type Frame, type FrameLocator, type Page } from "@playwright/test";

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
  const ready = "[data-testid=game-over], .all-moves";
  await surface.locator(`${ready}, [data-testid=begin]`).first().waitFor({ timeout: 60_000 });
  // A new round opens on your agenda; begin it.
  const begin = surface.locator("[data-testid=begin]");
  if (await begin.isVisible()) {
    await begin.click();
    await surface.locator(ready).first().waitFor({ timeout: 60_000 });
  }
}

/** Take one decision from the folded-away list of legal moves. False once the game is over. */
export async function playFromList(surface: Surface, choose: <T>(items: T[]) => T = (items) => items[0]): Promise<boolean> {
  await settle(surface);
  if (await surface.locator("[data-testid=game-over]").isVisible()) return false;
  await surface.locator(".all-moves summary").click();
  const options = await surface.locator("[data-testid=move-option], [data-testid=pick-option]").all();
  await choose(options).click();
  return true;
}

export function random<T>(items: T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}
