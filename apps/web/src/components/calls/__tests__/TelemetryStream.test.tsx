import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";

const mockUseTranscriptStream = vi.fn();

vi.mock("@/hooks/useTranscriptStream", () => ({
  useTranscriptStream: (...args: unknown[]) => mockUseTranscriptStream(...args),
}));

function mockMatchMedia() {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockReturnValue({
      matches: false,
      addListener: vi.fn(),
      removeListener: vi.fn(),
    }),
  });
}

describe("[2.2][TelemetryStream] — Live transcript display component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseTranscriptStream.mockReturnValue({
      entries: [],
      isConnected: false,
      error: null,
    });
    mockMatchMedia();
  });

  it("[2.2-UNIT-700][P0] Given null callId, When rendered, Then nothing is rendered", async () => {
    const { TelemetryStream } = await import("../TelemetryStream");
    const { container } = render(<TelemetryStream callId={null} />);
    expect(container.innerHTML).toBe("");
  });

  it("[2.2-UNIT-701][P0] Given connected state, When rendered, Then Connected status is shown", async () => {
    mockUseTranscriptStream.mockReturnValue({
      entries: [],
      isConnected: true,
      error: null,
    });
    const { TelemetryStream } = await import("../TelemetryStream");
    render(<TelemetryStream callId={42} />);
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("[2.2-UNIT-702][P0] Given disconnected state, When rendered, Then Disconnected status is shown", async () => {
    mockUseTranscriptStream.mockReturnValue({
      entries: [],
      isConnected: false,
      error: null,
    });
    const { TelemetryStream } = await import("../TelemetryStream");
    render(<TelemetryStream callId={42} />);
    expect(screen.getByText("Disconnected")).toBeInTheDocument();
  });

  it("[2.2-UNIT-703][P0] Given entries, When rendered, Then transcript text is displayed", async () => {
    mockUseTranscriptStream.mockReturnValue({
      entries: [
        {
          id: 1,
          callId: 42,
          role: "assistant-ai",
          text: "Hello, how can I help?",
          startTime: 100,
          endTime: 200,
          confidence: 0.95,
          receivedAt: "2025-01-01T00:00:00Z",
          timestamp: 100,
        },
        {
          id: 2,
          callId: 42,
          role: "lead",
          text: "I'm not interested",
          startTime: 300,
          endTime: 400,
          confidence: 0.8,
          receivedAt: "2025-01-01T00:00:01Z",
          timestamp: 300,
        },
      ],
      isConnected: true,
      error: null,
    });
    const { TelemetryStream } = await import("../TelemetryStream");
    render(<TelemetryStream callId={42} />);
    expect(screen.getByText("Hello, how can I help?")).toBeInTheDocument();
    expect(screen.getByText("I'm not interested")).toBeInTheDocument();
  });

  it("[2.2-UNIT-704][P1] Given entries with different roles, When rendered, Then role prefixes are shown", async () => {
    mockUseTranscriptStream.mockReturnValue({
      entries: [
        {
          id: 1,
          callId: 42,
          role: "assistant-ai",
          text: "AI says hi",
          startTime: 100,
          endTime: 200,
          confidence: null,
          receivedAt: "2025-01-01T00:00:00Z",
          timestamp: 100,
        },
        {
          id: 2,
          callId: 42,
          role: "assistant-human",
          text: "Human says hi",
          startTime: 300,
          endTime: 400,
          confidence: null,
          receivedAt: "2025-01-01T00:00:01Z",
          timestamp: 300,
        },
        {
          id: 3,
          callId: 42,
          role: "lead",
          text: "Lead says hi",
          startTime: 500,
          endTime: 600,
          confidence: null,
          receivedAt: "2025-01-01T00:00:02Z",
          timestamp: 500,
        },
      ],
      isConnected: true,
      error: null,
    });
    const { TelemetryStream } = await import("../TelemetryStream");
    render(<TelemetryStream callId={42} />);
    expect(screen.getAllByText("[AI]").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("[Human]").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("[Lead]").length).toBeGreaterThanOrEqual(1);
  });

  it("[2.2-UNIT-705][P1] Given error state, When rendered, Then error is shown with alert role", async () => {
    mockUseTranscriptStream.mockReturnValue({
      entries: [],
      isConnected: false,
      error: "WebSocket connection error",
    });
    const { TelemetryStream } = await import("../TelemetryStream");
    render(<TelemetryStream callId={42} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("WebSocket connection error");
  });

  it("[2.2-UNIT-706][P1] Given empty state with no error, When rendered, Then waiting message is shown", async () => {
    mockUseTranscriptStream.mockReturnValue({
      entries: [],
      isConnected: true,
      error: null,
    });
    const { TelemetryStream } = await import("../TelemetryStream");
    render(<TelemetryStream callId={42} />);
    expect(
      screen.getByText("Waiting for transcript data..."),
    ).toBeInTheDocument();
  });

  it("[2.2-UNIT-707][P2] Given Live Transcript header, When rendered, Then heading text is displayed", async () => {
    const { TelemetryStream } = await import("../TelemetryStream");
    render(<TelemetryStream callId={42} />);
    expect(screen.getByText("Live Transcript")).toBeInTheDocument();
  });

  it("[2.2-UNIT-708][P2] Given connected state, When rendered, Then green indicator dot is shown", async () => {
    mockUseTranscriptStream.mockReturnValue({
      entries: [],
      isConnected: true,
      error: null,
    });
    const { TelemetryStream } = await import("../TelemetryStream");
    const { container } = render(<TelemetryStream callId={42} />);
    const dot = container.querySelector('span[style*="border-radius"]');
    expect(dot).toBeInTheDocument();
  });

  it("[2.2-UNIT-709][P1] Given TelemetryStream, When axe audit runs, Then no WCAG violations", async () => {
    mockUseTranscriptStream.mockReturnValue({
      entries: [
        {
          id: 1,
          callId: 42,
          role: "assistant-ai",
          text: "Hello",
          startTime: 100,
          endTime: 200,
          confidence: 0.9,
          receivedAt: "2025-01-01T00:00:00Z",
          timestamp: 100,
        },
      ],
      isConnected: true,
      error: null,
    });
    const { TelemetryStream } = await import("../TelemetryStream");
    const { container } = render(<TelemetryStream callId={42} />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });

  it("[2.2-UNIT-710][P1] Given error state, When axe audit runs, Then no WCAG violations on error alert", async () => {
    mockUseTranscriptStream.mockReturnValue({
      entries: [],
      isConnected: false,
      error: "Connection lost",
    });
    const { TelemetryStream } = await import("../TelemetryStream");
    const { container } = render(<TelemetryStream callId={42} />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
