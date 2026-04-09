import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
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
  sendBtn.click();
}

describe("[3.6b][ChatPanel-Correction] — P0 critical tests", () => {
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

  it("[3.6b-INT-001][P0] Given corrected response, when message renders, then CorrectionBadge is visible", async () => {
    const claims = [
      createClaimVerification({
        claimText: "Incorrect claim",
        isSupported: false,
      }),
    ];
    mockSendLabChat.mockResolvedValue(
      createMockResponse({
        wasCorrected: true,
        correctionCount: 1,
        verifiedClaims: claims,
      }),
    );

    render(<ChatPanel sessionId={1} />);
    await sendMessage();

    await waitFor(() => {
      expect(screen.getByText("Corrected")).toBeInTheDocument();
    });
  });

  it("[3.6b-INT-002][P0] Given timed-out response, when message renders, then StatusMessage warning is visible", async () => {
    mockSendLabChat.mockResolvedValue(
      createMockResponse({ verificationTimedOut: true }),
    );

    render(<ChatPanel sessionId={1} />);
    await sendMessage();

    await waitFor(() => {
      expect(
        screen.getByText(
          "Verification timed out — response may contain unverified claims",
        ),
      ).toBeInTheDocument();
    });
    const statusEl = screen.getByRole("status");
    expect(statusEl).toBeInTheDocument();
  });

  it("[3.6b-INT-003][P0] Given normal response, when message renders, then no correction indicators shown", async () => {
    mockSendLabChat.mockResolvedValue(createMockResponse());

    render(<ChatPanel sessionId={1} />);
    await sendMessage();

    await waitFor(() => {
      expect(screen.getByText("AI response text")).toBeInTheDocument();
    });
    expect(screen.queryByText("Corrected")).not.toBeInTheDocument();
    expect(
      screen.queryByText(
        "Verification timed out — response may contain unverified claims",
      ),
    ).not.toBeInTheDocument();
  });

  it("[3.6b-INT-005][P0] Given ChatMessage with no correction fields at all (undefined, not false), when rendered, then no errors and no correction indicators shown — backward compatibility", async () => {
    mockSendLabChat.mockResolvedValue(createMockResponse());

    render(<ChatPanel sessionId={1} />);
    await sendMessage();

    await waitFor(() => {
      expect(screen.getByText("AI response text")).toBeInTheDocument();
    });
    expect(screen.queryByText("Corrected")).not.toBeInTheDocument();
  });

  it("[3.6b-INT-008][P0] Given corrected response without source attributions, when message renders, then CorrectionBadge is still visible", async () => {
    const claims = [
      createClaimVerification({
        claimText: "No sources claim",
        isSupported: false,
      }),
    ];
    mockSendLabChat.mockResolvedValue(
      createMockResponse({
        sourceAttributions: [],
        wasCorrected: true,
        correctionCount: 1,
        verifiedClaims: claims,
      }),
    );

    render(<ChatPanel sessionId={1} />);
    await sendMessage();

    await waitFor(() => {
      expect(screen.getByText("Corrected")).toBeInTheDocument();
    });
  });
});
