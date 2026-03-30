import { describe, it, expect } from "vitest";
import { THRESHOLD_LABELS, PLAN_LABELS } from "@/lib/usage-constants";

describe("[1.7-UNIT-107..112][usage-constants] — Constants coverage", () => {
  it("[1.7-UNIT-107][P0] THRESHOLD_LABELS has all four threshold keys", () => {
    expect(Object.keys(THRESHOLD_LABELS)).toEqual([
      "ok",
      "warning",
      "critical",
      "exceeded",
    ]);
  });

  it("[1.7-UNIT-108][P0] THRESHOLD_LABELS ok is non-empty", () => {
    expect(THRESHOLD_LABELS.ok.length).toBeGreaterThan(0);
  });

  it("[1.7-UNIT-109][P0] THRESHOLD_LABELS warning mentions 80%", () => {
    expect(THRESHOLD_LABELS.warning).toContain("80%");
  });

  it("[1.7-UNIT-110][P0] THRESHOLD_LABELS critical mentions 95%", () => {
    expect(THRESHOLD_LABELS.critical).toContain("95%");
  });

  it("[1.7-UNIT-111][P0] PLAN_LABELS has all three plan keys", () => {
    expect(Object.keys(PLAN_LABELS)).toEqual(["free", "pro", "enterprise"]);
  });

  it("[1.7-UNIT-112][P0] PLAN_LABELS values are non-empty", () => {
    for (const label of Object.values(PLAN_LABELS)) {
      expect(label.length).toBeGreaterThan(0);
    }
  });
});
