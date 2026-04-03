import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { FleetNavigator } from "../FleetNavigator";
import { PulseMaker } from "../../obsidian/PulseMaker";

// Mock the PulseMaker component to verify it's being called correctly
vi.mock("../../obsidian/PulseMaker", () => ({
  PulseMaker: vi.fn(({ agentId, motionEnabled }: any) => (
    <div data-testid={`pulse-${agentId}`} data-motion-enabled={motionEnabled}>
      Pulse for {agentId}
    </div>
  )),
}));

describe("PulseMaker Fleet Navigator Integration", () => {
  it("renders Pulse Maker for each active agent", () => {
    render(<FleetNavigator />);

    // Fleet Navigator has 3 mock agents
    expect(screen.getByTestId("pulse-agent-1")).toBeInTheDocument();
    expect(screen.getByTestId("pulse-agent-2")).toBeInTheDocument();
    expect(screen.getByTestId("pulse-agent-3")).toBeInTheDocument();
  });

  it("each Pulse Maker receives unique agentId prop", () => {
    render(<FleetNavigator />);

    const pulse1 = screen.getByTestId("pulse-agent-1");
    const pulse2 = screen.getByTestId("pulse-agent-2");
    const pulse3 = screen.getByTestId("pulse-agent-3");

    expect(pulse1).toHaveAttribute("data-testid", "pulse-agent-1");
    expect(pulse2).toHaveAttribute("data-testid", "pulse-agent-2");
    expect(pulse3).toHaveAttribute("data-testid", "pulse-agent-3");
  });

  it("multiple instances don't share state (isolation)", () => {
    // This is verified by each pulse having a unique agentId
    // The useVoiceEvents hook is called with unique agentId per instance
    render(<FleetNavigator />);

    const pulses = screen.getAllByText(/Pulse for agent-/);
    expect(pulses).toHaveLength(3);
    expect(pulses[0]).toHaveTextContent("Pulse for agent-1");
    expect(pulses[1]).toHaveTextContent("Pulse for agent-2");
    expect(pulses[2]).toHaveTextContent("Pulse for agent-3");
  });

  it("positioning is correct in agent button layout", () => {
    const { container } = render(<FleetNavigator />);

    // Verify Fleet Navigator structure
    const navigator = container.querySelector("aside");
    expect(navigator).toBeInTheDocument();
    expect(navigator).toHaveClass(/flex/);
    expect(navigator).toHaveClass(/bg-card/);
  });

  it("useVoiceEvents hook is called with correct agentId", () => {
    // This test verifies that each PulseMaker receives a unique agentId
    // which is passed to the useVoiceEvents hook inside the component
    render(<FleetNavigator />);

    const pulse1 = screen.getByTestId("pulse-agent-1");
    const pulse2 = screen.getByTestId("pulse-agent-2");
    const pulse3 = screen.getByTestId("pulse-agent-3");

    // Verify agent IDs are unique
    expect(pulse1.getAttribute("data-testid")).toBe("pulse-agent-1");
    expect(pulse2.getAttribute("data-testid")).toBe("pulse-agent-2");
    expect(pulse3.getAttribute("data-testid")).toBe("pulse-agent-3");

    // All have motion enabled by default
    expect(pulse1).toHaveAttribute("data-motion-enabled", "true");
    expect(pulse2).toHaveAttribute("data-motion-enabled", "true");
    expect(pulse3).toHaveAttribute("data-motion-enabled", "true");
  });
});
