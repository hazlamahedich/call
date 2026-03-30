import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { getThreshold } from "../UsageProgressBar";

describe("[1.7-UNIT-101..106][getThreshold] — Threshold computation function", () => {
  it("[1.7-UNIT-101][P0] Given 0%, returns ok", () => {
    expect(getThreshold(0)).toBe("ok");
  });

  it("[1.7-UNIT-102][P0] Given 79%, returns ok", () => {
    expect(getThreshold(79)).toBe("ok");
  });

  it("[1.7-UNIT-103][P0] Given 80%, returns warning", () => {
    expect(getThreshold(80)).toBe("warning");
  });

  it("[1.7-UNIT-104][P0] Given 94%, returns warning", () => {
    expect(getThreshold(94)).toBe("warning");
  });

  it("[1.7-UNIT-105][P0] Given 95%, returns critical", () => {
    expect(getThreshold(95)).toBe("critical");
  });

  it("[1.7-UNIT-106][P0] Given 100%, returns exceeded", () => {
    expect(getThreshold(100)).toBe("exceeded");
  });
});
