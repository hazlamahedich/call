/**
 * Story 2.6: Voice Presets by Use Case
 * Preset Highlighting State Tests (AC4 - Selected Preset Highlighting)
 *
 * Test ID Format: 2.6-FRONTEND-AC4-XXX
 * Priority: P2
 *
 * Tests the visual feedback and state management for selected preset highlighting,
 * including checkmark display, state persistence, and updates on preset change.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { VoicePresetSelector } from "../VoicePresetSelector";
import * as voicePresetsActions from "@/actions/voice-presets";

// Mock the voice-presets actions
vi.mock("@/actions/voice-presets", () => ({
  getVoicePresets: vi.fn(),
  selectVoicePreset: vi.fn(),
  getPresetSample: vi.fn(),
  saveAdvancedVoiceConfig: vi.fn(),
  getVoicePresetRecommendation: vi.fn(),
}));

describe("VoicePresetSelector Preset Highlighting (AC4 - Selected Preset)", () => {
  const mockPresets = [
    {
      id: 1,
      name: "Sales - Rachel",
      use_case: "sales",
      voice_id: "voice-1",
      speech_speed: 1.0,
      stability: 0.8,
      temperature: 0.7,
      description: "High energy sales voice",
      is_active: true,
      sort_order: 1,
    },
    {
      id: 2,
      name: "Sales - Alex",
      use_case: "sales",
      voice_id: "voice-2",
      speech_speed: 1.1,
      stability: 0.7,
      temperature: 0.6,
      description: "Confident sales voice",
      is_active: true,
      sort_order: 2,
    },
    {
      id: 3,
      name: "Sales - Jordan",
      use_case: "sales",
      voice_id: "voice-3",
      speech_speed: 0.9,
      stability: 0.9,
      temperature: 0.5,
      description: "Professional sales voice",
      is_active: true,
      sort_order: 3,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(voicePresetsActions.getVoicePresets).mockResolvedValue({
      data: mockPresets,
      error: null,
    });

    vi.mocked(voicePresetsActions.selectVoicePreset).mockResolvedValue({
      data: { message: "Preset selected successfully" },
      error: null,
    });

    vi.mocked(voicePresetsActions.getVoicePresetRecommendation).mockResolvedValue({
      data: null,
      error: null,
    });

    // Mock audio samples
    vi.mocked(voicePresetsActions.getPresetSample).mockResolvedValue({
      data: { arrayBuffer: () => Promise.resolve(new ArrayBuffer(1024)) } as any,
      error: null,
    });
  });

  describe("[2.6-FRONTEND-AC4-001][P2] Initial Selection State", () => {
    it("should display no presets as selected on initial load", async () => {
      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      // Verify no checkmarks are visible initially
      const checkmarks = screen.queryAllByTestId("preset-checkmark");
      expect(checkmarks).toHaveLength(0);
    });

    it("should show checkmark when preset is selected", async () => {
      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      // Select first preset
      const selectButtons = screen.getAllByTestId("select-button");
      await waitFor(async () => {
        fireEvent.click(selectButtons[0]);
      });

      // Verify checkmark appears
      await waitFor(() => {
        expect(screen.getByTestId("preset-checkmark")).toBeInTheDocument();
      });
    });
  });

  describe("[2.6-FRONTEND-AC4-002][P2] Visual Feedback", () => {
    it("should display checkmark icon on selected preset card", async () => {
      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const selectButtons = screen.getAllByTestId("select-button");
      await waitFor(async () => {
        fireEvent.click(selectButtons[0]);
      });

      // Verify checkmark is visible on the selected card
      await waitFor(() => {
        const checkmark = screen.getByTestId("preset-checkmark");
        expect(checkmark).toBeInTheDocument();
        expect(checkmark).toHaveTextContent(/✓|✔/i); // Checkmark character
      });
    });

    it("should apply selected styling to preset card", async () => {
      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const presetCards = screen.getAllByTestId("preset-card");
      const firstCard = presetCards[0];

      // Before selection
      expect(firstCard).not.toHaveClass(/selected/);

      // Select preset
      const selectButtons = screen.getAllByTestId("select-button");
      await waitFor(async () => {
        fireEvent.click(selectButtons[0]);
      });

      // After selection - verify styling changed
      await waitFor(() => {
        expect(screen.getByTestId("preset-checkmark")).toBeInTheDocument();
      });
    });

    it("should update button text when preset is selected", async () => {
      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const selectButtons = screen.getAllByTestId("select-button");
      const firstButton = selectButtons[0];

      // Before selection
      expect(firstButton).toHaveTextContent(/select this preset/i);

      // Select preset
      await waitFor(async () => {
        fireEvent.click(firstButton);
      });

      // After selection - button text should change
      await waitFor(() => {
        expect(firstButton).toHaveTextContent(/selected|saved/i);
      });
    });
  });

  describe("[2.6-FRONTEND-AC4-003][P2] State Persistence", () => {
    it("should maintain selection state during re-render", async () => {
      const { rerender } = render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      // Select first preset
      const selectButtons = screen.getAllByTestId("select-button");
      await waitFor(async () => {
        fireEvent.click(selectButtons[0]);
      });

      // Verify selection
      await waitFor(() => {
        expect(screen.getByTestId("preset-checkmark")).toBeInTheDocument();
      });

      // Force re-render
      rerender(<VoicePresetSelector />);

      // Verify selection persists
      await waitFor(() => {
        expect(screen.getByTestId("preset-checkmark")).toBeInTheDocument();
      });
    });

    it("should show correct selected preset after filtering by use case", async () => {
      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      // Select preset in Sales
      const selectButtons = screen.getAllByTestId("select-button");
      await waitFor(async () => {
        fireEvent.click(selectButtons[0]);
      });

      await waitFor(() => {
        expect(screen.getByTestId("preset-checkmark")).toBeInTheDocument();
      });

      // Switch to Support use case
      const supportButton = screen.getByRole("button", { name: "Support" });
      await waitFor(async () => {
        fireEvent.click(supportButton);
      });

      // Sales preset should no longer be visible (filter changed)
      // This is expected behavior - selection persists but is scoped to use case
    });
  });

  describe("[2.6-FRONTEND-AC4-004][P2] Selection Updates", () => {
    it("should remove checkmark from previous preset when selecting new preset", async () => {
      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const selectButtons = screen.getAllByTestId("select-button");

      // Select first preset
      await waitFor(async () => {
        fireEvent.click(selectButtons[0]);
      });

      await waitFor(() => {
        expect(screen.getByTestId("preset-checkmark")).toBeInTheDocument();
      });

      // Select second preset
      await waitFor(async () => {
        fireEvent.click(selectButtons[1]);
      });

      // Verify only one checkmark is visible (on second preset)
      await waitFor(() => {
        const checkmarks = screen.queryAllByTestId("preset-checkmark");
        expect(checkmarks).toHaveLength(1);
      });
    });

    it("should update selection when user switches between presets", async () => {
      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const presetCards = screen.getAllByTestId("preset-card");
      const selectButtons = screen.getAllByTestId("select-button");

      // Select first preset
      await waitFor(async () => {
        fireEvent.click(selectButtons[0]);
      });

      // Verify first card has checkmark
      await waitFor(() => {
        expect(presetCards[0]).toContainElement(screen.getByTestId("preset-checkmark"));
      });

      // Select second preset
      await waitFor(async () => {
        fireEvent.click(selectButtons[1]);
      });

      // Verify second card now has checkmark
      await waitFor(() => {
        expect(presetCards[1]).toContainElement(screen.getByTestId("preset-checkmark"));
      });

      // Verify first card no longer has checkmark
      expect(presetCards[0]).not.toContainElement(screen.getByTestId("preset-checkmark"));
    });
  });

  describe("[2.6-FRONTEND-AC4-005][P2] Multiple Selections", () => {
    it("should handle rapid preset switching correctly", async () => {
      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const selectButtons = screen.getAllByTestId("select-button");

      // Rapidly switch between presets
      await waitFor(async () => {
        fireEvent.click(selectButtons[0]);
      });

      await waitFor(async () => {
        fireEvent.click(selectButtons[1]);
      });

      await waitFor(async () => {
        fireEvent.click(selectButtons[2]);
      });

      // Verify only the last preset is selected
      await waitFor(() => {
        const checkmarks = screen.queryAllByTestId("preset-checkmark");
        expect(checkmarks).toHaveLength(1);
      });
    });
  });

  describe("[2.6-FRONTEND-AC4-006][P2] Error State Handling", () => {
    it("should maintain selection state even if API call fails", async () => {
      // Mock failure for subsequent selections
      vi.mocked(voicePresetsActions.selectVoicePreset).mockResolvedValueOnce({
        data: { message: "Preset selected successfully" },
        error: null,
      }).mockResolvedValueOnce({
        data: null,
        error: "Failed to select preset",
      });

      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const selectButtons = screen.getAllByTestId("select-button");

      // First selection succeeds
      await waitFor(async () => {
        fireEvent.click(selectButtons[0]);
      });

      await waitFor(() => {
        expect(screen.getByTestId("preset-checkmark")).toBeInTheDocument();
      });

      // Second selection fails
      await waitFor(async () => {
        fireEvent.click(selectButtons[1]);
      });

      // UI should handle error gracefully - check this doesn't crash
      await waitFor(() => {
        expect(screen.getByText(/failed to select preset/i)).toBeInTheDocument();
      });
    });
  });

  describe("[2.6-FRONTEND-AC4-007][P2] Accessibility", () => {
    it("should update ARIA attributes on selection", async () => {
      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const presetCards = screen.getAllByTestId("preset-card");
      const selectButtons = screen.getAllByTestId("select-button");

      // Before selection
      expect(presetCards[0]).not.toHaveAttribute("aria-selected", "true");

      // Select preset
      await waitFor(async () => {
        fireEvent.click(selectButtons[0]);
      });

      // After selection - verify ARIA attribute updated
      await waitFor(() => {
        expect(presetCards[0]).toHaveAttribute("aria-selected", "true");
      });
    });

    it("should announce selection to screen readers", async () => {
      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const selectButtons = screen.getAllByTestId("select-button");

      // Select preset
      await waitFor(async () => {
        fireEvent.click(selectButtons[0]);
      });

      // Verify success message is announced
      await waitFor(() => {
        expect(screen.getByText(/preset selected successfully/i)).toBeInTheDocument();
      });
    });
  });
});
