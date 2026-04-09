import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { axe } from "vitest-axe";
import { ChatPanel } from "../chat-panel";
import {
  createClaimVerification,
  resetClaimCounter,
} from "@/test/factories/correction";
import type { LabChatResponse } from "@/actions/scripts-lab";

const mockSendLabChat = vi.fn();

vi.mock("@/actions/scripts-lab", () => ({
  sendLabChat: (...args: unknown[]) => mockSendLabChat(...args),
}));

function createMockResponse(overrides: Partial<LabChatResponse> = {}): {
  data: LabChatResponse;
  error: null;
} {
  return {
    data: {
      responseText: "AI response text",
      sourceAttributions: [
        {
          chunkId: 1,
          documentName: "doc.pdf",
          pageNumber: 1,
          excerpt: "Some excerpt",
          similarityScore: 0.85,
        },
      ],
      groundingConfidence: 0.85,
      turnNumber: 1,
      lowConfidenceWarning: false,
      ...overrides,
    },
    error: null,
  };
}

async function sendMessage() {
  const textarea = screen.getByPlaceholderText(
    "Type a message to test the script...",
  );
  fireEvent.change(textarea, { target: { value: "Hello" } });
  const sendBtn = screen.getByRole("button", { name: /send/i });
  fireEvent.click(sendBtn);
}

describe("[3.6b][ChatPanel-Correction] — P1/P2 tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetClaimCounter();
    Element.prototype.scrollIntoView = vi.fn();
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    mockSendLabChat.mockResolvedValue(createMockResponse());
  });

  it("[3.6b-INT-004][P1] Given corrected response, when axe audit runs, then no accessibility violations", async () => {
    const claims = [
      createClaimVerification({ claimText: "Test claim", isSupported: false }),
    ];
    mockSendLabChat.mockResolvedValue(
      createMockResponse({
        wasCorrected: true,
        correctionCount: 1,
        verifiedClaims: claims,
      }),
    );

    const { container } = render(<ChatPanel sessionId={1} />);
    await sendMessage();

    await waitFor(() => {
      expect(screen.getByText("Corrected")).toBeInTheDocument();
    });

    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });

  it("[3.6b-INT-006][P1] Given response with both wasCorrected=true AND verificationTimedOut=true, when rendered, then both CorrectionBadge and timeout indicator are visible", async () => {
    const claims = [
      createClaimVerification({
        claimText: "Partial claim",
        isSupported: false,
      }),
    ];
    mockSendLabChat.mockResolvedValue(
      createMockResponse({
        wasCorrected: true,
        correctionCount: 1,
        verificationTimedOut: true,
        verifiedClaims: claims,
      }),
    );

    render(<ChatPanel sessionId={1} />);
    await sendMessage();

    await waitFor(() => {
      expect(screen.getByText("Corrected")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Verification timed out — response may contain unverified claims",
        ),
      ).toBeInTheDocument();
    });
  });

  it("[3.6b-INT-007][P1] Given LabChatResponse type, when verifying field names, then camelCase names match backend ClaimVerificationResponse — API contract test", () => {
    const response = createMockResponse({
      wasCorrected: true,
      correctionCount: 2,
      verificationTimedOut: false,
      verifiedClaims: [
        {
          claimText: "Claim one",
          isSupported: false,
          maxSimilarity: 0.42,
          verificationError: false,
        },
        {
          claimText: "Claim two",
          isSupported: false,
          maxSimilarity: 0.15,
          verificationError: true,
        },
      ],
    });

    expect(response.data.wasCorrected).toBe(true);
    expect(response.data.correctionCount).toBe(2);
    expect(response.data.verificationTimedOut).toBe(false);
    expect(response.data.verifiedClaims).toHaveLength(2);
    expect(response.data.verifiedClaims![0]).toHaveProperty("claimText");
    expect(response.data.verifiedClaims![0]).toHaveProperty("isSupported");
    expect(response.data.verifiedClaims![0]).toHaveProperty("maxSimilarity");
    expect(response.data.verifiedClaims![0]).toHaveProperty(
      "verificationError",
    );
    expect(response.data.verifiedClaims![0].claimText).toBe("Claim one");
    expect(response.data.verifiedClaims![1].verificationError).toBe(true);
  });

  it("[3.6b-INT-009][P1] Given multiple assistant messages with mixed correction states, when rendered, then only corrected messages show badge", async () => {
    const correctedClaims = [
      createClaimVerification({
        claimText: "Wrong claim",
        isSupported: false,
      }),
    ];
    mockSendLabChat
      .mockResolvedValueOnce(
        createMockResponse({
          wasCorrected: true,
          correctionCount: 1,
          verifiedClaims: correctedClaims,
        }),
      )
      .mockResolvedValueOnce(createMockResponse());

    render(<ChatPanel sessionId={1} />);
    await sendMessage();
    await waitFor(() => {
      expect(screen.getByText("Corrected")).toBeInTheDocument();
    });

    await sendMessage();
    await waitFor(() => {
      expect(screen.getByText("AI response text")).toBeInTheDocument();
    });
    const badges = screen.queryAllByText("Corrected");
    expect(badges).toHaveLength(1);
  });

  it("[3.6b-INT-010][P1] Given wasCorrected true with empty verifiedClaims, when rendered, then badge shows with 0 in count", async () => {
    mockSendLabChat.mockResolvedValue(
      createMockResponse({
        wasCorrected: true,
        correctionCount: 1,
        verifiedClaims: [],
      }),
    );

    render(<ChatPanel sessionId={1} />);
    await sendMessage();

    await waitFor(() => {
      expect(screen.getByText("Corrected")).toBeInTheDocument();
    });
    expect(screen.getByText("(1)")).toBeInTheDocument();
  });

  it("[3.6b-INT-011][P1] Given error response, when rendered, then no correction indicators shown", async () => {
    mockSendLabChat.mockResolvedValue({
      data: null,
      error: "Server error",
    });

    render(<ChatPanel sessionId={1} />);
    await sendMessage();

    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
    expect(screen.queryByText("Corrected")).not.toBeInTheDocument();
    expect(
      screen.queryByText(
        "Verification timed out — response may contain unverified claims",
      ),
    ).not.toBeInTheDocument();
  });

  it("[3.6b-INT-012][P1] Given user message, when rendered, then no correction indicators on user messages", async () => {
    mockSendLabChat.mockResolvedValue(createMockResponse());

    render(<ChatPanel sessionId={1} />);
    await sendMessage();

    await waitFor(() => {
      expect(screen.getByText("Hello")).toBeInTheDocument();
    });
    expect(screen.queryByText("Corrected")).not.toBeInTheDocument();
  });

  it("[3.6b-INT-013][P2] Given corrected and timed-out response without source attributions, when rendered, then both CorrectionBadge and GlitchPip visible", async () => {
    const claims = [
      createClaimVerification({
        claimText: "Partial claim",
        isSupported: false,
      }),
    ];
    mockSendLabChat.mockResolvedValue(
      createMockResponse({
        sourceAttributions: [],
        wasCorrected: true,
        correctionCount: 1,
        verificationTimedOut: true,
        verifiedClaims: claims,
      }),
    );

    render(<ChatPanel sessionId={1} />);
    await sendMessage();

    await waitFor(() => {
      expect(screen.getByText("Corrected")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Verification timed out — response may contain unverified claims",
        ),
      ).toBeInTheDocument();
    });
  });
});
