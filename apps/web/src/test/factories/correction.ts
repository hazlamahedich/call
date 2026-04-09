import type { ClaimVerification } from "@/actions/scripts-lab";

let counter = 0;

export function resetClaimCounter(): void {
  counter = 0;
}

export function createClaimVerification(
  overrides: Partial<ClaimVerification> = {},
): ClaimVerification {
  counter++;
  return {
    claimText: `Test claim ${counter}`,
    isSupported: false,
    maxSimilarity: 0.45,
    verificationError: false,
    ...overrides,
  };
}
