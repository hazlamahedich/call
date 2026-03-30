import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { StepVoiceSelection } from "../StepVoiceSelection";
import { VOICE_OPTIONS } from "@/lib/onboarding-constants";

describe("[1.6-AC3][StepVoiceSelection] — Voice selection step", () => {
  it("[1.6-UNIT-020][P0] Given no value, When rendered, Then all voice options are shown", () => {
    render(<StepVoiceSelection value="" onChange={vi.fn()} />);
    for (const voice of VOICE_OPTIONS) {
      expect(screen.getByText(voice.name)).toBeInTheDocument();
    }
  });

  it("[1.6-UNIT-021][P0] Given value='avery', When rendered, Then Avery is selected", () => {
    const { container } = render(
      <StepVoiceSelection value="avery" onChange={vi.fn()} />,
    );
    const selected = container.querySelector(
      '[role="radio"][aria-checked="true"]',
    );
    expect(selected).toBeInTheDocument();
    expect(selected?.textContent).toContain("Avery");
  });

  it("[1.6-UNIT-022][P0] Given voice option, When clicked, Then onChange fires with voice id", async () => {
    const onChange = vi.fn();
    render(<StepVoiceSelection value="" onChange={onChange} />);
    await userEvent.click(screen.getByText("Jordan"));
    expect(onChange).toHaveBeenCalledWith("jordan");
  });

  it("[1.6-UNIT-023][P1] Given radiogroup, When rendered, Then correct ARIA role is present", () => {
    render(<StepVoiceSelection value="" onChange={vi.fn()} />);
    expect(
      screen.getByRole("radiogroup", { name: "Voice options" }),
    ).toBeInTheDocument();
  });

  it("[1.6-UNIT-024][P2] Given StepVoiceSelection, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <StepVoiceSelection value="" onChange={vi.fn()} />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
