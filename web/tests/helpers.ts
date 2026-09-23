// Playing a game through from a test, one decision at a time.
import type { Frame, FrameLocator, Page } from "@playwright/test";

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
