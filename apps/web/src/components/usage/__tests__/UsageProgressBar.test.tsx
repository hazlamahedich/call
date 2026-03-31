import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { UsageProgressBar } from "../UsageProgressBar";

describe("[1.7-AC5][UsageProgressBar] — Visual progress bar with threshold colors", () => {
  it("[1.7-UNIT-040][P0] Given low usage, When rendered, Then progress bar shows correct width", () => {
    const { container } = render(<UsageProgressBar percentage={25} />);
    const bar = container.querySelector("[style*='width']");
    expect(bar).toBeInTheDocument();
    expect(bar?.getAttribute("style")).toContain("25%");
  });

  it("[1.7-UNIT-041][P0] Given percentage, When rendered, Then role=progressbar with ARIA attributes", () => {
    render(<UsageProgressBar percentage={50} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toBeInTheDocument();
    expect(bar).toHaveAttribute("aria-valuenow", "50");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
  });

  it("[1.7-UNIT-042][P1] Given percentage < 80, When rendered, Then emerald color class is applied", () => {
    const { container } = render(<UsageProgressBar percentage={30} />);
    const fill = container.querySelector(".bg-neon-emerald");
    expect(fill).toBeInTheDocument();
  });

  it("[1.7-UNIT-043][P1] Given percentage >= 80 and < 95, When rendered, Then warning color class is applied", () => {
    const { container } = render(<UsageProgressBar percentage={85} />);
    const fill = container.querySelector(".bg-neon-blue");
    expect(fill).toBeInTheDocument();
  });

  it("[1.7-UNIT-044][P1] Given percentage >= 95, When rendered, Then exceeded color class is applied", () => {
    const { container } = render(<UsageProgressBar percentage={97} />);
    const fill = container.querySelector(".bg-destructive");
    expect(fill).toBeInTheDocument();
  });

  it("[1.7-UNIT-045][P2] Given reducedMotion=true, When rendered, Then no transition class", () => {
    const { container } = render(
      <UsageProgressBar percentage={50} reducedMotion={true} />,
    );
    const fill = container.querySelector(".transition-all");
    expect(fill).not.toBeInTheDocument();
  });

  it("[1.7-UNIT-046][P2] Given reducedMotion=false, When rendered, Then transition class is present", () => {
    const { container } = render(
      <UsageProgressBar percentage={50} reducedMotion={false} />,
    );
    const fill = container.querySelector(".transition-all");
    expect(fill).toBeInTheDocument();
  });

  it("[1.7-UNIT-047][P1] Given percentage > 100, When rendered, Then clamped to 100%", () => {
    const { container } = render(<UsageProgressBar percentage={150} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "100");
  });

  it("[1.7-UNIT-048][P2] Given UsageProgressBar, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(<UsageProgressBar percentage={50} />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });

  it("[1.7-UNIT-048b][P1] Given reducedMotion=true, When rendered, Then no CSS transition duration in styles", () => {
    const { container } = render(
      <UsageProgressBar percentage={60} reducedMotion={true} />,
    );
    const fill = container.querySelector("[style*='width']");
    expect(fill?.className).not.toContain("transition-all");
    expect(fill?.className).not.toContain("duration-500");
  });

  it("[1.7-UNIT-048c][P1] Given reducedMotion=true with exceeded threshold, When rendered, Then destructive color shown without transition", () => {
    const { container } = render(
      <UsageProgressBar percentage={100} reducedMotion={true} />,
    );
    const fill = container.querySelector(".bg-destructive");
    expect(fill).toBeInTheDocument();
    expect(fill?.className).not.toContain("transition-all");
  });
});

describe("[1.7-AC5][UsageProgressBar] — Color transition boundaries", () => {
  it("[1.7-UNIT-049][P0] Given percentage=79, When rendered, Then ok (emerald) color class is applied", () => {
    const { container } = render(<UsageProgressBar percentage={79} />);
    const fill = container.querySelector(".bg-neon-emerald");
    expect(fill).toBeInTheDocument();
  });

  it("[1.7-UNIT-049b][P0] Given percentage=80, When rendered, Then warning (blue) color class is applied", () => {
    const { container } = render(<UsageProgressBar percentage={80} />);
    const fill = container.querySelector(".bg-neon-blue");
    expect(fill).toBeInTheDocument();
  });

  it("[1.7-UNIT-049c][P0] Given percentage=94, When rendered, Then warning (blue) color class is applied", () => {
    const { container } = render(<UsageProgressBar percentage={94} />);
    const fill = container.querySelector(".bg-neon-blue");
    expect(fill).toBeInTheDocument();
  });

  it("[1.7-UNIT-049d][P0] Given percentage=95, When rendered, Then critical (destructive) color class is applied", () => {
    const { container } = render(<UsageProgressBar percentage={95} />);
    const fill = container.querySelector(".bg-destructive");
    expect(fill).toBeInTheDocument();
  });

  it("[1.7-UNIT-049e][P0] Given percentage=100, When rendered, Then exceeded (destructive) color class is applied", () => {
    const { container } = render(<UsageProgressBar percentage={100} />);
    const fill = container.querySelector(".bg-destructive");
    expect(fill).toBeInTheDocument();
  });

  it("[1.7-UNIT-049f][P1] Given percentage=0, When rendered, Then ok (emerald) color class is applied", () => {
    const { container } = render(<UsageProgressBar percentage={0} />);
    const fill = container.querySelector(".bg-neon-emerald");
    expect(fill).toBeInTheDocument();
  });

  it("[1.7-UNIT-049g][P1] Given NaN percentage, When rendered, Then falls back to 0% with ok color", () => {
    const { container } = render(<UsageProgressBar percentage={NaN} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "0");
    const fill = container.querySelector(".bg-neon-emerald");
    expect(fill).toBeInTheDocument();
  });

  it("[1.7-UNIT-049h][P1] Given Infinity percentage, When rendered, Then falls back to 0% with ok color", () => {
    const { container } = render(<UsageProgressBar percentage={Infinity} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "0");
    const fill = container.querySelector(".bg-neon-emerald");
    expect(fill).toBeInTheDocument();
  });
});
