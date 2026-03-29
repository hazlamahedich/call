import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../tabs";

describe("[1.4-AC5][Tabs] — Radix Tabs with neon underline indicator", () => {
  it("[1.4-UNIT-046][P1] Given tabs, When rendered, Then neon underline indicator styling is applied", () => {
    render(
      <Tabs defaultValue="tab1">
        <TabsList>
          <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          <TabsTrigger value="tab2">Tab 2</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content 1</TabsContent>
        <TabsContent value="tab2">Content 2</TabsContent>
      </Tabs>,
    );

    const triggers = screen.getAllByRole("tab");
    expect(triggers).toHaveLength(2);
    expect(triggers[0].className).toContain(
      "data-[state=active]:border-neon-emerald",
    );
  });

  it("[1.4-UNIT-047][P1] Given tabs, When rendered, Then tablist, tab, and tabpanel roles are present", () => {
    render(
      <Tabs defaultValue="tab1">
        <TabsList>
          <TabsTrigger value="tab1">First</TabsTrigger>
          <TabsTrigger value="tab2">Second</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Panel 1</TabsContent>
        <TabsContent value="tab2">Panel 2</TabsContent>
      </Tabs>,
    );

    expect(screen.getByRole("tablist")).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(2);
    expect(screen.getByRole("tabpanel", { name: "First" })).toBeInTheDocument();
  });

  it("[1.4-UNIT-048][P1] Given different tab clicked, When clicked, Then content switches", async () => {
    render(
      <Tabs defaultValue="tab1">
        <TabsList>
          <TabsTrigger value="tab1">First</TabsTrigger>
          <TabsTrigger value="tab2">Second</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Panel 1</TabsContent>
        <TabsContent value="tab2">Panel 2</TabsContent>
      </Tabs>,
    );

    expect(screen.getByRole("tabpanel", { name: "First" })).toHaveTextContent(
      "Panel 1",
    );

    await userEvent.click(screen.getByText("Second"));
    expect(screen.getByRole("tabpanel", { name: "Second" })).toHaveTextContent(
      "Panel 2",
    );
  });

  it("[1.4-UNIT-049][P2] Given TabsContent, When rendered, Then mt-md spacing is applied", () => {
    const { container } = render(
      <Tabs defaultValue="tab1">
        <TabsList>
          <TabsTrigger value="tab1">Tab</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content</TabsContent>
      </Tabs>,
    );

    const panel = container.querySelector("[role='tabpanel']");
    expect(panel?.className).toContain("mt-md");
  });

  it("[1.4-UNIT-050][P1] Given Tabs component, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <Tabs defaultValue="tab1">
        <TabsList>
          <TabsTrigger value="tab1">First</TabsTrigger>
          <TabsTrigger value="tab2">Second</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content 1</TabsContent>
        <TabsContent value="tab2">Content 2</TabsContent>
      </Tabs>,
    );

    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
