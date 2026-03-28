import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "../dialog";

describe("Dialog", () => {
  it("renders with Obsidian glassmorphism styling", async () => {
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
  });
});
