import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { StepIntegrationChoice } from "../StepIntegrationChoice";
import { INTEGRATION_OPTIONS } from "@/lib/onboarding-constants";

describe("[1.6-AC4][StepIntegrationChoice] — Integration selection step", () => {
  it("[1.6-UNIT-030][P0] Given no value, When rendered, Then all integration options are shown", () => {
    render(<StepIntegrationChoice value="" onChange={vi.fn()} />);
    for (const option of INTEGRATION_OPTIONS) {
      expect(screen.getByText(option.name)).toBeInTheDocument();
    }
  });

  it("[1.6-UNIT-031][P0] Given value='hubspot', When rendered, Then HubSpot is selected", () => {
    const { container } = render(
      <StepIntegrationChoice value="hubspot" onChange={vi.fn()} />,
    );
    const selected = container.querySelector(
      '[role="radio"][aria-checked="true"]',
    );
    expect(selected).toBeInTheDocument();
    expect(selected?.textContent).toContain("HubSpot");
  });

  it("[1.6-UNIT-032][P0] Given skip option, When clicked, Then onChange fires with 'skip'", async () => {
    const onChange = vi.fn();
    render(<StepIntegrationChoice value="" onChange={onChange} />);
    await userEvent.click(screen.getByText("Skip for now"));
    expect(onChange).toHaveBeenCalledWith("skip");
  });

  it("[1.6-UNIT-033][P1] Given radiogroup, When rendered, Then correct ARIA role is present", () => {
    render(<StepIntegrationChoice value="" onChange={vi.fn()} />);
    expect(
      screen.getByRole("radiogroup", { name: "Integration options" }),
    ).toBeInTheDocument();
  });

  it("[1.6-UNIT-034][P2] Given StepIntegrationChoice, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <StepIntegrationChoice value="" onChange={vi.fn()} />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
