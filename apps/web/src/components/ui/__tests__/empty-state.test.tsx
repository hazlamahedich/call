import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { EmptyState } from "../empty-state";
import { Button } from "../button";
import { Search } from "lucide-react";

describe("[1.4-AC3][EmptyState] — Empty state placeholder with icon and action", () => {
  it("[1.4-UNIT-048][P0] Given title and description, When rendered, Then both are visible", () => {
    render(
      <EmptyState title="No data" description="Add something to get started" />,
    );
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(
      screen.getByText("Add something to get started"),
    ).toBeInTheDocument();
  });

  it("[1.4-UNIT-049][P0] Given action slot, When rendered, Then action button is present", () => {
    render(<EmptyState title="Empty" action={<Button>Add Item</Button>} />);
    expect(screen.getByText("Add Item")).toBeInTheDocument();
  });

  it("[1.4-UNIT-050][P1] Given no action, When rendered, Then no button is present", () => {
    render(<EmptyState title="Empty" />);
    expect(screen.getByText("Empty")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("[1.4-UNIT-051][P1] Given custom icon prop, When rendered, Then custom icon is displayed", () => {
    const { container } = render(
      <EmptyState title="Not found" icon={Search} />,
    );
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("[1.4-UNIT-052][P2] Given no icon prop, When rendered, Then default Inbox icon is displayed", () => {
    const { container } = render(<EmptyState title="Empty" />);
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("[1.4-UNIT-053][P1] Given EmptyState, When rendered, Then border-dashed styling is applied", () => {
    const { container } = render(<EmptyState title="Empty" />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("border-dashed");
  });

  it("[1.4-UNIT-054][P2] Given only title, When rendered, Then title is visible without action", () => {
    render(<EmptyState title="Just a title" />);
    expect(screen.getByText("Just a title")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("[1.4-UNIT-055][P1] Given EmptyState with action, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <EmptyState
        title="No items"
        description="Add your first item"
        action={<Button>Add</Button>}
      />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
