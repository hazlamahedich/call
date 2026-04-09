import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { axe } from "vitest-axe";
import { CorrectionBadge } from "../correction-badge";
import {
  createClaimVerification,
  resetClaimCounter,
} from "@/test/factories/correction";

describe("[3.6b][CorrectionBadge] — correction badge with expandable detail panel", () => {
  const defaultClaims = [
    createClaimVerification({
      claimText: "Claim A",
      isSupported: false,
      verificationError: false,
    }),
    createClaimVerification({
      claimText: "Claim B",
      isSupported: false,
      verificationError: true,
    }),
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    resetClaimCounter();
  });

  it("[3.6b-UNIT-001][P0] Given correction badge, when rendered, then shows Corrected text with ShieldCheck icon", () => {
    render(
      <CorrectionBadge correctionCount={2} verifiedClaims={defaultClaims} />,
    );
    expect(screen.getByText("Corrected")).toBeInTheDocument();
    expect(screen.getByText("(2)")).toBeInTheDocument();
    const trigger = screen.getByRole("button");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("[3.6b-UNIT-002][P0] Given correction badge with 2 corrections, when clicked, then detail panel expands showing 2 claims", async () => {
    render(
      <CorrectionBadge correctionCount={2} verifiedClaims={defaultClaims} />,
    );
    const trigger = screen.getByRole("button");
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    await waitFor(() => {
      expect(screen.getByText("2 claims corrected")).toBeInTheDocument();
    });
    expect(screen.getByText("Claim A")).toBeInTheDocument();
    expect(screen.getByText("Claim B")).toBeInTheDocument();
  });

  it("[3.6b-UNIT-003][P0] Given expanded detail panel, when Escape pressed, then panel collapses and focus returns to trigger", async () => {
    render(
      <CorrectionBadge correctionCount={2} verifiedClaims={defaultClaims} />,
    );
    const trigger = screen.getByRole("button");
    fireEvent.click(trigger);
    await waitFor(() => {
      expect(screen.getByText("2 claims corrected")).toBeInTheDocument();
    });
    fireEvent.keyDown(trigger, { key: "Escape" });
    await waitFor(() => {
      expect(trigger).toHaveAttribute("aria-expanded", "false");
    });
    expect(trigger).toHaveFocus();
  });

  it("[3.6b-UNIT-004][P1] Given expanded detail panel, when clicking outside, then panel collapses", async () => {
    render(
      <div>
        <CorrectionBadge correctionCount={2} verifiedClaims={defaultClaims} />
        <div data-testid="outside">Outside element</div>
      </div>,
    );
    const trigger = screen.getByRole("button");
    fireEvent.click(trigger);
    await waitFor(() => {
      expect(screen.getByText("2 claims corrected")).toBeInTheDocument();
    });
    fireEvent.mouseDown(screen.getByTestId("outside"));
    await waitFor(() => {
      expect(trigger).toHaveAttribute("aria-expanded", "false");
    });
  });

  it("[3.6b-UNIT-005][P0] Given claim text longer than 50 chars, when displayed, then truncated with ellipsis — prevents PII exposure", async () => {
    const longClaim = "A".repeat(80);
    const claims = [
      createClaimVerification({ claimText: longClaim, isSupported: false }),
    ];
    render(<CorrectionBadge correctionCount={1} verifiedClaims={claims} />);
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      const claimEl = screen.getByText("A".repeat(50) + "...");
      expect(claimEl).toBeInTheDocument();
    });
    expect(screen.queryByText(longClaim)).not.toBeInTheDocument();
  });

  it("[3.6b-UNIT-006][P1] Given correction badge, when axe audit runs on expanded panel, then no accessibility violations", async () => {
    const { container } = render(
      <CorrectionBadge correctionCount={2} verifiedClaims={defaultClaims} />,
    );
    const trigger = screen.getByRole("button");
    fireEvent.click(trigger);
    await waitFor(() => {
      expect(screen.getByText("2 claims corrected")).toBeInTheDocument();
    });
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });

  it("[3.6b-UNIT-007][P2] Given correction badge with unsupported claims, when rendering, then neon-crimson dot and Could not verify label shown", async () => {
    const claims = [
      createClaimVerification({
        claimText: "Fallback claim",
        isSupported: false,
        verificationError: true,
      }),
    ];
    const { container } = render(
      <CorrectionBadge correctionCount={1} verifiedClaims={claims} />,
    );
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(screen.getByText("Fallback claim")).toBeInTheDocument();
      expect(screen.getByText("Could not verify")).toBeInTheDocument();
    });
    const dot = container.querySelector(".correction-detail__dot--unverified");
    expect(dot).toBeInTheDocument();
  });

  it("[3.6b-UNIT-008][P2] Given correction badge with rephrased claims, when rendering, then neon-emerald dot and Rephrased label shown", async () => {
    const claims = [
      createClaimVerification({
        claimText: "Rephrased claim",
        isSupported: false,
        verificationError: false,
      }),
    ];
    const { container } = render(
      <CorrectionBadge correctionCount={1} verifiedClaims={claims} />,
    );
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(screen.getByText("Rephrased claim")).toBeInTheDocument();
      expect(screen.getByText("Rephrased")).toBeInTheDocument();
    });
    const dot = container.querySelector(".correction-detail__dot--rephrased");
    expect(dot).toBeInTheDocument();
  });

  it("[3.6b-UNIT-009][P2] Given correction badge, when rapidly toggled open/close 5 times, then final state is consistent (no state race condition)", async () => {
    render(
      <CorrectionBadge correctionCount={1} verifiedClaims={defaultClaims} />,
    );
    const trigger = screen.getByRole("button");
    for (let i = 0; i < 5; i++) {
      fireEvent.click(trigger);
    }
    await waitFor(() => {
      expect(trigger).toHaveAttribute("aria-expanded", "true");
    });
  });

  it("[3.6b-UNIT-010][P1] Given all claims supported, when expanded, then header shows 0 claims corrected", async () => {
    const claims = [
      createClaimVerification({
        claimText: "Supported claim",
        isSupported: true,
      }),
    ];
    render(<CorrectionBadge correctionCount={1} verifiedClaims={claims} />);
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(screen.getByText("0 claims corrected")).toBeInTheDocument();
    });
    expect(screen.queryByText("Supported claim")).not.toBeInTheDocument();
  });

  it("[3.6b-UNIT-011][P1] Given header uses unsupported count not correctionCount, when correctionCount=5 but only 2 unsupported, then header says 2", async () => {
    render(
      <CorrectionBadge correctionCount={5} verifiedClaims={defaultClaims} />,
    );
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(screen.getByText("2 claims corrected")).toBeInTheDocument();
    });
  });
});
