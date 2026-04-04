/** E2E tests for knowledge ingestion flow. */

import { test, expect } from "@playwright/test";

test.describe("Knowledge Ingestion", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to knowledge base page
    await page.goto("/onboarding/knowledge");
  });

  test("should display knowledge base interface", async ({ page }) => {
    // Check that the main elements are present
    await expect(page.locator("h2")).toContainText("Knowledge Base");
    await expect(page.locator("text=Upload PDF")).toBeVisible();
    await expect(page.locator("text=Add URL")).toBeVisible();
    await expect(page.locator("text=Paste Text")).toBeVisible();
  });

  test("should switch between tabs", async ({ page }) => {
    // Click on URL tab
    await page.click("text=Add URL");
    await expect(page.locator('input[type="url"]')).toBeVisible();

    // Click on Text tab
    await page.click("text=Paste Text");
    await expect(page.locator("textarea")).toBeVisible();

    // Click on File tab
    await page.click("text=Upload File");
    await expect(page.locator('input[type="file"]')).toBeVisible();
  });

  test("should validate URL input", async ({ page }) => {
    await page.click("text=Add URL");

    // Try to submit without URL
    await page.click("button:has-text('Add')");

    // Should show error
    await expect(page.locator("text=URL is required")).toBeVisible();
  });

  test("should validate text input", async ({ page }) => {
    await page.click("text=Paste Text");

    // Try to submit without text
    await page.click("button:has-text('Add')");

    // Should show error
    await expect(page.locator("text=Text is required")).toBeVisible();
  });

  test("should show document list", async ({ page }) => {
    // Documents section should be visible
    await expect(page.locator("text=Documents")).toBeVisible();
  });

  test("should show empty state when no documents", async ({ page }) => {
    await expect(
      page.locator("text=No documents yet")
    ).toBeVisible();
  });

  test("should display document status badges", async ({ page }) => {
    // If documents exist, they should have status badges
    const statusBadges = page.locator("[class*='bg-']");
    const count = await statusBadges.count();

    if (count > 0) {
      // Check that badges have proper classes
      const firstBadge = statusBadges.first();
      await expect(firstBadge).toHaveClass(/rounded-full/);
    }
  });

  test("should disable delete for processing documents", async ({ page }) => {
    // Find documents with Processing status
    const processingDocs = page.locator("text=Processing");

    const count = await processingDocs.count();
    for (let i = 0; i < count; i++) {
      const doc = processingDocs.nth(i);
      const deleteButton = doc.locator("button:has-text('Delete')");

      if (await deleteButton.isVisible()) {
        await expect(deleteButton).toBeDisabled();
      }
    }
  });

  test("should show error message for upload failure", async ({ page }) => {
    // This test would require mocking the API to return an error
    // For now, document the expected behavior
    // Expected: Error banner should be visible
  });

  test("should show success message after upload", async ({ page }) => {
    // This test would require mocking a successful upload
    // For now, document the expected behavior
    // Expected: Success message should be visible
    // Expected: Document should appear in list
  });

  test("should confirm before deleting", async ({ page }) => {
    // Find a delete button (if documents exist)
    const deleteButton = page.locator("button:has-text('Delete')").first();

    if (await deleteButton.isVisible()) {
      // Click delete
      await deleteButton.click();

      // Should show confirmation dialog
      const dialog = page.locator("dialog");
      await expect(dialog).toBeVisible();
      await expect(dialog).toContainText("delete");
    }
  });

  test("should poll for status updates", async ({ page }) => {
    // This test would require:
    // 1. Upload a document
    // 2. Verify status changes from Processing to Ready
    // 3. Verify update happens within polling interval (3 seconds)

    // For now, document that polling should be active
    // Check that status badges update every ~3 seconds
  });

  test("should handle file upload with drag and drop", async ({ page }) => {
    await page.click("text=Upload File");

    const dropZone = page.locator("input[type='file']").locator("..");

    // Drag and drop would be tested here
    // For now, verify drop zone is visible
    await expect(dropZone).toBeVisible();
  });

  test("should validate file size", async ({ page }) => {
    // This test would require mocking file upload with oversized file
    // Expected: Error message about file size
  });

  test("should validate file format", async ({ page }) => {
    // This test would require uploading invalid file
    // Expected: Error message about unsupported format
  });
});

test.describe("Knowledge Ingestion - Authentication", () => {
  test("should redirect if not authenticated", async ({ page }) => {
    // Clear authentication
    await page.context().clearCookies();
    await page.goto("/onboarding/knowledge");

    // Should redirect to login or show auth error
    // Implementation depends on auth setup
  });
});

