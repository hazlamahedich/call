import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../tabs";

describe("Tabs", () => {
  it("renders tabs with neon underline indicator styling", () => {
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
});
