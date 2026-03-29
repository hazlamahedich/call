import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "../tooltip";

describe("[1.4-AC5][Tooltip] — Radix Tooltip with Obsidian styling", () => {
  it("[1.4-UNIT-058][P1] Given tooltip, When not hovered, Then content is hidden", () => {
    render(
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger>Hover me</TooltipTrigger>
          <TooltipContent>Tooltip text</TooltipContent>
        </Tooltip>
      </TooltipProvider>,
    );
    expect(screen.queryByText("Tooltip text")).not.toBeInTheDocument();
  });

  it("[1.4-UNIT-059][P1] Given tooltip trigger hovered, When hovered, Then content appears", async () => {
    render(
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger>Hover me</TooltipTrigger>
          <TooltipContent>Tooltip text</TooltipContent>
        </Tooltip>
      </TooltipProvider>,
    );
    await userEvent.hover(screen.getByText("Hover me"));
    expect(await screen.findByRole("tooltip")).toBeInTheDocument();
  });

  it("[1.4-UNIT-060][P1] Given tooltip shown, When inspected, Then Obsidian styling is applied", async () => {
    const { container } = render(
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger>Hover me</TooltipTrigger>
          <TooltipContent>Tooltip text</TooltipContent>
        </Tooltip>
      </TooltipProvider>,
    );
    await userEvent.hover(screen.getByText("Hover me"));
    await screen.findByRole("tooltip");
    const tooltipEl = container.querySelector("[data-side]");
    expect(tooltipEl?.className).toContain("bg-card");
    expect(tooltipEl?.className).toContain("border-border");
  });

  it("[1.4-UNIT-061][P2] Given tooltip with sideOffset, When shown, Then it renders correctly", async () => {
    render(
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger>Hover me</TooltipTrigger>
          <TooltipContent sideOffset={10}>Tooltip text</TooltipContent>
        </Tooltip>
      </TooltipProvider>,
    );
    await userEvent.hover(screen.getByText("Hover me"));
    expect(await screen.findByRole("tooltip")).toBeInTheDocument();
  });

  it("[1.4-UNIT-062][P2] Given custom className, When shown, Then className is merged", async () => {
    const { container } = render(
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger>Hover me</TooltipTrigger>
          <TooltipContent className="custom-class">Tooltip text</TooltipContent>
        </Tooltip>
      </TooltipProvider>,
    );
    await userEvent.hover(screen.getByText("Hover me"));
    await screen.findByRole("tooltip");
    const tooltipEl = container.querySelector("[data-side]");
    expect(tooltipEl?.className).toContain("custom-class");
  });

  it("[1.4-UNIT-063][P1] Given Tooltip component, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger>Hover me</TooltipTrigger>
          <TooltipContent>Tooltip text</TooltipContent>
        </Tooltip>
      </TooltipProvider>,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
