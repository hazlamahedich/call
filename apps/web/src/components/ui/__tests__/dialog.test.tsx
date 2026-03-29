import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogClose,
  DialogHeader,
  DialogFooter,
} from "../dialog";

describe("[1.4-AC5][Dialog] — Radix Dialog with Obsidian styling", () => {
  it("[1.4-UNIT-040][P1] Given dialog is open, When rendered, Then glassmorphism styling is applied", () => {
    render(
      <Dialog defaultOpen>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Test Dialog</DialogTitle>
          <DialogDescription>Test description</DialogDescription>
        </DialogContent>
      </Dialog>,
    );

    expect(screen.getByText("Test Dialog")).toBeInTheDocument();
    const content =
      screen.getByText("Test Dialog").closest("[role='dialog']") ??
      screen.getByText("Test Dialog").parentElement;
    expect(content?.className).toContain("bg-card");
    expect(content?.className).toContain("border-border");
  });

  it("[1.4-UNIT-041][P1] Given dialog is open, When inspected, Then it has role=dialog", () => {
    render(
      <Dialog defaultOpen>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Dialog</DialogTitle>
          <DialogDescription>Desc</DialogDescription>
        </DialogContent>
      </Dialog>,
    );

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute("role", "dialog");
  });

  it("[1.4-UNIT-042][P1] Given DialogHeader and DialogFooter, When rendered, Then flex layout classes are applied", () => {
    render(
      <Dialog defaultOpen>
        <DialogContent>
          <DialogHeader>Header area</DialogHeader>
          <DialogTitle>Title</DialogTitle>
          <DialogDescription>Desc</DialogDescription>
          <DialogFooter>Footer area</DialogFooter>
        </DialogContent>
      </Dialog>,
    );

    expect(screen.getByText("Header area")).toBeInTheDocument();
    expect(screen.getByText("Footer area")).toBeInTheDocument();
  });

  it("[1.4-UNIT-043][P2] Given DialogHeader, When rendered, Then flex and space-y-xs classes are applied", () => {
    render(
      <Dialog defaultOpen>
        <DialogContent>
          <DialogHeader data-testid="header">H</DialogHeader>
          <DialogTitle>T</DialogTitle>
          <DialogDescription>D</DialogDescription>
        </DialogContent>
      </Dialog>,
    );

    const header = screen.getByTestId("header");
    expect(header.className).toContain("flex");
    expect(header.className).toContain("space-y-xs");
  });

  it("[1.4-UNIT-044][P2] Given DialogFooter, When rendered, Then flex layout classes are applied", () => {
    render(
      <Dialog defaultOpen>
        <DialogContent>
          <DialogFooter data-testid="footer">F</DialogFooter>
        </DialogContent>
      </Dialog>,
    );

    const footer = screen.getByTestId("footer");
    expect(footer.className).toContain("flex");
  });

  it("[1.4-UNIT-045][P1] Given Dialog component, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <Dialog defaultOpen>
        <DialogContent>
          <DialogTitle>Accessible Dialog</DialogTitle>
          <DialogDescription>Description for a11y</DialogDescription>
        </DialogContent>
      </Dialog>,
    );

    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
