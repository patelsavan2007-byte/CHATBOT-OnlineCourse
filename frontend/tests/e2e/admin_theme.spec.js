import { test, expect } from "@playwright/test";
import { resolve } from "path";

test.describe("Admin console verification and tab screenshots", () => {
  const adminUser = {
    id: "admin-user-id",
    email: "admin@charusat.ac.in",
    display_name: "Admin User",
    role: "admin",
  };

  test("Capture all 5 admin tabs in light and dark modes", async ({ page }) => {
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
          range_days: 30,
          total_queries: 142,
          answered_queries: 130,
          gap_queries: 12,
          gap_rate: 0.0845,
          median_latency_s: 1.15,
          active_users: 38,
          total_users: 52,
          feedback: {
            thumbs_up: 22,
            thumbs_down: 2,
            total_ratings: 24,
            feedback_rate: 0.169,
            positive_share: 0.917,
            enough_ratings: true,
          },
          queries_per_day: [
            { date: "2026-10-25", total: 18, answered: 16, gaps: 2 },
            { date: "2026-10-26", total: 24, answered: 23, gaps: 1 },
            { date: "2026-10-27", total: 30, answered: 27, gaps: 3 },
            { date: "2026-10-28", total: 22, answered: 20, gaps: 2 },
            { date: "2026-10-29", total: 28, answered: 26, gaps: 2 },
            { date: "2026-10-30", total: 20, answered: 18, gaps: 2 },
          ],
        }),
      });
    });

    await page.route("**/api/admin/knowledge-gaps*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          gaps: [
            {
              id: "gap-1",
              normalized_question: "what is the hostel fee structure?",
              question: "What is the hostel fee structure?",
              count: 6,
              frequency: 6,
              topic: "fees",
              topics: ["fees"],
              programme: "general",
              programmes: ["general"],
              review_status: "open",
              last_seen: "2026-11-01T08:00:00Z",
              retest_status: null,
            },
            {
              id: "gap-2",
              normalized_question: "are international students eligible?",
              question: "Are international students eligible for online BCA?",
              count: 4,
              frequency: 4,
              topic: "eligibility",
              topics: ["eligibility"],
              programme: "bca",
              programmes: ["online_bca"],
              review_status: "open",
              last_seen: "2026-11-01T09:30:00Z",
              retest_status: "Probably answerable now",
            },
          ],
          total: 2,
        }),
      });
    });

    await page.route("**/api/admin/feedback*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          feedback_items: [
            {
              id: "msg-1",
              question: "Can I pay fees in installments?",
              answer: "Please contact admission office for EMI details.",
              reason: "Wanted specific EMI schedule",
              review_status: "open",
              timestamp: "2026-10-31T12:00:00Z",
            },
          ],
          total: 1,
        }),
      });
    });

    await page.route("**/api/admin/knowledge-base*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          total_chunks: 301,
          total_documents: 23,
          chunks_per_programme: { bba: 60, bca: 78, mba: 84, mca: 64, general: 15 },
          last_ingested_at: "2026-11-01T07:00:00Z",
          last_modified: "2026-11-01T07:00:00Z",
          documents: [
            { name: "ciqa.md", program: "general", chunk_count: 16, source: "backend/knowledge_base/ciqa.md" },
            { name: "bca_syllabus.pdf", program: "bca", chunk_count: 78, source: "backend/knowledge_base/bca_syllabus.pdf" },
          ],
        }),
      });
    });

    await page.route("**/api/admin/users*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          users: [
            {
              id: "admin-user-id",
              email: "admin@charusat.ac.in",
              role: "admin",
              created_at: "2026-10-20T10:00:00Z",
              last_active: "2026-11-01T11:00:00Z",
              is_disabled: false,
            },
            {
              id: "u-2",
              email: "student@charusat.ac.in",
              role: "user",
              created_at: "2026-10-22T14:00:00Z",
              last_active: "2026-11-01T10:30:00Z",
              is_disabled: false,
            },
          ],
          total: 2,
        }),
      });
    });

    await page.route("**/api/admin/system*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          python_version: "3.14.6",
          os_platform: "Windows",
          database: { connected: true, name: "charusat_assistant" },
          vector_store: { ready: true, chunks: 301 },
          models: {
            primary: "Gemini 2.5 Flash",
            primary_status: "configured",
            failover: "Groq (openai/gpt-oss-120b)",
            failover_status: "configured",
          },
          cache: { hits: 142, misses: 28, hit_rate: 0.835 },
          recent_logs: [
            {
              id: "log-1",
              timestamp: "2026-11-01T10:30:00Z",
              admin_email: "admin@charusat.ac.in",
              action: "admin_login",
              target_type: "auth",
              details: { role: "admin" },
            },
          ],
        }),
      });
    });

    // 1. Initial load in Light theme
    await page.addInitScript(() => {
      localStorage.setItem("auth_token", "fake-admin-token");
      localStorage.setItem("theme", "light");
    });

    await page.goto("/admin");
    const html = page.locator("html");
    await expect(html).toHaveClass(/light/);

    const tabs = [
      { id: "overview", btnName: "Overview", filePrefix: "overview" },
      { id: "needs_attention", btnName: "Needs attention", filePrefix: "needs-attention" },
      { id: "knowledge_base", btnName: "Knowledge Base", filePrefix: "knowledge-base" },
      { id: "users", btnName: "Users", filePrefix: "users" },
      { id: "system", btnName: "System", filePrefix: "system" },
    ];

    // Screenshot all 5 tabs in Light theme
    for (const tab of tabs) {
      await page.getByRole("button", { name: tab.btnName, exact: true }).click();
      await page.waitForTimeout(150);
      const shotPath = resolve("..", "REPORTS", "admin-screenshots", `${tab.filePrefix}-light.png`);
      await page.screenshot({ path: shotPath });
    }

    // 2. Switch to Dark theme
    await page.evaluate(() => {
      localStorage.setItem("theme", "dark");
      document.documentElement.classList.remove("light");
      document.documentElement.classList.add("dark");
      document.documentElement.setAttribute("data-theme", "dark");
    });
    await expect(html).toHaveClass(/dark/);

    // Screenshot all 5 tabs in Dark theme
    for (const tab of tabs) {
      await page.getByRole("button", { name: tab.btnName, exact: true }).click();
      await page.waitForTimeout(150);
      const shotPath = resolve("..", "REPORTS", "admin-screenshots", `${tab.filePrefix}-dark.png`);
      await page.screenshot({ path: shotPath });
    }
  });
});