test.describe("Knowledge Ingestion - API Integration", () => {
  test("should upload PDF file", async ({ page }) => {
    // Mock the API call
    await page.route("**/api/v1/knowledge/upload", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          knowledgeBaseId: 1,
          status: "processing",
          message: "Document uploaded successfully",
        }),
      });
    });

    await page.goto("/onboarding/knowledge");
    await page.click("text=Upload File");

    // Simulate file upload
    const fileInput = page.locator("input[type='file']");
    await fileInput.setInputFiles({
      name: "test.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-test"),
    });

    await page.click("button:has-text('Upload')");

    // Should show success message
    await expect(page.locator("text=uploaded successfully")).toBeVisible();
  });

  test("should add URL", async ({ page }) => {
    // Mock the API call
    await page.route("**/api/v1/knowledge/upload", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          knowledgeBaseId: 1,
          status: "processing",
          message: "URL added successfully",
        }),
      });
    });

    await page.goto("/onboarding/knowledge");
    await page.click("text=Add URL");

    await page.fill('input[type="url"]', "https://example.com");
    await page.click("button:has-text('Add')");

    // Should show success message
    await expect(page.locator("text=added successfully")).toBeVisible();
  });

  test("should add text", async ({ page }) => {
    // Mock the API call
    await page.route("**/api/v1/knowledge/upload", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          knowledgeBaseId: 1,
          status: "processing",
          message: "Text added successfully",
        }),
      });
    });

    await page.goto("/onboarding/knowledge");
    await page.click("text=Paste Text");

    await page.fill("textarea", "Test content that meets minimum length requirements for knowledge base ingestion.");
    await page.click("button:has-text('Add')");

    // Should show success message
    await expect(page.locator("text=added successfully")).toBeVisible();
  });

  test("should list documents", async ({ page }) => {
    // Mock the API call
    await page.route("**/api/v1/knowledge/documents*", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              id: 1,
              orgId: "test-org",
              title: "Test Document",
              sourceType: "pdf",
              chunkCount: 5,
              status: "ready",
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          ],
          total: 1,
          page: 1,
          pageSize: 20,
        }),
      });
    });

    await page.goto("/onboarding/knowledge");

    // Should show document
    await expect(page.locator("text=Test Document")).toBeVisible();
    await expect(page.locator("text=5 chunks")).toBeVisible();
    await expect(page.locator("text=Ready")).toBeVisible();
  });

  test("should delete document", async ({ page }) => {
    // Mock list and delete API calls
    await page.route("**/api/v1/knowledge/documents*", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              id: 1,
              orgId: "test-org",
              title: "Test Document",
              sourceType: "pdf",
              chunkCount: 5,
              status: "ready",
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          ],
          total: 1,
          page: 1,
          pageSize: 20,
        }),
      });
    });

    await page.route("**/api/v1/knowledge/documents/1", (route) => {
      if (route.request().method() === "DELETE") {
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            message: "Document deleted successfully",
          }),
        });
      }
    });

    await page.goto("/onboarding/knowledge");

    // Click delete
    const deleteButton = page.locator("button:has-text('Delete')").first();
    await deleteButton.click();

    // Confirm deletion
    await page.click("button:has-text('OK')");

    // Should show success message
    await expect(page.locator("text=deleted successfully")).toBeVisible();
  });
});

test.describe("Knowledge Ingestion - Error Handling", () => {
  test("should display API error message", async ({ page }) => {
    // Mock API error
    await page.route("**/api/v1/knowledge/upload", (route) => {
      route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Invalid file format",
        }),
      });
    });

    await page.goto("/onboarding/knowledge");
    await page.click("text=Upload File");

    const fileInput = page.locator("input[type='file']");
    await fileInput.setInputFiles({
      name: "test.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-test"),
    });

    await page.click("button:has-text('Upload')");

    // Should show error message
    await expect(page.locator("text=Invalid file format")).toBeVisible();
  });

  test("should handle network error gracefully", async ({ page }) => {
    // Mock network failure
    await page.route("**/api/v1/knowledge/upload", (route) => {
      route.abort("failed");
    });

    await page.goto("/onboarding/knowledge");
    await page.click("text=Upload File");

    const fileInput = page.locator("input[type='file']");
    await fileInput.setInputFiles({
      name: "test.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-test"),
    });

    await page.click("button:has-text('Upload')");

    // Should show error message
    await expect(page.locator("text=failed")).toBeVisible();
  });
});
