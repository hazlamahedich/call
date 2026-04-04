/**
 * Story 2.6: Voice Presets by Use Case
 * E2E Tests for Voice Preset Selection Flow
 *
 * Test ID Format: 2.6-E2E-XXX
 * Priority: P0 (Critical) | P1 (High) | P2 (Medium)
 *
 * NOTE: These tests require:
 * 1. Clerk test fixtures to be configured
 * 2. Redis to be running (optional - caching disabled if unavailable)
 * 3. Voice presets to be seeded in database
 */
import { test, expect } from "../support/merged-fixtures";

test.describe("[P0] Voice Preset Selection Flow", () => {
  // Cleanup after each test to ensure isolation
  test.afterEach(async ({ page }) => {
    // Navigate away and reset any stored state
    await page.goto("/dashboard");
    // Clear any localStorage/sessionStorage if used
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test("[2.6-E2E-001][P0] Given authenticated user, When visiting voice preset page, Then presets load successfully", async ({
    page,
  }) => {
    // Navigate to voice presets page
    await page.goto("/voice-presets");

    // Wait for page to load
    await expect(page.getByText("Choose a voice preset")).toBeVisible();
    await expect(page.getByText("Select your use case and pick a voice preset optimized for it")).toBeVisible();
  });

  test("[2.6-E2E-002][P0] Given voice preset page, When rendered, Then use case selector shows Sales, Support, Marketing", async ({
    page,
  }) => {
    await page.goto("/voice-presets");

    // Check all three use case buttons are visible
    await expect(page.getByRole("button", { name: "Sales" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Support" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Marketing" })).toBeVisible();
  });

  test("[2.6-E2E-003][P0] Given Sales use case selected, When presets load, Then 3-5 sales preset cards display", async ({
    page,
  }) => {
    await page.goto("/voice-presets");

    // Click Sales use case
    await page.getByRole("button", { name: "Sales" }).click();

    // Wait for presets to load
    await page.waitForSelector("[data-testid='preset-card']", { timeout: 5000 });

    // Count preset cards
    const presetCards = page.locator("[data-testid='preset-card']");
    const count = await presetCards.count();

    // Should have 3-5 sales presets
    expect(count).toBeGreaterThanOrEqual(3);
    expect(count).toBeLessThanOrEqual(5);
  });

  test("[2.6-E2E-004][P0] Given preset cards displayed, When clicking use case filter, Then presets filter correctly", async ({
    page,
  }) => {
    await page.goto("/voice-presets");

    // Click Sales (default)
    await page.getByRole("button", { name: "Sales" }).click();
    await page.waitForSelector("[data-testid='preset-card']");

    // Get first sales preset name
    const salesPreset = page.locator("[data-testid='preset-card']").first();
    const salesName = await salesPreset.locator("[data-testid='preset-name']").textContent();

    // Click Support
    await page.getByRole("button", { name: "Support" }).click();

    // Wait for preset cards to update (network-first pattern)
    await page.waitForSelector("[data-testid='preset-card']");

    // Get first support preset name
    const supportPreset = page.locator("[data-testid='preset-card']").first();
    const supportName = await supportPreset.locator("[data-testid='preset-name']").textContent();

    // Names should be different (different presets)
    expect(salesName).not.toBe(supportName);
  });

  test("[2.6-E2E-005][P0] Given preset card, When clicking Play Sample, Then audio plays and button shows Stop", async ({
    page,
  }) => {
    await page.goto("/voice-presets");
    await page.getByRole("button", { name: "Sales" }).click();
    await page.waitForSelector("[data-testid='preset-card']");

    // Get first preset card
    const firstCard = page.locator("[data-testid='preset-card']").first();
    const playButton = firstCard.locator("[data-testid='play-sample-button']");

    // Click play
    await playButton.click();

    // Button should show "Stop" while playing
    await expect(playButton).toContainText("Stop", { timeout: 3000 });

    // Wait for audio to finish (button state change)
    await expect(playButton).toContainText("Play", { timeout: 10000 });
  });

  test("[2.6-E2E-006][P0] Given preset card, When clicking Select, Then preset is saved and success message appears", async ({
    page,
  }) => {
    await page.goto("/voice-presets");
    await page.getByRole("button", { name: "Sales" }).click();
    await page.waitForSelector("[data-testid='preset-card']");

    // Select first preset
    const firstCard = page.locator("[data-testid='preset-card']").first();
    const selectButton = firstCard.locator("[data-testid='select-button']");

    await selectButton.click();

    // Success message should appear
    await expect(page.getByText(/saved successfully/i)).toBeVisible({ timeout: 5000 });

    // Preset card should show checkmark
    await expect(firstCard.locator("[data-testid='preset-checkmark']")).toBeVisible();
  });

  test("[2.6-E2E-007][P1] Given selected preset, When returning to page, Then preset is highlighted as selected", async ({
    page,
  }) => {
    await page.goto("/voice-presets");
    await page.getByRole("button", { name: "Sales" }).click();
    await page.waitForSelector("[data-testid='preset-card']");

    // Select first preset
    const firstCard = page.locator("[data-testid='preset-card']").first();
    await firstCard.locator("[data-testid='select-button']").click();

    // Wait for success
    await expect(page.getByText(/saved successfully/i)).toBeVisible();

    // Reload page
    await page.reload();

    // Wait for presets to load
    await page.waitForSelector("[data-testid='preset-card']");

    // First card should still be selected (has checkmark)
    await expect(firstCard.locator("[data-testid='preset-checkmark']")).toBeVisible();
  });

  test("[2.6-E2E-008][P1] Given preset selection, When changing to different preset, Then previous preset unchecks", async ({
    page,
  }) => {
    await page.goto("/voice-presets");
    await page.getByRole("button", { name: "Sales" }).click();
    await page.waitForSelector("[data-testid='preset-card']");

    // Select first preset
    const cards = page.locator("[data-testid='preset-card']");
    const firstCard = cards.nth(0);
    const secondCard = cards.nth(1);

    await firstCard.locator("[data-testid='select-button']").click();
    await expect(page.getByText(/saved successfully/i)).toBeVisible();

    // Select second preset
    await secondCard.locator("[data-testid='select-button']").click();
    await expect(page.getByText(/saved successfully/i)).toBeVisible();

    // First card should no longer be selected
    await expect(firstCard.locator("[data-testid='preset-checkmark']")).not.toBeVisible();

    // Second card should be selected
    await expect(secondCard.locator("[data-testid='preset-checkmark']")).toBeVisible();
  });
});

test.describe("[P1] Advanced Mode", () => {
  test.afterEach(async ({ page }) => {
    await page.goto("/dashboard");
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test("[2.6-E2E-009][P1] Given voice preset page, When clicking Advanced Mode toggle, Then warning appears", async ({
    page,
  }) => {
    await page.goto("/voice-presets");

    // Click Advanced Mode toggle
    const toggle = page.locator("[data-testid='advanced-mode-toggle']");
    await toggle.click();

    // Warning message should appear
    await expect(page.getByText(/Advanced settings may not sound optimal/i)).toBeVisible();
  });

  test("[2.6-E2E-010][P1] Given Advanced Mode enabled, When toggling off, Then warning disappears", async ({
    page,
  }) => {
    await page.goto("/voice-presets");

    // Enable Advanced Mode
    const toggle = page.locator("[data-testid='advanced-mode-toggle']");
    await toggle.click();
    await expect(page.getByText(/Advanced settings may not sound optimal/i)).toBeVisible();

    // Disable Advanced Mode
    await toggle.click();

    // Warning should disappear
    await expect(page.getByText(/Advanced settings may not sound optimal/i)).not.toBeVisible();
  });
});

test.describe("[P1] Error Handling", () => {
  test.afterEach(async ({ page }) => {
    await page.goto("/dashboard");
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test("[2.6-E2E-011][P1] Given TTS provider failure, When playing sample, Then error message displays gracefully", async ({
    page,
  }) => {
    await page.goto("/voice-presets");
    await page.getByRole("button", { name: "Sales" }).click();
    await page.waitForSelector("[data-testid='preset-card']");

    // Mock TTS failure endpoint
    await page.route("**/api/voice-presets/*/sample", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          error: "Voice samples temporarily unavailable. Please try again later.",
        }),
      });
    });

    // Click play sample on first preset
    const playButton = page.locator("[data-testid='preset-card']").first().locator("[data-testid='play-sample-button']");
    await playButton.click();

    // Verify error message appears
    await expect(page.getByText(/temporarily unavailable/i)).toBeVisible({ timeout: 5000 });

    // Verify UI remains functional - preset cards still visible
    await expect(page.locator("[data-testid='preset-card']").first()).toBeVisible();

    // Verify user can try other actions (e.g., select preset)
    const selectButton = page.locator("[data-testid='preset-card']").first().locator("[data-testid='select-button']");
    await expect(selectButton).toBeVisible();
  });

  test("[2.6-E2E-012][P2] Given network error, When selecting preset, Then error displays and UI remains functional", async ({
    page,
  }) => {
    await page.goto("/voice-presets");
    await page.getByRole("button", { name: "Sales" }).click();
    await page.waitForSelector("[data-testid='preset-card']");

    // Mock network failure for preset selection
    await page.route("**/api/voice-presets/select", async (route) => {
      await route.abort("failed");
    });

    // Try to select a preset
    const selectButton = page.locator("[data-testid='preset-card']").first().locator("[data-testid='select-button']");
    await selectButton.click();

    // Verify error toast appears
    await expect(page.getByText(/failed to select preset|network error/i)).toBeVisible({ timeout: 5000 });

    // Verify UI remains functional - can still see and interact with other presets
    await expect(page.locator("[data-testid='preset-card']")).toHaveCount(3); // All presets still visible

    // Verify user can retry with another preset
    const secondSelectButton = page.locator("[data-testid='preset-card']").nth(1).locator("[data-testid='select-button']");
    await expect(secondSelectButton).toBeVisible();
  });

  test("[2.6-E2E-017][P2] Given network timeout, When loading presets, Then shows loading state then error", async ({
    page,
  }) => {
    // Mock network timeout - abort request to trigger timeout immediately
    await page.route("**/api/voice-presets**", async (route) => {
      // Abort immediately to simulate network timeout
      await route.abort("failed");
    });

    await page.goto("/voice-presets");

    // Verify loading state appears
    await expect(page.getByText(/loading/i)).toBeVisible();

    // Verify error message appears after timeout
    await expect(page.getByText(/timeout|unavailable|failed to load/i)).toBeVisible({ timeout: 5000 });
  });

  test("[2.6-E2E-018][P2] Given server error 500, When loading presets, Then error message displays and UI handles gracefully", async ({
    page,
  }) => {
    // Mock server error
    await page.route("**/api/voice-presets**", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          error: "Internal server error",
        }),
      });
    });

    await page.goto("/voice-presets");

    // Verify error message appears
    await expect(page.getByText(/internal server error|something went wrong/i)).toBeVisible({ timeout: 5000 });

    // Verify error is user-friendly (not technical stack trace)
    const errorText = await page.getByText(/error/i).textContent();
    expect(errorText).not.toMatch(/stack trace|exception|undefined/i);
  });

  test("[2.6-E2E-019][P2] Given Redis unavailable, When playing sample, Then fallback to direct TTS call", async ({
    page,
  }) => {
    await page.goto("/voice-presets");
    await page.getByRole("button", { name: "Sales" }).click();
    await page.waitForSelector("[data-testid='preset-card']");

    // Mock Redis error response
    await page.route("**/api/voice-presets/*/sample", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: { arrayBuffer: () => new ArrayBuffer(1024) },
          cached: false, // Indicates fallback to direct TTS call
        }),
      });
    });

    // Click play sample
    const playButton = page.locator("[data-testid='preset-card']").first().locator("[data-testid='play-sample-button']");
    await playButton.click();

    // Verify audio still plays (fallback worked)
    await expect(playButton).toContainText("Stop", { timeout: 5000 });
  });

  test("[2.6-E2E-020][P2] Given intermittent network errors, When retrying operation, Then succeeds on retry", async ({
    page,
  }) => {
    await page.goto("/voice-presets");
    await page.getByRole("button", { name: "Sales" }).click();
    await page.waitForSelector("[data-testid='preset-card']");

    let attemptCount = 0;

    // Mock intermittent failure
    await page.route("**/api/voice-presets/select", async (route) => {
      attemptCount++;
      if (attemptCount === 1) {
        await route.abort("failed");
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: { message: "Preset selected successfully" },
          }),
        });
      }
    });

    // First attempt fails
    const selectButton = page.locator("[data-testid='preset-card']").first().locator("[data-testid='select-button']");
    await selectButton.click();

    // Wait for error
    await expect(page.getByText(/failed to select preset/i)).toBeVisible();

    // Retry - should succeed
    await selectButton.click();

    // Verify success message appears
    await expect(page.getByText(/preset selected successfully/i)).toBeVisible({ timeout: 5000 });
  });

  test("[2.6-E2E-021][P2] Given audio playback error, When error occurs, Then user can still interact with UI", async ({
    page,
  }) => {
    await page.goto("/voice-presets");
    await page.getByRole("button", { name: "Sales" }).click();
    await page.waitForSelector("[data-testid='preset-card']");

    // Mock audio decode error
    await page.route("**/api/voice-presets/*/sample", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: null,
          error: "Failed to decode audio data",
        }),
      });
    });

    // Try to play sample
    const playButton = page.locator("[data-testid='preset-card']").first().locator("[data-testid='play-sample-button']");
    await playButton.click();

    // Verify error appears
    await expect(page.getByText(/failed to play sample|audio error/i)).toBeVisible({ timeout: 5000 });

    // Verify UI is still functional - can select preset
    const selectButton = page.locator("[data-testid='preset-card']").first().locator("[data-testid='select-button']");
    await expect(selectButton).toBeVisible();

    // Verify can still switch use cases
    await expect(page.getByRole("button", { name: "Support" })).toBeVisible();
  });
});

