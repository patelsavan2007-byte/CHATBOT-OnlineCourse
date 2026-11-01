import { test, expect } from "@playwright/test";

test.describe("Knowledge Base Manager and Answer This Workflow (Part 3 & 4)", () => {
  const adminUser = {
    id: "admin-user-id",
    email: "admin@charusat.ac.in",
    display_name: "Admin User",
    role: "admin",
  };

  test("upload, review, publish and answer-this workflows", async ({ page }) => {
    // 1. Mock user authentication
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

    // 2. Mock overview
    await page.route("**/api/admin/overview*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          range_days: 30,
          total_queries: 100,
          answered_queries: 90,
          gap_queries: 10,
          gap_rate: 0.1,
          median_latency_s: 1.0,
          active_users: 25,
          total_users: 40,
          feedback: { thumbs_up: 10, thumbs_down: 1, total_ratings: 11, enough_ratings: false },
          queries_per_day: [],
        }),
      });
    });

    // 3. Mock Knowledge Base endpoints
    let docsList = [
      {
        slug: "ciqa",
        filename: "ciqa.md",
        rel_path: "ciqa.md",
        title: "Centre for Internal Quality Assurance",
        source_type: "Website",
        programme: "GENERAL",
        chunks: 16,
        status: "Live",
        can_delete: false,
      },
      {
        slug: "fee-notice",
        filename: "fee_notice.pdf",
        rel_path: "uploads/fee_notice.md",
        title: "Fee Notice 2026",
        source_type: "Upload",
        programme: "MBA",
        chunks: 0,
        status: "Saved to repository",
        can_delete: true,
      },
    ];

    await page.route("**/api/admin/kb/status", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          automation: {
            configured: true,
            last_run: "2026-11-01T07:00:00Z",
            status: "idle",
            result: "success",
            trigger: "schedule",
            run_url: "https://github.com/charusat/chatbot/actions/runs/1",
          },
          index: {
            total_chunks: 301,
            total_documents: docsList.length,
          },
          documents: docsList,
        }),
      });
    });

    await page.route("**/api/admin/knowledge-base", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          total_chunks: 301,
          total_documents: docsList.length,
          last_ingested_at: "2026-11-01T07:00:00Z",
          chunks_per_programme: { bba: 60, bca: 78, mba: 84, mca: 64, general: 15 },
          documents: [],
        }),
      });
    });

    // Mock file convert
    await page.route("**/api/admin/kb/convert", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          draft_id: "draft_test_123",
          title: "Exam Schedule Winter 2026",
          filename: "exam_schedule.txt",
          markdown: "## Examination Schedule\\n\\nExams begin on December 15, 2026.",
          warnings: [],
          page_count: 1,
          chunk_estimate: 2,
          can_publish: true,
          programme: "GENERAL",
        }),
      });
    });

    // Mock publish
    await page.route("**/api/admin/kb/drafts/draft_test_123/publish", async (route) => {
      docsList.push({
        slug: "exam-schedule-winter-2026",
        filename: "exam_schedule.txt",
        rel_path: "uploads/exam-schedule-winter-2026.md",
        title: "Exam Schedule Winter 2026",
        source_type: "Upload",
        programme: "GENERAL",
        chunks: 0,
        status: "Rebuilding",
        can_delete: true,
      });
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "success",
          slug: "exam-schedule-winter-2026",
          rel_path: "uploads/exam-schedule-winter-2026.md",
          github_committed: true,
          workflow_triggered: true,
          message: "Document published to repository. Rebuild workflow dispatched.",
        }),
      });
    });

    // Mock test question
    await page.route("**/api/admin/kb/test-question", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          question: "When are the winter exams?",
          standalone_question: "When are the winter exams?",
          answerable: true,
          relevance_score: 0.88,
          chunks: [
            {
              source: "uploads/exam-schedule-winter-2026.md",
              title: "Exam Schedule Winter 2026",
              programme: "GENERAL",
              content_snippet: "Exams begin on December 15, 2026.",
              score: 0.88,
            },
          ],
        }),
      });
    });

    // Mock Needs Attention (knowledge gaps & feedback)
    let gapsList = [
      {
        id: "gap-1",
        question: "How do I download my grade card?",
        normalized_question: "how do i download my grade card",
        topic: "examination",
        programme: "bca",
        frequency: 4,
        review_status: "open",
        last_seen: "2026-11-01T10:00:00Z",
      },
    ];

    await page.route("**/api/admin/knowledge-gaps*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ gaps: gapsList }),
      });
    });

    await page.route("**/api/admin/feedback*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ feedback: [] }),
      });
    });

    // Mock FAQ endpoint
    await page.route("**/api/admin/kb/faq", async (route) => {
      gapsList = gapsList.map((g) => ({ ...g, review_status: "resolved" }));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "success",
          slug: "faq-how-do-i-download-my-grade-card",
          rel_path: "uploads/faq-how-do-i-download-my-grade-card.md",
          message: "FAQ document created and knowledge gap resolved.",
        }),
      });
    });

    // Inject auth token before navigation
    await page.addInitScript(() => {
      localStorage.setItem("auth_token", "fake-admin-token");
      localStorage.setItem("theme", "light");
    });

    // Navigate to Admin
    await page.goto("/admin");
    await expect(page.locator("h1")).toContainText("CCOE CHARUSAT Admin Console");

    // --- STEP 1: Test Knowledge Base Manager Tab ---
    await page.click('button:has-text("Knowledge Base")');
    await expect(page.locator("text=Automation")).toBeVisible();
    await expect(page.locator("text=Centre for Internal Quality Assurance")).toBeVisible();

    // Trigger file upload
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.click('text="Upload document"');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: "exam_schedule.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Exams begin on December 15, 2026."),
    });

    // Verify Review Modal opens
    await expect(page.locator("text=Review Document Draft")).toBeVisible();
    await expect(page.locator("text=Pages: 1")).toBeVisible();
    await expect(page.locator("text=Estimated Chunks: 2")).toBeVisible();

    // Click Publish to Knowledge Base
    await page.click('button:has-text("Publish to Knowledge Base")');
    await expect(page.locator("text=Publish Document to Knowledge Base?")).toBeVisible();

    // Confirm publish
    await page.click('button:has-text("Confirm Publish")');
    await expect(page.locator("text=Document published to repository")).toBeVisible();

    // Test a question dry-run
    await page.fill('input[placeholder*="test question"]', "When are the winter exams?");
    await page.click('button:has-text("Ask")');
    await expect(page.locator("text=Probably answerable now")).toBeVisible();
    await expect(page.locator("text=Relevance score:")).toBeVisible();

    // --- STEP 2: Test "Answer this" Action in Needs Attention Tab ---
    await page.click('button:has-text("Needs attention")');
    await expect(page.locator("text=How do I download my grade card?")).toBeVisible();

    // Click Answer this
    await page.click('button:has-text("Answer this")');
    await expect(page.locator("text=Answer Unanswered Question")).toBeVisible();

    // Fill answer and source
    await page.fill('textarea[placeholder*="Write the clear"]', "Log in to the student portal at charusat.online and click on Examination -> Grade Cards.");
    await page.fill('input[placeholder*="charusat.online"]', "https://charusat.online/student-portal");

    // Click Publish FAQ
    await page.click('button:has-text("Publish FAQ")');
    await expect(page.locator("text=FAQ document saved and knowledge gap resolved")).toBeVisible();
  });
});
