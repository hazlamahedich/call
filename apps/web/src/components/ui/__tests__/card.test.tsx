import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "../card";

describe("[1.4-AC2][Card] — Obsidian card with standard and glass variants", () => {
  it("[1.4-UNIT-022][P0] Given standard Card, When rendered, Then bg-card, border, and shadow-xl classes are applied", () => {
    const { container } = render(<Card>Content</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain("bg-card");
    expect(card.className).toContain("border");
    expect(card.className).toContain("border-border");
    expect(card.className).toContain("shadow-xl");
  });

  it("[1.4-UNIT-023][P0] Given variant=glass, When rendered, Then glassmorphism classes are applied", () => {
    const { container } = render(<Card variant="glass">Content</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain("bg-card/40");
    expect(card.className).toContain("backdrop-blur-md");
  });

  it("[1.4-UNIT-024][P1] Given children, When rendered, Then children are visible", () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText("Card content")).toBeInTheDocument();
  });

  it("[1.4-UNIT-025][P2] Given custom className, When rendered, Then className is merged", () => {
    const { container } = render(<Card className="extra">Content</Card>);
    expect((container.firstChild as HTMLElement).className).toContain("extra");
  });
});

describe("[1.4-AC2][Card sub-components] — Header, Title, Description, Content, Footer", () => {
  it("[1.4-UNIT-026][P1] Given CardHeader, When rendered, Then flex and p-lg spacing classes are applied", () => {
    const { container } = render(<CardHeader>Header</CardHeader>);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("flex");
    expect(el.className).toContain("p-lg");
    expect(screen.getByText("Header")).toBeInTheDocument();
  });

  it("[1.4-UNIT-027][P1] Given CardTitle, When rendered, Then h3 tag with text-foreground and font-semibold is used", () => {
    render(<CardTitle>Card Title</CardTitle>);
    const title = screen.getByText("Card Title");
    expect(title.tagName).toBe("H3");
    expect(title.className).toContain("text-foreground");
    expect(title.className).toContain("font-semibold");
  });

  it("[1.4-UNIT-028][P2] Given CardDescription, When rendered, Then muted text classes are applied", () => {
    render(<CardDescription>Description text</CardDescription>);
    const desc = screen.getByText("Description text");
    expect(desc.className).toContain("text-muted-foreground");
  });

  it("[1.4-UNIT-029][P1] Given CardContent, When rendered, Then p-lg pt-0 padding is applied", () => {
    const { container } = render(<CardContent>Body</CardContent>);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("p-lg");
    expect(el.className).toContain("pt-0");
  });

  it("[1.4-UNIT-030][P1] Given CardFooter, When rendered, Then flex layout classes are applied", () => {
    const { container } = render(<CardFooter>Footer</CardFooter>);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("flex");
    expect(el.className).toContain("items-center");
  });

  it("[1.4-UNIT-031][P1] Given full card composition, When rendered, Then all sub-components render correctly", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
          <CardDescription>Desc</CardDescription>
        </CardHeader>
        <CardContent>Body</CardContent>
        <CardFooter>Footer</CardFooter>
      </Card>,
    );

    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("Desc")).toBeInTheDocument();
    expect(screen.getByText("Body")).toBeInTheDocument();
    expect(screen.getByText("Footer")).toBeInTheDocument();
  });

  it("[1.4-UNIT-032][P1] Given Card composition, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
          <CardDescription>Desc</CardDescription>
        </CardHeader>
        <CardContent>Body</CardContent>
      </Card>,
    );

    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
