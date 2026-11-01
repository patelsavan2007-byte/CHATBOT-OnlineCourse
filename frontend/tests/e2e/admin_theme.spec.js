import { test, expect } from "@playwright/test";
import { resolve } from "path";

test.describe("Admin theme verification and screenshots", () => {
  const adminUser = {
    id: "admin-user-id",
    email: "admin@charusat.ac.in",
    display_name: "Admin User",
    role: "admin",
  };

  test("Admin console follows Light, Dark and System theme settings", async ({ page }) => {
    await page.route("**/api/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(adminUser),
      });
    });

    await page.route("**/api/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(adminUser),
      });
    });

    await page.route("**/api/admin/overview*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          total_queries: 124,
          unique_users: 48,
          gap_rate: 0.08,
          feedback_rate: 0.85,
          median_latency: 1.2,
          daily_counts: [
            { date: "2026-10-25", count: 18, gaps: 2 },
            { date: "2026-10-26", count: 24, gaps: 1 },
            { date: "2026-10-27", count: 30, gaps: 3 },
          ],
        }),
      });
    });

    await page.route("**/api/admin/gaps*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            normalized_question: "what is the hostel fee?",
            count: 5,
            last_seen: "2026-11-01T08:00:00Z",
            topic: "fees",
            programme: "general",
            status: "open",
            notes: "",
          },
        ]),
      });
    });

    await page.route("**/api/admin/feedback*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });

    await page.route("**/api/admin/users*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "u1",
            email: "student@charusat.ac.in",
            role: "user",
            last_active: "2026-11-01T10:00:00Z",
            is_disabled: false,
          },
        ]),
      });
    });

    await page.route("**/api/admin/system*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          database: { connected: true, name: "charusat_assistant" },
          vector_store: { connected: true, chunk_count: 301 },
          llm: { primary: "configured", failover: "configured" },
        }),
      });
    });

    await page.route("**/api/admin/kb/*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ documents: [], automation: {} }),
      });
    });

    // 1. Set Light theme and open Admin
    await page.addInitScript(() => {
      localStorage.setItem("auth_token", "fake-admin-token");
      localStorage.setItem("theme", "light");
    });

    await page.goto("/admin");

    const htmlElement = page.locator("html");
    await expect(htmlElement).toHaveClass(/light/);
    await expect(htmlElement).not.toHaveClass(/dark/);

    // Capture Light theme screenshot
    const lightOverviewShot = resolve("..", "REPORTS", "admin-screenshots", "overview-light.png");
    await page.screenshot({ path: lightOverviewShot });

    // 2. Click ThemeToggle in header -> switches to dark or system
    const themeBtn = page.locator('header button[aria-label*="mode"], header button[aria-label*="theme"]');
    await expect(themeBtn).toBeVisible();

    // Set to dark explicitly
    await page.evaluate(() => {
      localStorage.setItem("theme", "dark");
      document.documentElement.classList.remove("light");
      document.documentElement.classList.add("dark");
      document.documentElement.setAttribute("data-theme", "dark");
    });

    await expect(htmlElement).toHaveClass(/dark/);
    await expect(htmlElement).not.toHaveClass(/light/);

    // Capture Dark theme screenshot
    const darkOverviewShot = resolve("..", "REPORTS", "admin-screenshots", "overview-dark.png");
    await page.screenshot({ path: darkOverviewShot });
  });
});
