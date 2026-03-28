import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "../card";

describe("Card", () => {
  it("renders standard variant with correct classes", () => {
    const { container } = render(<Card>Content</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain("bg-card");
    expect(card.className).toContain("border");
    expect(card.className).toContain("border-border");
  });

  it("renders glass variant with glassmorphism classes", () => {
    const { container } = render(<Card variant="glass">Content</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain("bg-card/40");
    expect(card.className).toContain("backdrop-blur-md");
  });
});
