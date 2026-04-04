/**
 * API-First Setup Helpers for Story 2.6 - Voice Presets
 *
 * Provides fast, deterministic test data setup via API calls.
 * Follows data-factories.md best practices from TEA knowledge base.
 */

import type { APIRequestContext } from "@playwright/test";
import { createVoicePreset, createSalesPreset, createSupportPreset, createMarketingPreset } from "./factories";

/**
 * Seed voice presets via API
 * Creates test presets quickly without UI navigation
 */
export async function seedVoicePresets(
  request: APIRequestContext,
  count: number = 5,
  useCase: "sales" | "support" | "marketing" = "sales"
): Promise<VoicePreset[]> {
  const presets: VoicePreset[] = [];

  for (let i = 0; i < count; i++) {
    const preset =
      useCase === "sales"
        ? createSalesPreset({ sort_order: i + 1 })
        : useCase === "support"
        ? createSupportPreset({ sort_order: i + 1 })
        : createMarketingPreset({ sort_order: i + 1 });

    // Create preset via API
    const response = await request.post("/api/voice-presets", {
      data: preset,
    });

    if (!response.ok()) {
      throw new Error(`Failed to seed preset: ${response.status()} ${await response.text()}`);
    }

    const created = await response.json();
    presets.push(created);
  }

  return presets;
}

/**
 * Select a voice preset via API
 * Fast preset selection without UI interaction
 */
export async function selectVoicePresetViaAPI(
  request: APIRequestContext,
  presetId: number,
  useAdvancedMode: boolean = false
): Promise<{ success: boolean; message?: string }> {
  const response = await request.post("/api/voice-presets/select", {
    data: {
      preset_id: presetId,
      use_advanced_mode: useAdvancedMode,
    },
  });

  if (!response.ok()) {
    throw new Error(`Failed to select preset: ${response.status()} ${await response.text()}`);
  }

  return await response.json();
}

/**
 * Cleanup: Delete all created presets
 */
export async function cleanupVoicePresets(
  request: APIRequestContext,
  presetIds: number[]
): Promise<void> {
  for (const id of presetIds) {
    try {
      await request.delete(`/api/voice-presets/${id}`);
    } catch (error) {
      // Log but don't fail - cleanup is best-effort
      console.warn(`Failed to cleanup preset ${id}:`, error);
    }
  }
}

/**
 * Mock API response for preset samples
 * Prevents actual TTS calls during tests
 */
export function mockPresetSampleAPI(page: any, sampleData?: ArrayBuffer): void {
  page.route("**/api/voice-presets/*/sample", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          arrayBuffer: () => Promise.resolve(sampleData || new ArrayBuffer(1024)),
        },
        error: null,
      }),
    });
  });
}

/**
 * Mock API error scenarios
 */
export function mockPresetAPIError(
  page: any,
  errorType: "timeout" | "server-error" | "network-error"
): void {
  page.route("**/api/voice-presets**", async (route) => {
    switch (errorType) {
      case "timeout":
        await route.abort("failed");
        break;
      case "server-error":
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ error: "Internal server error" }),
        });
        break;
      case "network-error":
        await route.abort("failed");
        break;
    }
  });
}

/**
 * Mock preset selection API with failure scenarios
 */
export function mockPresetSelectionError(
  page: any,
  failFirstAttempt: boolean = false
): { attemptCount: number } => {
  const state = { attemptCount: 0 };

  page.route("**/api/voice-presets/select", async (route) => {
    state.attemptCount++;

    if (failFirstAttempt && state.attemptCount === 1) {
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

  return state;
}

// Type imports
import type { VoicePreset } from "./factories";
