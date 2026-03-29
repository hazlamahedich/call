import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { TelemetryStreamObsidian } from "../telemetry-stream";
import { createTranscriptEntry } from "@/test/factories/transcript";

const originalScrollIntoView = HTMLElement.prototype.scrollIntoView;

beforeEach(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  HTMLElement.prototype.scrollIntoView = originalScrollIntoView;
});

describe("[1.4-AC1][TelemetryStreamObsidian] — Transcript feed component", () => {
  it("[1.4-UNIT-033][P1] Given entries with roles badges, When rendered, Then AI/LEAD/HUMAN labels appear", () => {
    const entries = [
      createTranscriptEntry({ role: "assistant-ai", text: "Opening pitch" }),
      createTranscriptEntry({ role: "lead", text: "Tell me more" }),
      createTranscriptEntry({ role: "assistant-human", text: "Taking over" }),
    ];

    render(<TelemetryStreamObsidian entries={entries} />);

    expect(screen.getByText("Opening pitch")).toBeInTheDocument();
    expect(screen.getByText("Tell me more")).toBeInTheDocument();
    expect(screen.getByText("Taking over")).toBeInTheDocument();

    expect(screen.getByText("AI")).toBeInTheDocument();
    expect(screen.getByText("LEAD")).toBeInTheDocument();
    expect(screen.getByText("HUMAN")).toBeInTheDocument();
  });

  it("[1.4-UNIT-034][P1] Given entries with timestamps, When rendered, Then formatted times appear", () => {
    render(
      <TelemetryStreamObsidian
        entries={[
          createTranscriptEntry({
            timestamp: new Date("2026-03-29T10:00:00").getTime(),
          }),
          createTranscriptEntry({
            timestamp: new Date("2026-03-29T10:01:00").getTime(),
          }),
          createTranscriptEntry({
            timestamp: new Date("2026-03-29T10:02:00").getTime(),
          }),
        ]}
      />,
    );

    expect(screen.getByText("10:00:00")).toBeInTheDocument();
    expect(screen.getByText("10:01:00")).toBeInTheDocument();
    expect(screen.getByText("10:02:00")).toBeInTheDocument();
  });

  it("[1.4-UNIT-035][P1] Given AI entry, When rendered, Then emerald role color is applied", () => {
    render(
      <TelemetryStreamObsidian
        entries={[createTranscriptEntry({ role: "assistant-ai" })]}
      />,
    );
    const aiBadge = screen.getByText("AI");
    expect(aiBadge.className).toContain("text-neon-emerald");
  });

  it("[1.4-UNIT-036][P1] Given lead entry, When rendered, Then blue role color is applied", () => {
    render(
      <TelemetryStreamObsidian
        entries={[createTranscriptEntry({ role: "lead" })]}
      />,
    );
    const leadBadge = screen.getByText("LEAD");
    expect(leadBadge.className).toContain("text-neon-blue");
  });

  it("[1.4-UNIT-037][P1] Given onScrollBottom callback, When entries change, Then callback is invoked", () => {
    const onScrollBottom = vi.fn();
    const initialEntries = [createTranscriptEntry()];
    const { rerender } = render(
      <TelemetryStreamObsidian
        entries={initialEntries}
        onScrollBottom={onScrollBottom}
      />,
    );

    expect(onScrollBottom).toHaveBeenCalled();

    const updatedEntries = [
      ...initialEntries,
      createTranscriptEntry({ text: "New entry" }),
    ];
    rerender(
      <TelemetryStreamObsidian
        entries={updatedEntries}
        onScrollBottom={onScrollBottom}
      />,
    );
    expect(onScrollBottom).toHaveBeenCalledTimes(2);
  });

  it("[1.4-UNIT-038][P2] Given empty entries, When rendered, Then container has card styling", () => {
    const { container } = render(<TelemetryStreamObsidian entries={[]} />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("bg-card");
    expect(wrapper.className).toContain("border-border");
  });

  it("[1.4-UNIT-039][P2] Given unknown role entry, When rendered, Then fallback badge appears", () => {
    render(
      <TelemetryStreamObsidian
        entries={[
          createTranscriptEntry({
            role: "unknown-role" as any,
            text: "Mystery",
          }),
        ]}
      />,
    );
    expect(screen.getByText("UNKNOWN-ROLE")).toBeInTheDocument();
  });

  it("[1.4-UNIT-040][P1] Given entries, When rendered, Then design token classes are applied", () => {
    const { container } = render(
      <TelemetryStreamObsidian entries={[createTranscriptEntry()]} />,
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("bg-card");
    expect(wrapper.className).toContain("border-border");
    expect(wrapper.className).toContain("rounded-lg");
  });

  it("[1.4-UNIT-041][P1] Given TelemetryStream component, When audited, Then no WCAG violations", async () => {
    const { container } = render(
      <TelemetryStreamObsidian
        entries={[
          createTranscriptEntry(),
          createTranscriptEntry({ role: "lead" }),
        ]}
      />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
