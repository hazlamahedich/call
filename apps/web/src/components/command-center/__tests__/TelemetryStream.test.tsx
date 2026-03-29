import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { TelemetryStream } from "../TelemetryStream";

describe("[1.4-AC1][TelemetryStream] — Base telemetry log feed with design system primitives", () => {
  beforeEach(() => {
    HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  it("[1.4-UNIT-110][P0] Given TelemetryStream, When rendered, Then Live Telemetry heading is displayed", () => {
    render(<TelemetryStream />);
    expect(screen.getByText("Live Telemetry")).toBeInTheDocument();
  });

  it("[1.4-UNIT-111][P1] Given TelemetryStream, When rendered, Then log entries are displayed", () => {
    render(<TelemetryStream />);
    expect(screen.getByText(/Good morning!/)).toBeInTheDocument();
    expect(screen.getByText(/Not interested/)).toBeInTheDocument();
  });

  it("[1.4-UNIT-112][P1] Given TelemetryStream, When rendered, Then role tags are shown", () => {
    render(<TelemetryStream />);
    const aiTags = screen.getAllByText("AI");
    expect(aiTags.length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("LEAD").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("SYS").length).toBeGreaterThanOrEqual(1);
  });

  it("[1.4-UNIT-113][P1] Given TelemetryStream, When rendered, Then alert entries show Critical badge", () => {
    render(<TelemetryStream />);
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("[1.4-UNIT-114][P1] Given sentiment=positive, When rendered, Then emerald sentiment bar is applied", () => {
    const { container } = render(<TelemetryStream sentiment="positive" />);
    const bar = container.querySelector(".bg-neon-emerald.h-1");
    expect(bar).toBeInTheDocument();
  });

  it("[1.4-UNIT-115][P1] Given sentiment=hostile, When rendered, Then crimson sentiment bar is applied", () => {
    const { container } = render(<TelemetryStream sentiment="hostile" />);
    const bar = container.querySelector(".bg-neon-crimson.h-1");
    expect(bar).toBeInTheDocument();
  });

  it("[1.4-UNIT-116][P1] Given sentiment=neutral, When rendered, Then blue sentiment bar is applied", () => {
    const { container } = render(<TelemetryStream sentiment="neutral" />);
    const bar = container.querySelector(".bg-neon-blue.h-1");
    expect(bar).toBeInTheDocument();
  });

  it("[1.4-UNIT-117][P1] Given TelemetryStream, When rendered, Then Intervene button is present", () => {
    render(<TelemetryStream />);
    expect(screen.getByText("Intervene")).toBeInTheDocument();
  });

  it("[1.4-UNIT-118][P2] Given TelemetryStream uses design system, When rendered, Then Card component wraps content", () => {
    const { container } = render(<TelemetryStream />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain("bg-card");
  });

  it("[1.4-UNIT-119][P2] Given custom className, When rendered, Then className is merged", () => {
    const { container } = render(<TelemetryStream className="custom-stream" />);
    expect((container.firstChild as HTMLElement).className).toContain(
      "custom-stream",
    );
  });

  it("[1.4-UNIT-120][P1] Given TelemetryStream, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(<TelemetryStream />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
