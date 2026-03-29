import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { BrandingPreview } from "../BrandingPreview";

describe("[1.5-AC2][BrandingPreview] — Live branding preview", () => {
  it("[1.5-UNIT-030][P0] Given default props, When rendered, Then preview is shown", () => {
    const { container } = render(
      <BrandingPreview
        logoUrl={null}
        primaryColor="#10B981"
        brandName={null}
      />,
    );
    expect(screen.getByText("Call")).toBeTruthy();
  });

  it("[1.5-UNIT-031][P1] Given brandName, When rendered, Then brand name is shown", () => {
    render(
      <BrandingPreview
        logoUrl={null}
        primaryColor="#FF5500"
        brandName="My Agency"
      />,
    );
    expect(screen.getByText("My Agency")).toBeTruthy();
  });

  it("[1.5-UNIT-032][P1] Given primaryColor, When rendered, Then color is applied to preview button", () => {
    const { container } = render(
      <BrandingPreview
        logoUrl={null}
        primaryColor="#FF5500"
        brandName={null}
      />,
    );
    const btn = screen.getByText("Primary Action");
    expect(btn.style.backgroundColor).toBe("rgb(255, 85, 0)");
  });

  it("[1.5-UNIT-033][P2] Given logoUrl, When rendered, Then logo image is shown", () => {
    render(
      <BrandingPreview
        logoUrl="data:image/png;base64,test"
        primaryColor="#10B981"
        brandName={null}
      />,
    );
    const img = screen.getByAltText("Logo preview");
    expect(img).toBeTruthy();
  });
});
