import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CorrectionBadge } from "../correction-badge";
import {
  createClaimVerification,
  resetClaimCounter,
} from "@/test/factories/correction";

describe("[3.6b][CorrectionBadge] — P0 critical tests", () => {
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

  it("[3.6b-UNIT-012][P0] Given expanded detail panel, when X close button clicked, then panel collapses", async () => {
    render(
      <CorrectionBadge correctionCount={2} verifiedClaims={defaultClaims} />,
    );
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(screen.getByText("2 claims corrected")).toBeInTheDocument();
    });
    const closeBtn = screen.getByLabelText("Close correction details");
    fireEvent.click(closeBtn);
    await waitFor(() => {
      expect(screen.getByRole("button")).toHaveAttribute(
        "aria-expanded",
        "false",
      );
    });
  });

  it("[3.6b-UNIT-013][P0] Given collapsed badge, when Enter key pressed, then panel expands", async () => {
    render(
      <CorrectionBadge correctionCount={1} verifiedClaims={defaultClaims} />,
    );
    const trigger = screen.getByRole("button");
    fireEvent.keyDown(trigger, { key: "Enter" });
    await waitFor(() => {
      expect(trigger).toHaveAttribute("aria-expanded", "true");
    });
  });

  it("[3.6b-UNIT-014][P0] Given collapsed badge, when Space key pressed, then panel expands", async () => {
    render(
      <CorrectionBadge correctionCount={1} verifiedClaims={defaultClaims} />,
    );
    const trigger = screen.getByRole("button");
    fireEvent.keyDown(trigger, { key: " " });
    await waitFor(() => {
      expect(trigger).toHaveAttribute("aria-expanded", "true");
    });
  });
});