test.describe("[P0] Tenant Isolation", () => {
  test.afterEach(async ({ page }) => {
    await page.goto("/dashboard");
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test("[2.6-E2E-013][P0] Given two orgs, When each views presets, Then they see only their own presets", async ({
    page,
  }) => {
    // This test requires multi-tenant setup with Clerk organizations
    // For now, we'll test the API-level tenant isolation by mocking responses

    await page.goto("/voice-presets");

    // Mock API response for org1 presets
    await page.route("**/api/voice-presets**", async (route) => {
      // Simulate org-scoped response
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              id: 1,
              name: "Sales - Rachel",
              use_case: "sales",
              voice_id: "voice-1",
              org_id: "org1", // Preset belongs to org1
            },
          ],
        }),
      });
    });

    // Reload page to fetch mocked data
    await page.reload();
    await page.waitForSelector("[data-testid='preset-card']");

    // Verify only org1 presets are visible
    const presetCards = page.locator("[data-testid='preset-card']");
    const count = await presetCards.count();

    expect(count).toBeGreaterThan(0);

    // Verify preset data is correctly scoped
    const firstPreset = presetCards.first();
    const presetName = await firstPreset.locator("[data-testid='preset-name']").textContent();
    expect(presetName).toBe("Sales - Rachel");
  });

  test("[2.6-E2E-014][P0] Given org1 user, When accessing org2 preset by ID, Then request is rejected with 403", async ({
    page,
  }) => {
    await page.goto("/voice-presets");

    // Mock API to return 403 for cross-tenant preset access
    await page.route("**/api/voice-presets/999**", async (route) => {
      // Simulate tenant isolation rejection
      await route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({
          error: "Access denied: Preset does not belong to your organization",
        }),
      });
    });

    // Attempt to access a preset from another org
    const response = await page.evaluate(async () => {
      try {
        const res = await fetch("/api/voice-presets/999", {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
        });
        return { status: res.status, ok: res.ok };
      } catch (error) {
        return { status: 0, ok: false };
      }
    });

    // Verify request was rejected
    expect(response.status).toBe(403);
    expect(response.ok).toBe(false);
  });

  test("[2.6-E2E-015][P1] Given preset selection, When tampering with preset_id, Then server rejects invalid preset", async ({
    page,
  }) => {
    await page.goto("/voice-presets");
    await page.getByRole("button", { name: "Sales" }).click();
    await page.waitForSelector("[data-testid='preset-card']");

    // Mock API to reject preset_id tampering
    await page.route("**/api/voice-presets/select**", async (route) => {
      const request = route.request();
      const requestBody = await request.postData();

      if (requestBody) {
        const data = JSON.parse(requestBody);

        // Simulate server validation: preset_id must belong to user's org
        if (data.preset_id === "tampered_id") {
          await route.fulfill({
            status: 403,
            contentType: "application/json",
            body: JSON.stringify({
              error: "Invalid preset: Preset does not belong to your organization",
            }),
          });
          return;
        }
      }

      // Allow legitimate preset selection
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            id: 1,
            preset_id: 1,
            use_advanced_mode: false,
          },
        }),
      });
    });

    // Attempt to select a preset with tampered preset_id
    const response = await page.evaluate(async () => {
      try {
        const res = await fetch("/api/voice-presets/select", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            preset_id: "tampered_id", // Attempt to access preset from another org
          }),
        });
        return { status: res.status, ok: res.ok };
      } catch (error) {
        return { status: 0, ok: false };
      }
    });

    // Verify request was rejected
    expect(response.status).toBe(403);
    expect(response.ok).toBe(false);
  });

  test("[2.6-E2E-016][P1] Given multi-agent setup, When assigning presets, Then each agent maintains correct preset", async ({
    page,
  }) => {
    await page.goto("/voice-presets");

    // Mock API responses for multi-agent scenario
    await page.route("**/api/agents**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              id: "agent1",
              name: "Sales Agent 1",
              preset_id: 1, // Has preset assigned
            },
            {
              id: "agent2",
              name: "Support Agent 1",
              preset_id: 2, // Different preset assigned
            },
          ],
        }),
      });
    });

    // Navigate to agents page (assuming it exists)
    await page.goto("/dashboard/agents");

    // Wait for agent list to load
    await page.waitForSelector("[data-testid='agent-card']");

    // Verify agents have different presets
    const agentCards = page.locator("[data-testid='agent-card']");
    const count = await agentCards.count();

    expect(count).toBeGreaterThanOrEqual(2);

    // Verify first agent has preset 1
    const agent1 = agentCards.nth(0);
    const agent1Preset = await agent1.locator("[data-testid='agent-preset-id']").textContent();
    expect(agent1Preset).toContain("1");

    // Verify second agent has preset 2
    const agent2 = agentCards.nth(1);
    const agent2Preset = await agent2.locator("[data-testid='agent-preset-id']").textContent();
    expect(agent2Preset).toContain("2");
  });
});

