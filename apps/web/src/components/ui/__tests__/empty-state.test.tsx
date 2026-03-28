import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "../empty-state";
import { Button } from "../button";

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(
      <EmptyState title="No data" description="Add something to get started" />,
    );
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(
      screen.getByText("Add something to get started"),
    ).toBeInTheDocument();
  });

  it("renders action slot when provided", () => {
    render(<EmptyState title="Empty" action={<Button>Add Item</Button>} />);
    expect(screen.getByText("Add Item")).toBeInTheDocument();
  });

  it("renders without action when not provided", () => {
    render(<EmptyState title="Empty" />);
    expect(screen.getByText("Empty")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
