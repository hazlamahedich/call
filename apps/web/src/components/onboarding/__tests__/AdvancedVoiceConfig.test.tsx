"""Tests for Advanced Mode component and functionality.

[2.6-ADVANCED-001] Test sliders update local state
[2.6-ADVANCED-002] Test save persists custom config
[2.6-ADVANCED-003] Test warning displays when advanced mode active
"""

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AdvancedVoiceConfig, type AdvancedConfig } from "../AdvancedVoiceConfig";

describe("AdvancedVoiceConfig", () => {
  const mockOnSave = jest.fn();

  beforeEach(() => {
    mockOnSave.mockClear();
  });

  test("[2.6-ADVANCED-001] Given advanced mode, When adjusting sliders, Then local state updates", async () => {
    const user = userEvent.setup();

    render(<AdvancedVoiceConfig onSave={mockOnSave} />);

    // Find speech speed slider
    const speechSpeedSlider = screen.getByLabelText("Speech Speed");
    expect(speechSpeedSlider).toBeInTheDocument();

    // Get initial value
    const initialValue = screen.getByText("1.00x");
    expect(initialValue).toBeInTheDocument();

    // Adjust slider
    await user.click(speechSpeedSlider, { target: { value: "1.5" } });

    // Value should update
    await waitFor(() => {
      expect(screen.getByText("1.50x")).toBeInTheDocument();
    });
  });

  test("[2.6-ADVANCED-002] Given custom config, When clicking save, Then config persists", async () => {
    const user = userEvent.setup();
    const mockSave = jest.fn().mockResolvedValue(undefined);

    render(<AdvancedVoiceConfig onSave={mockSave} />);

    // Adjust values
    const stabilitySlider = screen.getByLabelText("Stability");
    const temperatureSlider = screen.getByLabelText("Temperature (Expressiveness)");

    await user.click(stabilitySlider, { target: { value: "0.9" } });
    await user.click(temperatureSlider, { target: { value: "0.8" } });

    // Click save
    const saveButton = screen.getByRole("button", { name: /save configuration/i });
    await user.click(saveButton);

    // Verify onSave was called with correct config
    await waitFor(() => {
      expect(mockSave).toHaveBeenCalledWith({
        speech_speed: 1.0,
        stability: 0.9,
        temperature: 0.8,
      });
    });

    // Should show saved message
    await waitFor(() => {
      expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
    });
  });

  test("[2.6-ADVANCED-003] Given advanced mode enabled, When component renders, Then warning displays", () => {
    render(<AdvancedVoiceConfig onSave={mockOnSave} />);

    // Warning message should be visible
    expect(
      screen.getByText(/Advanced Settings Warning/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Custom settings may not sound optimal/i)
    ).toBeInTheDocument();
  });

  test("[2.6-ADVANCED-004] Given sliders at edges, When values are min/max, Then display correctly", () => {
    render(
      <AdvancedVoiceConfig
        onSave={mockOnSave}
        currentConfig={{
          speech_speed: 0.5,
          stability: 1.0,
          temperature: 0.0,
        }}
      />
    );

    // Min speech speed
    expect(screen.getByText("0.50x")).toBeInTheDocument();

    // Max stability
    expect(screen.getByText("1.00")).toBeInTheDocument();

    // Min temperature
    expect(screen.getByText("0.00")).toBeInTheDocument();
  });

  test("[2.6-ADVANCED-005] Given custom config, When clicking reset, Then values revert to defaults", async () => {
    const user = userEvent.setup();

    render(
      <AdvancedVoiceConfig
        onSave={mockOnSave}
        currentConfig={{
          speech_speed: 1.8,
          stability: 0.4,
          temperature: 0.9,
        }}
      />
    );

    // Verify custom values are shown
    expect(screen.getByText("1.80x")).toBeInTheDocument();

    // Click reset
    const resetButton = screen.getByRole("button", { name: /reset to defaults/i });
    await user.click(resetButton);

    // Values should revert to defaults
    expect(screen.getByText("1.00x")).toBeInTheDocument();
    expect(screen.getByText("0.80")).toBeInTheDocument();
    expect(screen.getByText("0.70")).toBeInTheDocument();
  });

  test("[2.6-ADVANCED-006] Given save in progress, When saving, Then button shows loading state", async () => {
    const user = userEvent.setup();
    let resolveSave: (value: void) => void;

    const mockSave = new Promise<void>((resolve) => {
      resolveSave = resolve;
    });

    render(<AdvancedVoiceConfig onSave={() => mockSave} />);

    const saveButton = screen.getByRole("button", { name: /save configuration/i });
    await user.click(saveButton);

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText("Saving...")).toBeInTheDocument();
    });

    // Resolve save
    resolveSave!();

    // Should show saved state
    await waitFor(() => {
      expect(screen.getByText("Saved!")).toBeInTheDocument();
    });
  });

  test("[2.6-ADVANCED-007] Given save error, When save fails, Then error message displays", async () => {
    const user = userEvent.setup();
    const mockSave = jest.fn().mockRejectedValue(new Error("Network error"));

    render(<AdvancedVoiceConfig onSave={mockSave} />);

    const saveButton = screen.getByRole("button", { name: /save configuration/i });
    await user.click(saveButton);

    // Error message should appear
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  test("[2.6-ADVANCED-008] Given disabled prop, When disabled, Then sliders are not interactive", () => {
    render(<AdvancedVoiceConfig onSave={mockOnSave} disabled={true} />);

    const speechSpeedSlider = screen.getByLabelText("Speech Speed");
    const saveButton = screen.getByRole("button", { name: /save configuration/i });

    expect(speechSpeedSlider).toBeDisabled();
    expect(saveButton).toBeDisabled();
  });
});
