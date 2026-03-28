import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ContextTriad } from "../context-triad";

describe("ContextTriad", () => {
  it("renders all 3 bullets with ALL-CAPS labels", () => {
    render(
      <ContextTriad
        why="Solar prospect"
        mood="Engaged"
        target="Mr. Henderson"
      />,
    );

    expect(screen.getByText("WHY:")).toBeInTheDocument();
    expect(screen.getByText("MOOD:")).toBeInTheDocument();
    expect(screen.getByText("TARGET:")).toBeInTheDocument();

    expect(screen.getByText("Solar prospect")).toBeInTheDocument();
    expect(screen.getByText("Engaged")).toBeInTheDocument();
    expect(screen.getByText("Mr. Henderson")).toBeInTheDocument();
  });
});
