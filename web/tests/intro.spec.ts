// The introduction: once on a first visit, and again only when asked for.
import { expect, test } from "./helpers";

test.use({ firstVisit: true });

test("a first visit opens on the introduction, and it plays through to the title", async ({ page }) => {
  await page.goto("./");
  const intro = page.getByTestId("intro");
  await expect(intro).toBeVisible();
  await expect(intro).toContainText("The King has died");
  // Clicking hurries it along: each beat's lines, then the next beat.
  for (let i = 0; i < 12 && !(await page.getByTestId("enter").isVisible()); i++) {
    await intro.click({ position: { x: 20, y: 200 } });
  }
  await expect(page.getByRole("heading", { name: "Succession" })).toBeVisible();
  await page.getByTestId("enter").click();
  await expect(intro).toBeHidden();
  await expect(page.getByTestId("deal")).toBeVisible({ timeout: 90_000 });
});

test("once seen it stays away, until you ask to watch it", async ({ page }) => {
  await page.goto("./");
  await page.getByTestId("skip-intro").click();
  await expect(page.getByTestId("intro")).toBeHidden();
  await page.reload();
  await expect(page.getByTestId("deal")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByTestId("intro")).toHaveCount(0);

  await page.getByTestId("watch-intro").click();
  await expect(page.getByTestId("intro")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("intro")).toBeHidden();
  await expect(page.getByTestId("deal")).toBeVisible();
});
