import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { LogoUpload } from "../LogoUpload";

describe("[1.5-AC1][LogoUpload] — Drag-and-drop logo upload", () => {
  it("[1.5-UNIT-001][P0] Given LogoUpload, When rendered, Then upload area is visible", () => {
    const { container } = render(
      <LogoUpload currentLogo={null} onLogoChange={vi.fn()} />,
    );
    expect(container.querySelector('[role="button"]')).toBeTruthy();
  });

  it("[1.5-UNIT-002][P1] Given currentLogo, When rendered, Then logo preview is shown", () => {
    render(
      <LogoUpload
        currentLogo="data:image/png;base64,test"
        onLogoChange={vi.fn()}
      />,
    );
    const img = screen.getByAltText("Brand logo");
    expect(img).toBeTruthy();
  });

  it("[1.5-UNIT-003][P0] Given no logo, When rendered, Then upload prompt is shown", () => {
    render(<LogoUpload currentLogo={null} onLogoChange={vi.fn()} />);
    expect(screen.getByText(/drop logo/i)).toBeTruthy();
  });

  it("[1.5-UNIT-004][P1] Given LogoUpload, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <LogoUpload currentLogo={null} onLogoChange={vi.fn()} />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
