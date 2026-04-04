/**
 * Story 2.6: Voice Presets by Use Case
 * Component Tests for RecommendationBanner (AC6 - Performance Recommendations)
 *
 * Test ID Format: 2.6-FRONTEND-AC6-XXX
 * Priority: P0 (Critical Gap)
 *
 * Tests the performance recommendation banner that displays after 10+ calls
 * with AI-driven preset suggestions based on call performance metrics.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RecommendationBanner } from "../RecommendationBanner";

describe("RecommendationBanner (AC6 - Performance Recommendations)", () => {
  const mockProps = {
    presetName: "Sales - Rachel",
    improvementPct: 23,
    reasoning: "Higher energy voice correlates with 15% better pickup rates in sales calls",
    onApply: vi.fn(),
    onDismiss: vi.fn(),
  };

  describe("[2.6-FRONTEND-AC6-001][P0] Rendering", () => {
    it("should render banner with all required elements", () => {
      render(<RecommendationBanner {...mockProps} />);

      // Check for main heading
      expect(screen.getByText("Performance-Based Recommendation")).toBeInTheDocument();

      // Check for subtitle
      expect(screen.getByText("Based on your call performance data")).toBeInTheDocument();

      // Check for preset name
      expect(screen.getByText(/"Sales - Rachel"/)).toBeInTheDocument();

      // Check for improvement percentage
      expect(screen.getByText(/23% better pickup rates/)).toBeInTheDocument();

      // Check for reasoning
      expect(screen.getByText(/Reasoning:/)).toBeInTheDocument();
      expect(screen.getByText(mockProps.reasoning)).toBeInTheDocument();
    });

    it("should display dismiss button with correct ARIA label", () => {
      render(<RecommendationBanner {...mockProps} />);

      const dismissButton = screen.getByLabelText("Dismiss recommendation");
      expect(dismissButton).toBeInTheDocument();
      expect(dismissButton).toHaveTextContent("✕");
    });

    it("should display Apply Recommendation and Dismiss buttons", () => {
      render(<RecommendationBanner {...mockProps} />);

      expect(screen.getByRole("button", { name: "Apply Recommendation" })).toBeInTheDocument();
      expect(screen.getAllByRole("button", { name: /dismiss/i })).toHaveLength(2); // One in header, one in actions
    });
  });

  describe("[2.6-FRONTEND-AC6-002][P0] User Interactions", () => {
    it("should call onApply when Apply Recommendation button is clicked", () => {
      render(<RecommendationBanner {...mockProps} />);

      const applyButton = screen.getByRole("button", { name: "Apply Recommendation" });
      fireEvent.click(applyButton);

      expect(mockProps.onApply).toHaveBeenCalledTimes(1);
    });

    it("should call onDismiss when dismiss button in header is clicked", () => {
      render(<RecommendationBanner {...mockProps} />);

      const dismissButton = screen.getByLabelText("Dismiss recommendation");
      fireEvent.click(dismissButton);

      expect(mockProps.onDismiss).toHaveBeenCalledTimes(1);
    });

    it("should call onDismiss when Dismiss button in actions is clicked", () => {
      render(<RecommendationBanner {...mockProps} />);

      const dismissButtons = screen.getAllByRole("button", { name: /dismiss/i });
      // Click the second dismiss button (in actions area)
      fireEvent.click(dismissButtons[1]);

      expect(mockProps.onDismiss).toHaveBeenCalledTimes(1);
    });

    it("should handle multiple dismiss clicks correctly", () => {
      render(<RecommendationBanner {...mockProps} />);

      const dismissButton = screen.getByLabelText("Dismiss recommendation");
      fireEvent.click(dismissButton);
      fireEvent.click(dismissButton);

      expect(mockProps.onDismiss).toHaveBeenCalledTimes(2);
    });
  });

  describe("[2.6-FRONTEND-AC6-003][P1] Dynamic Content", () => {
    it("should display different preset names correctly", () => {
      const customProps = { ...mockProps, presetName: "Support - Alex" };
      render(<RecommendationBanner {...customProps} />);

      expect(screen.getByText(/"Support - Alex"/)).toBeInTheDocument();
      expect(screen.queryByText(/"Sales - Rachel"/)).not.toBeInTheDocument();
    });

    it("should display different improvement percentages correctly", () => {
      const customProps = { ...mockProps, improvementPct: 15 };
      render(<RecommendationBanner {...customProps} />);

      expect(screen.getByText(/15% better pickup rates/)).toBeInTheDocument();
    });

    it("should display different reasoning text correctly", () => {
      const customReasoning = "Calm voice reduces call duration by 20%";
      const customProps = { ...mockProps, reasoning: customReasoning };
      render(<RecommendationBanner {...customProps} />);

      expect(screen.getByText(new RegExp(customReasoning))).toBeInTheDocument();
    });

    it("should handle zero improvement percentage", () => {
      const customProps = { ...mockProps, improvementPct: 0 };
      render(<RecommendationBanner {...customProps} />);

      expect(screen.getByText(/0% better pickup rates/)).toBeInTheDocument();
    });

    it("should handle large improvement percentages", () => {
      const customProps = { ...mockProps, improvementPct: 100 };
      render(<RecommendationBanner {...customProps} />);

      expect(screen.getByText(/100% better pickup rates/)).toBeInTheDocument();
    });
  });

  describe("[2.6-FRONTEND-AC6-004][P1] Accessibility", () => {
    it("should have proper button roles and labels", () => {
      render(<RecommendationBanner {...mockProps} />);

      // Apply button
      const applyButton = screen.getByRole("button", { name: "Apply Recommendation" });
      expect(applyButton).toBeInTheDocument();

      // Dismiss buttons (header X button has explicit ARIA label)
      const dismissButton = screen.getByLabelText("Dismiss recommendation");
      expect(dismissButton).toBeInTheDocument();
    });

    it("should be keyboard navigable", () => {
      render(<RecommendationBanner {...mockProps} />);

      const applyButton = screen.getByRole("button", { name: "Apply Recommendation" });
      const dismissButton = screen.getByLabelText("Dismiss recommendation");

      expect(applyButton).toHaveAttribute("type", "button");
      expect(dismissButton).toHaveAttribute("type", "button");
    });

    it("should maintain focus order", () => {
      render(<RecommendationBanner {...mockProps} />);

      const buttons = screen.getAllByRole("button");
      expect(buttons).toHaveLength(3); // Dismiss (X), Apply, Dismiss (text)
    });
  });

  describe("[2.6-FRONTEND-AC6-005][P2] Edge Cases", () => {
    it("should handle empty preset name", () => {
      const customProps = { ...mockProps, presetName: "" };
      render(<RecommendationBanner {...customProps} />);

      expect(screen.getByText(/""/)).toBeInTheDocument();
    });

    it("should handle very long reasoning text", () => {
      const longReasoning = "A".repeat(500);
      const customProps = { ...mockProps, reasoning: longReasoning };
      render(<RecommendationBanner {...customProps} />);

      expect(screen.getByText(new RegExp(longReasoning))).toBeInTheDocument();
    });

    it("should handle undefined callbacks gracefully", () => {
      const invalidProps = {
        ...mockProps,
        onApply: undefined as unknown as () => void,
        onDismiss: undefined as unknown as () => void,
      };

      // This should not throw during render
      expect(() => render(<RecommendationBanner {...invalidProps} />)).not.toThrow();
    });

    it("should handle special characters in preset name", () => {
      const specialName = "Sales - O'Brien & Associates";
      const customProps = { ...mockProps, presetName: specialName };
      render(<RecommendationBanner {...customProps} />);

      expect(screen.getByText(new RegExp(specialName))).toBeInTheDocument();
    });
  });

  describe("[2.6-FRONTEND-AC6-006][P2] Styling and Layout", () => {
    it("should apply correct CSS classes for blue theme", () => {
      const { container } = render(<RecommendationBanner {...mockProps} />);

      const banner = container.firstChild as HTMLElement;
      expect(banner).toHaveClass({
        "border-blue-500/50": true,
        "bg-blue-500/10": true,
      });
    });

    it("should render dismiss button in correct position", () => {
      const { container } = render(<RecommendationBanner {...mockProps} />);

      const dismissButton = screen.getByLabelText("Dismiss recommendation");
      expect(dismissButton).toHaveClass({ "absolute": true, "right-2": true, "top-2": true });
    });

    it("should render action buttons with correct styles", () => {
      render(<RecommendationBanner {...mockProps} />);

      const applyButton = screen.getByRole("button", { name: "Apply Recommendation" });
      expect(applyButton).toHaveClass({ "bg-blue-600": true, "text-white": true });
    });
  });
});
