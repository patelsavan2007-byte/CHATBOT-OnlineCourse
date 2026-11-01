import { test, expect } from "@playwright/test";
import { resolve } from "path";

test("favicon and manifest are properly linked with v=2 cache buster and no vite.svg", async ({ page }) => {
  await page.goto("/");
  
  // Check favicon link has v=2
  const favicon = page.locator('link[rel="icon"][sizes="any"]');
  await expect(favicon).toHaveAttribute("href", "/favicon.ico?v=2");

  const favicon32 = page.locator('link[rel="icon"][sizes="32x32"]');
  await expect(favicon32).toHaveAttribute("href", "/favicon-32x32.png?v=2");

  const appleIcon = page.locator('link[rel="apple-touch-icon"]');
  await expect(appleIcon).toHaveAttribute("href", "/apple-touch-icon.png?v=2");

  const manifest = page.locator('link[rel="manifest"]');
  await expect(manifest).toHaveAttribute("href", "/site.webmanifest?v=2");

  // Verify no vite.svg in head
  const viteIcon = page.locator('link[href*="vite.svg"]');
  expect(await viteIcon.count()).toBe(0);

  // Take screenshot for visual verification
  const screenshotPath = resolve("..", "REPORTS", "favicon-verification.png");
  await page.screenshot({ path: screenshotPath });
});
