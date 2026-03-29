import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { DomainConfig } from "../DomainConfig";

describe("[1.5-AC3][DomainConfig] — Custom domain verification", () => {
  it("[1.5-UNIT-020][P0] Given DomainConfig, When rendered, Then domain input and verify button are present", () => {
    render(<DomainConfig domain={null} verified={false} onVerify={vi.fn()} />);
    expect(screen.getByPlaceholderText(/custom/i)).toBeTruthy();
    expect(screen.getByText("Verify DNS")).toBeTruthy();
  });

  it("[1.5-UNIT-021][P1] Given existing domain, When rendered, Then input shows domain", () => {
    render(
      <DomainConfig
        domain="custom.example.com"
        verified={false}
        onVerify={vi.fn()}
      />,
    );
    const input = screen.getByDisplayValue("custom.example.com");
    expect(input).toBeTruthy();
  });

  it("[1.5-UNIT-022][P0] Given empty input, When verify clicked, Then button is disabled", () => {
    render(<DomainConfig domain={null} verified={false} onVerify={vi.fn()} />);
    const btn = screen.getByText("Verify DNS") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("[1.5-UNIT-023][P1] Given DomainConfig, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <DomainConfig domain={null} verified={false} onVerify={vi.fn()} />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
