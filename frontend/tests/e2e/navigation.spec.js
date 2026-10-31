import { expect, test } from "@playwright/test";

test("navigate from / to /settings then back returns to /chat", async ({ page }) => {
  await page.goto("/");
  await page.goto("/settings");
  await page.goBack();
  await expect(page).toHaveURL(/\/chat$/);
});

test("navigate from / to /about then back returns to /chat", async ({ page }) => {
  await page.goto("/");
  await page.goto("/about");
  await page.goBack();
  await expect(page).toHaveURL(/\/chat$/);
});

test("navigate from / to /login then back returns to /chat", async ({ page }) => {
  await page.goto("/");
  await page.goto("/login");
  await page.goBack();
  await expect(page).toHaveURL(/\/chat$/);
});

test("navigate from / to /signup then back returns to /chat", async ({ page }) => {
  await page.goto("/");
  await page.goto("/signup");
  await page.goBack();
  await expect(page).toHaveURL(/\/chat$/);
});

test("navigate from / to /admin/login then back returns to /chat", async ({ page }) => {
  await page.goto("/");
  await page.goto("/admin/login");
  await page.goBack();
  await expect(page).toHaveURL(/\/chat$/);
});

test("navigate from / to /admin then back returns to /chat", async ({ page }) => {
  await page.goto("/");
  await page.goto("/admin");
  await page.goBack();
  await expect(page).toHaveURL(/\/chat$/);
});

test("the 404 page link returns to chat", async ({ page }) => {
  await page.goto("/not-a-page");
  await page.getByRole("link", { name: "Return to chat" }).click();
  await expect(page).toHaveURL(/\/chat$/);
});

test("direct load of /about then back control falls back safely", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("button", { name: "Back to chat" }).click();
  await expect(page).toHaveURL(/\/$|\/chat$/);
});

test("removed /privacy route renders normal 404 page without redirect", async ({ page }) => {
  await page.goto("/privacy");
  await expect(page.getByText("Page not found")).toBeVisible();
  await expect(page).toHaveURL(/\/privacy$/);
});

test("removed /terms route renders normal 404 page without redirect", async ({ page }) => {
  await page.goto("/terms");
  await expect(page.getByText("Page not found")).toBeVisible();
  await expect(page).toHaveURL(/\/terms$/);
});
