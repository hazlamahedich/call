import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { axe } from "vitest-axe";
import { CorrectionBadge } from "../correction-badge";
import {
  createClaimVerification,
  resetClaimCounter,
} from "@/test/factories/correction";

describe("[3.6b][CorrectionBadge] — P1/P2 tests", () => {
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

  it("[3.6b-UNIT-015][P1] Given correction badge, when rendered, then aria-label contains correction count", () => {
    render(
      <CorrectionBadge correctionCount={3} verifiedClaims={defaultClaims} />,
    );
    const trigger = screen.getByRole("button");
    expect(trigger).toHaveAttribute(
      "aria-label",
      "Corrected — 3 claims corrected",
    );
  });

  it("[3.6b-UNIT-016][P1] Given correction badge with 1 correction, when rendered, then aria-label uses singular claim", () => {
    const claims = [
      createClaimVerification({
        claimText: "Single claim",
        isSupported: false,
      }),
    ];
    render(<CorrectionBadge correctionCount={1} verifiedClaims={claims} />);
    const trigger = screen.getByRole("button");
    expect(trigger).toHaveAttribute(
      "aria-label",
      "Corrected — 1 claim corrected",
    );
  });

  it("[3.6b-UNIT-017][P1] Given claim with maxSimilarity 0.42, when displayed, then shows 42% match", async () => {
    const claims = [
      createClaimVerification({
        claimText: "Sim test",
        isSupported: false,
        maxSimilarity: 0.42,
      }),
    ];
    render(<CorrectionBadge correctionCount={1} verifiedClaims={claims} />);
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(screen.getByText("42% match")).toBeInTheDocument();
    });
  });

  it("[3.6b-UNIT-018][P1] Given claim text of exactly 50 chars, when displayed, then not truncated", async () => {
    const exactClaim = "A".repeat(50);
    const claims = [
      createClaimVerification({
        claimText: exactClaim,
        isSupported: false,
      }),
    ];
    render(<CorrectionBadge correctionCount={1} verifiedClaims={claims} />);
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(screen.getByText(exactClaim)).toBeInTheDocument();
    });
    expect(screen.queryByText("...")).not.toBeInTheDocument();
  });

  it("[3.6b-UNIT-019][P1] Given empty claim text, when displayed, then shows empty string without crash", async () => {
    const claims = [
      createClaimVerification({
        claimText: "",
        isSupported: false,
      }),
    ];
    const { container } = render(
      <CorrectionBadge correctionCount={1} verifiedClaims={claims} />,
    );
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(
        container.querySelector(".correction-detail--visible"),
      ).toBeInTheDocument();
    });
    const claimTexts = container.querySelectorAll(
      ".correction-detail__claim-text",
    );
    expect(claimTexts).toHaveLength(1);
    expect(claimTexts[0].textContent).toBe("");
  });

  it("[3.6b-UNIT-020][P2] Given badge with className prop, when rendered, then className is applied to wrapper", () => {
    const { container } = render(
      <CorrectionBadge
        correctionCount={1}
        verifiedClaims={defaultClaims}
        className="custom-class"
      />,
    );
    const wrapper = container.querySelector(".correction-badge-wrapper");
    expect(wrapper).toHaveClass("custom-class");
  });
});
