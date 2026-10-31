import { expect, test } from "@playwright/test";

async function expectBackToChat(page, path) {
  await page.goto("/");
  await page.goto(path);
  await page.goBack();
  await expect(page).toHaveURL(/\/chat$/);
}

test("navigation history returns to the preceding page", async ({ page }) => {
  await expectBackToChat(page, "/settings");
  await expectBackToChat(page, "/about");
  await expectBackToChat(page, "/login");
  await expectBackToChat(page, "/signup");
  await expectBackToChat(page, "/admin/login");
  await expectBackToChat(page, "/admin");
});

test("removed legal routes render the normal 404 page", async ({ page }) => {
  for (const path of ["/privacy", "/terms"]) {
    await page.goto(path);
    await expect(page.getByText("Page not found")).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`${path}$`));
  }
});

test("404 return link and direct About back control fall back safely", async ({ page }) => {
  await page.goto("/not-a-page");
  await page.getByRole("link", { name: "Return to chat" }).click();
  await expect(page).toHaveURL(/\/chat$/);

  await page.goto("/about");
  await page.getByRole("button", { name: "Back to chat" }).click();
  await expect(page).toHaveURL(/\/$|\/chat$/);
});
