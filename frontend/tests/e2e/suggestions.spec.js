import { expect, test } from "@playwright/test";

test("typing 'which', 'fee', 'pla', and 'hw to apply' shows suggestions in dropdown", async ({ page }) => {
  // Mock /api/suggest
  await page.route("**/api/suggest", async (route) => {
    const postData = route.request().postDataJSON() || {};
    const text = (postData.text || "").toLowerCase();

    let suggestions = [];
    if (text.includes("which")) {
      suggestions = [
        { text: "Which programmes are offered online?", topic: "Programmes" },
        { text: "Which LMS is used for online classes?", topic: "LMS & Tech" },
      ];
    } else if (text.includes("fee")) {
      suggestions = [
        { text: "What is the fee structure for Online BBA?", topic: "Fees" },
        { text: "What are the semester-wise fees?", topic: "Fees" },
      ];
    } else if (text.includes("pla")) {
      suggestions = [
        { text: "Is placement assistance provided?", topic: "Placement" },
        { text: "Which companies recruit students?", topic: "Placement" },
      ];
    } else if (text.includes("hw to apply")) {
      suggestions = [
        { text: "How to apply for online admission?", topic: "Admissions" },
        { text: "What is the last date to apply?", topic: "Admissions" },
      ];
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ suggestions }),
    });
  });

  await page.goto("/chat");
  const input = page.locator("#chat-input");
  await expect(input).toBeVisible();

  for (const query of ["which", "fee", "pla", "hw to apply"]) {
    await input.fill("");
    await input.fill(query);
    const dropdown = page.locator("#composer-typing-suggestions-list");
    await expect(dropdown).toBeVisible({ timeout: 5000 });
    const items = dropdown.locator("[role='option']");
    await expect(items.first()).toBeVisible();
    const count = await items.count();
    expect(count).toBeGreaterThan(0);
  }
});
