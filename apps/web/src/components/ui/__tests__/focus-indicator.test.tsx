import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { FocusIndicator } from "../focus-indicator";

describe("[1.4-AC1][FocusIndicator] — Focus ring wrapper for accessible interactions", () => {
  it("[1.4-UNIT-063][P0] Given children, When rendered, Then children are visible", () => {
    render(
      <FocusIndicator>
        <button>Focusable</button>
      </FocusIndicator>,
    );

    expect(screen.getByText("Focusable")).toBeInTheDocument();
  });

  it("[1.4-UNIT-064][P1] Given FocusIndicator, When rendered, Then focus-within ring classes are applied", () => {
    const { container } = render(
      <FocusIndicator>
        <button>Focusable</button>
      </FocusIndicator>,
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("focus-within:ring-2");
    expect(wrapper.className).toContain("focus-within:ring-ring");
  });

  it("[1.4-UNIT-065][P2] Given FocusIndicator, When rendered, Then rounded-md class is applied", () => {
    const { container } = render(
      <FocusIndicator>
        <button>Focusable</button>
      </FocusIndicator>,
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("rounded-md");
  });

  it("[1.4-UNIT-066][P2] Given custom className, When rendered, Then className is merged", () => {
    const { container } = render(
      <FocusIndicator className="extra-class">
        <button>Focusable</button>
      </FocusIndicator>,
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("extra-class");
  });

  it("[1.4-UNIT-067][P1] Given FocusIndicator, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <FocusIndicator>
        <button>Focusable</button>
      </FocusIndicator>,
    );

    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
