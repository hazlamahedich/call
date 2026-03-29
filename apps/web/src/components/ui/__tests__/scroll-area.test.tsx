import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { ScrollArea, ScrollBar } from "../scroll-area";

describe("[1.4-AC5][ScrollArea] — Radix ScrollArea with Obsidian styling", () => {
  it("[1.4-UNIT-063][P1] Given ScrollArea, When rendered, Then children are visible", () => {
    render(
      <ScrollArea>
        <div>Child content</div>
      </ScrollArea>,
    );
    expect(screen.getByText("Child content")).toBeInTheDocument();
  });

  it("[1.4-UNIT-064][P1] Given ScrollArea, When rendered, Then viewport element exists", () => {
    const { container } = render(
      <ScrollArea>
        <div>Content</div>
      </ScrollArea>,
    );
    const viewport = container.querySelector(
      "[data-radix-scroll-area-viewport]",
    );
    expect(viewport).toBeInTheDocument();
  });

  it("[1.4-UNIT-065][P2] Given horizontal ScrollBar, When rendered, Then no errors occur", () => {
    const { container } = render(
      <ScrollArea>
        <div>Content</div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>,
    );
    expect(screen.getByText("Content")).toBeInTheDocument();
    expect(
      container.querySelector("[data-radix-scroll-area-viewport]"),
    ).toBeInTheDocument();
  });

  it("[1.4-UNIT-066][P1] Given ScrollArea, When rendered, Then relative overflow-hidden classes are applied", () => {
    const { container } = render(
      <ScrollArea>
        <div>Content</div>
      </ScrollArea>,
    );
    const root = container.firstChild as HTMLElement;
    expect(root.className).toContain("relative");
    expect(root.className).toContain("overflow-hidden");
  });

  it("[1.4-UNIT-067][P2] Given custom className, When rendered, Then className is merged", () => {
    const { container } = render(
      <ScrollArea className="custom-class">
        <div>Content</div>
      </ScrollArea>,
    );
    const root = container.firstChild as HTMLElement;
    expect(root.className).toContain("custom-class");
  });

  it("[1.4-UNIT-068][P1] Given ScrollArea component, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <ScrollArea>
        <div>Accessible content</div>
      </ScrollArea>,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