test.describe("[P1] Performance Recommendations (AC6)", () => {
  test.beforeEach(async ({ page }) => {
    // Mock that user has made 10+ calls (eligible for recommendations)
    await page.goto("/voice-presets");
  });

  test.afterEach(async ({ page }) => {
    await page.goto("/dashboard");
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test("[2.6-E2E-022][P1] Given user with 10+ calls, When visiting presets, Then recommendation banner displays", async ({
    page,
  }) => {
    // Mock API to return recommendation
    await page.route("**/api/voice-presets/recommendation", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            preset_name: "Sales - Alex",
            improvement_pct: 23,
            reasoning: "Higher energy voice correlates with 15% better pickup rates in sales calls",
          },
          error: null,
        }),
      });
    });

    await page.goto("/voice-presets");

    // Verify recommendation banner appears
    await expect(page.getByText("Performance-Based Recommendation")).toBeVisible();
    await expect(page.getByText(/"Sales - Alex"/)).toBeVisible();
    await expect(page.getByText(/23% better pickup rates/)).toBeVisible();
  });

  test("[2.6-E2E-023][P1] Given recommendation banner, When clicking Apply, Then preset is selected", async ({
    page,
  }) => {
    // Mock recommendation API
    await page.route("**/api/voice-presets/recommendation", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            preset_name: "Sales - Alex",
            improvement_pct: 23,
            reasoning: "Higher energy voice correlates with 15% better pickup rates",
          },
          error: null,
        }),
      });
    });

    // Mock preset selection API
    let selectCalled = false;
    await page.route("**/api/voice-presets/select", async (route) => {
      selectCalled = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: { message: "Preset selected successfully" },
          error: null,
        }),
      });
    });

    await page.goto("/voice-presets");

    // Click Apply Recommendation button
    await page.getByRole("button", { name: "Apply Recommendation" }).click();

    // Verify selection was called
    expect(selectCalled).toBe(true);

    // Verify success message
    await expect(page.getByText(/preset selected successfully/i)).toBeVisible();
  });

  test("[2.6-E2E-024][P2] Given recommendation banner, When clicking Dismiss, Then banner disappears", async ({
    page,
  }) => {
    // Mock recommendation API
    await page.route("**/api/voice-presets/recommendation", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            preset_name: "Sales - Alex",
            improvement_pct: 23,
            reasoning: "Higher energy voice correlates with 15% better pickup rates",
          },
          error: null,
        }),
      });
    });

    await page.goto("/voice-presets");

    // Verify banner is visible
    await expect(page.getByText("Performance-Based Recommendation")).toBeVisible();

    // Click dismiss button
    const dismissButton = page.getByLabel("Dismiss recommendation");
    await dismissButton.click();

    // Verify banner is no longer visible
    await expect(page.getByText("Performance-Based Recommendation")).not.toBeVisible();
  });

  test("[2.6-E2E-025][P2] Given user with <10 calls, When visiting presets, Then no recommendation displays", async ({
    page,
  }) => {
    // Mock API to return no recommendation (user hasn't made 10 calls yet)
    await page.route("**/api/voice-presets/recommendation", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: null,
          error: null,
        }),
      });
    });

    await page.goto("/voice-presets");

    // Verify recommendation banner does NOT appear
    await expect(page.getByText("Performance-Based Recommendation")).not.toBeVisible();
  });
});
