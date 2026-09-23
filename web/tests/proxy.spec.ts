// bobbymeyer.com/succession: the game behind the Netlify proxy in
// docs/EMBED.md, opened without its trailing slash. The page must add the
// slash itself -- a redirect rule for it would loop on Netlify -- and then
// load and play as usual.
import { expect, test } from "@playwright/test";

test("opened at /succession without the slash, the game puts it back and plays", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://127.0.0.1:4175/succession");
  await expect(page).toHaveURL("http://127.0.0.1:4175/succession/");
  await page.getByTestId("deal").click({ timeout: 90_000 });
  await page.locator(".all-moves, [data-testid=pick-option], [data-testid=game-over]").first().waitFor();
  await expect(page.locator(".opponent")).toHaveCount(3);
  await expect(page.locator(".seat img").first()).toBeVisible(); // card art resolved under the prefix
  expect(errors).toEqual([]);
});

test("a query string survives the added slash", async ({ page }) => {
  await page.goto("http://127.0.0.1:4175/succession?from=home");
  await expect(page).toHaveURL("http://127.0.0.1:4175/succession/?from=home");
});
