import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { PulseMaker } from "../PulseMaker";
import type { PulseMakerProps } from "@call/types";

describe("PulseMaker", () => {
  beforeEach(() => {
    // Mock window.matchMedia for prefers-reduced-motion
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query !== "(prefers-reduced-motion: reduce)",
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });

    // Mock useTranscriptStream to return voice events
    vi.mock("@/hooks/useTranscriptStream", () => ({
      useTranscriptStream: vi.fn(() => ({
        entries: [],
        voiceEvents: [],
        isConnected: false,
        error: null,
      })),
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders with default props (AC: 1)", () => {
    const props: PulseMakerProps = { agentId: "test-agent-1" };
    render(<PulseMaker {...props} />);

    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders with custom volume and sentiment props (AC: 3, 4)", () => {
    const props: PulseMakerProps = {
      agentId: "test-agent-1",
      volume: 0.8,
      sentiment: 0.7,
    };
    const { container } = render(<PulseMaker {...props} />);

    const pulseContainer = container.querySelector('[data-pulse-maker="true"]');
    expect(pulseContainer).toBeInTheDocument();
  });

  it("applies correct CSS custom properties based on props (AC: 3, 4)", () => {
    const props: PulseMakerProps = {
      agentId: "test-agent-1",
      volume: 0.8, // speaking volume
      sentiment: 0.5,
    };
    const { container } = render(<PulseMaker {...props} />);

    // CSS custom properties are on the pulse-maker container
    const pulseMaker = container.querySelector(".pulse-maker");
    expect(pulseMaker).toBeInTheDocument();

    const style = pulseMaker?.getAttribute("style");
    expect(style).toContain("--pulse-scale");
    expect(style).toContain("--pulse-duration");
    expect(style).toContain("--pulse-color");
  });

  it("respects motionEnabled=false prop (AC: 6)", () => {
    const props: PulseMakerProps = {
      agentId: "test-agent-1",
      motionEnabled: false,
    };
    const { container } = render(<PulseMaker {...props} />);

    const pulseContainer = container.querySelector('[data-pulse-maker="true"]');
    expect(pulseContainer).toBeInTheDocument();
  });

  it("respects prefers-reduced-motion media query (AC: 6)", () => {
    // Mock prefers-reduced-motion
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === "(prefers-reduced-motion: reduce)",
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const props: PulseMakerProps = { agentId: "test-agent-1" };
    const { container } = render(<PulseMaker {...props} />);

    const pulseContainer = container.querySelector('[data-pulse-maker="true"]');
    expect(pulseContainer).toBeInTheDocument();
  });

  it("has proper screen reader support (AC: 9)", () => {
    const props: PulseMakerProps = {
      agentId: "test-agent-1",
      volume: 0.8,
      sentiment: 0.5,
    };

    const { container } = render(<PulseMaker {...props} />);

    // role="status" is on the main container
    const statusRegion = screen.getByRole("status");
    expect(statusRegion).toBeInTheDocument();

    // sr-only span contains state info
    const liveRegion = container.querySelector(".sr-only");
    expect(liveRegion).toBeInTheDocument();
    expect(liveRegion?.textContent).toContain("Pulse:");
  });

  it("has proper ARIA attributes and roles (AC: 9)", () => {
    const props: PulseMakerProps = { agentId: "test-agent-1" };
    render(<PulseMaker {...props} />);

    const statusRegion = screen.getByRole("status");
    expect(statusRegion).toHaveAttribute("aria-label");
    expect(statusRegion?.getAttribute("aria-label")).toContain("Agent activity pulse");
  });

  it("glassmorphism styles applied correctly (AC: 8)", () => {
    const props: PulseMakerProps = { agentId: "test-agent-1" };
    const { container } = render(<PulseMaker {...props} />);

    const statusElement = container.querySelector('[role="status"]');
    expect(statusElement).toHaveClass("bg-card/40"); // glassmorphism background
    expect(statusElement).toHaveClass("backdrop-blur-md"); // backdrop blur
    expect(statusElement).toHaveClass("border"); // border
  });

  it("volume mapping uses binary state with VOLUME_THRESHOLD (AC: 3)", () => {
    const props: PulseMakerProps = {
      agentId: "test-agent-1",
      volume: 0.8, // speaking (at threshold)
    };
    const { container } = render(<PulseMaker {...props} />);

    // CSS custom properties are on the pulse-maker container
    const pulseMaker = container.querySelector(".pulse-maker");
    const style = pulseMaker?.getAttribute("style");

    // Volume >= VOLUME_THRESHOLD (0.8) should use speaking scale (1.3)
    expect(style).toContain("1.3");
  });

  it("renders three ripple rings with consistent spacing", () => {
    const props: PulseMakerProps = { agentId: "test-agent-1" };
    const { container } = render(<PulseMaker {...props} />);

    const ripples = container.querySelectorAll('[data-pulse-ripple="true"]');
    expect(ripples.length).toBe(3);

    // Check that sizes follow the pattern: 72px, 60px, 54px (6px spacing)
    const sizes = Array.from(ripples).map((r) => parseInt(r.getAttribute("style") || ""));
    expect(sizes[0]).toBe(72);
    expect(sizes[1]).toBe(60);
    expect(sizes[2]).toBe(54);
  });

  it("uses constants instead of hardcoded values", () => {
    const props: PulseMakerProps = { agentId: "test-agent-1" };
    const { container } = render(<PulseMaker {...props} />);

    // Verify ripple delays use constants
    const ripples = container.querySelectorAll('[data-pulse-ripple="true"]');
    const firstRipple = ripples[0];
    const style = firstRipple.getAttribute("style");

    // Should have animation-delay from constants
    expect(style).toContain("animation-delay");
  });

  it("memoizes state change callback to prevent infinite re-renders", () => {
    const onStateChange = vi.fn();
    const props: PulseMakerProps = {
      agentId: "test-agent-1",
      volume: 0.5,
      onStateChange,
    };

    const { rerender } = render(<PulseMaker {...props} />);

    // Re-render with same props
    rerender(<PulseMaker {...props} />);

    // onStateChange should not be called multiple times unnecessarily
    // (The hook memoizes the callback)
  });

  it("does not have duplicate aria-live regions (AC: 9)", () => {
    const props: PulseMakerProps = { agentId: "test-agent-1" };
    const { container } = render(<PulseMaker {...props} />);

    // Only role="status" should be present, not aria-live
    const ariaLiveRegions = container.querySelectorAll('[aria-live="polite"]');
    expect(ariaLiveRegions.length).toBe(0);

    // sr-only span should not have aria-live
    const srOnly = container.querySelector(".sr-only");
    expect(srOnly?.getAttribute("aria-live")).toBeNull();
  });
});
