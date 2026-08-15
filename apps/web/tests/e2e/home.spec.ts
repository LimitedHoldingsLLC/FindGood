import { expect, test } from "@playwright/test";

test("home shows the discovery headline", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /what’s good near you/i })).toBeVisible();
});
