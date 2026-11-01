import { test, expect } from "@playwright/test";

test.describe("Sign out confirmation dialogs", () => {
  test("Settings sign out entry point opens accessible confirmation dialog", async ({ page }) => {
    const mockUser = {
      id: "test-user-id",
      email: "student@charusat.ac.in",
      display_name: "Student User",
      role: "user",
    };

    await page.route("**/api/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockUser),
      });
    });

    await page.route("**/api/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockUser),
      });
    });

    await page.addInitScript(() => {
      localStorage.setItem("auth_token", "fake-test-token");
    });

    await page.goto("/settings");

    // Click Sign out button
    const signoutBtn = page.getByRole("button", { name: /^Sign out$/i });
    await expect(signoutBtn).toBeVisible();
    await signoutBtn.click();

    // Verify Dialog opened
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading", { name: "Sign out?" })).toBeVisible();
    await expect(
      dialog.getByText("You will need to sign in again to see your saved chats.")
    ).toBeVisible();

    // Cancel button is focused by default or available
    const cancelBtn = dialog.getByRole("button", { name: "Cancel" });
    await expect(cancelBtn).toBeVisible();

    // Cancel closes dialog and keeps session
    await cancelBtn.click();
    await expect(dialog).not.toBeVisible();
    expect(await page.evaluate(() => localStorage.getItem("auth_token"))).toBe("fake-test-token");

    // Reopen and test Escape
    await signoutBtn.click();
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();

    // Reopen and confirm sign out
    await signoutBtn.click();
    await expect(dialog).toBeVisible();
    const confirmBtn = dialog.getByRole("button", { name: /^Sign out$/i });
    await confirmBtn.click();
    await expect(dialog).not.toBeVisible();
    expect(await page.evaluate(() => localStorage.getItem("auth_token"))).toBeNull();
  });

  test("Sidebar sign out entry point opens confirmation dialog", async ({ page }) => {
    const mockUser = {
      id: "test-user-id",
      email: "student@charusat.ac.in",
      display_name: "Student User",
      role: "user",
    };

    await page.route("**/api/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockUser),
      });
    });

    await page.route("**/api/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockUser),
      });
    });

    await page.route("**/api/conversations*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.addInitScript(() => {
      localStorage.setItem("auth_token", "fake-test-token");
    });

    await page.goto("/");

    // Locate signout button in sidebar
    const sidebarSignout = page.locator("aside").getByRole("button", { name: /^Sign out$/i });
    await expect(sidebarSignout).toBeVisible();
    await sidebarSignout.click();

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading", { name: "Sign out?" })).toBeVisible();
    await expect(
      dialog.getByText("You will need to sign in again to see your saved chats.")
    ).toBeVisible();

    // Cancel keeps session
    const cancelBtn = dialog.getByRole("button", { name: "Cancel" });
    await cancelBtn.click();
    await expect(dialog).not.toBeVisible();
    expect(await page.evaluate(() => localStorage.getItem("auth_token"))).toBe("fake-test-token");
  });

  test("Admin console sign out entry point opens admin-specific confirmation dialog", async ({ page }) => {
    const adminUser = {
      id: "admin-user-id",
      email: "admin@charusat.ac.in",
      display_name: "Admin User",
      role: "admin",
    };

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
          total_queries: 0,
          unique_users: 0,
          gap_rate: 0,
          feedback_rate: 0,
          daily_counts: [],
        }),
      });
    });

    await page.addInitScript(() => {
      localStorage.setItem("auth_token", "fake-admin-token");
    });

    await page.goto("/admin");

    // Click Sign out button in admin header
    const adminSignout = page.locator("header").getByRole("button", { name: /^Sign out$/i });
    await expect(adminSignout).toBeVisible();
    await adminSignout.click();

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading", { name: "Sign out?" })).toBeVisible();
    await expect(
      dialog.getByText("You will need to sign in again to use the admin console.")
    ).toBeVisible();

    // Cancel keeps session
    const cancelBtn = dialog.getByRole("button", { name: "Cancel" });
    await cancelBtn.click();
    await expect(dialog).not.toBeVisible();
    expect(await page.evaluate(() => localStorage.getItem("auth_token"))).toBe("fake-admin-token");
  });
});
