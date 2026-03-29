import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { Popover, PopoverTrigger, PopoverContent } from "../popover";

describe("[1.4-AC5][Popover] — Radix Popover with Obsidian styling", () => {
  it("[1.4-UNIT-069][P1] Given popover trigger clicked, When clicked, Then content appears", async () => {
    render(
      <Popover>
        <PopoverTrigger>Open popover</PopoverTrigger>
        <PopoverContent>Popover body</PopoverContent>
      </Popover>,
    );
    expect(screen.queryByText("Popover body")).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("Open popover"));
    expect(await screen.findByText("Popover body")).toBeInTheDocument();
  });

  it("[1.4-UNIT-070][P1] Given popover shown, When inspected, Then Obsidian styling is applied", async () => {
    render(
      <Popover>
        <PopoverTrigger>Open</PopoverTrigger>
        <PopoverContent>Body</PopoverContent>
      </Popover>,
    );
    await userEvent.click(screen.getByText("Open"));
    const content = await screen.findByText("Body");
    expect(content.className).toContain("bg-card");
    expect(content.className).toContain("border-border");
  });

  it("[1.4-UNIT-071][P2] Given popover with sideOffset, When shown, Then it renders correctly", async () => {
    render(
      <Popover>
        <PopoverTrigger>Open</PopoverTrigger>
        <PopoverContent sideOffset={12}>Body</PopoverContent>
      </Popover>,
    );
    await userEvent.click(screen.getByText("Open"));
    expect(await screen.findByText("Body")).toBeInTheDocument();
  });

  it("[1.4-UNIT-072][P2] Given custom className, When shown, Then className is merged", async () => {
    render(
      <Popover>
        <PopoverTrigger>Open</PopoverTrigger>
        <PopoverContent className="custom-popover">Body</PopoverContent>
      </Popover>,
    );
    await userEvent.click(screen.getByText("Open"));
    const content = await screen.findByText("Body");
    expect(content.className).toContain("custom-popover");
  });

  it("[1.4-UNIT-073][P1] Given Popover component, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <Popover>
        <PopoverTrigger>Open</PopoverTrigger>
        <PopoverContent>Body</PopoverContent>
      </Popover>,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
