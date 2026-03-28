import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { CockpitContainer } from "../cockpit-container";

describe("CockpitContainer", () => {
  it("triggers boot animation when active prop changes to true", async () => {
    const onBootComplete = vi.fn();
    const { rerender } = render(
      <CockpitContainer active={false} onBootComplete={onBootComplete}>
        <div>Content</div>
      </CockpitContainer>,
    );

    const container = screen.getByText("Content").parentElement!;
    expect(container.className).not.toContain("animate-boot-glow");

    rerender(
      <CockpitContainer active={true} onBootComplete={onBootComplete}>
        <div>Content</div>
      </CockpitContainer>,
    );

    expect(container.className).toContain("animate-boot-glow");

    await act(async () => {
      await new Promise((r) => setTimeout(r, 400));
    });

    expect(onBootComplete).toHaveBeenCalled();
  });

  it("renders glassmorphism styling", () => {
    const { container } = render(
      <CockpitContainer>
        <div>Content</div>
      </CockpitContainer>,
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("bg-card/40");
    expect(wrapper.className).toContain("backdrop-blur-md");
  });

  it("respects reducedMotion prop", async () => {
    const { container } = render(
      <CockpitContainer active={true} reducedMotion={true}>
        <div>Content</div>
      </CockpitContainer>,
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).not.toContain("animate-boot-glow");
  });
});
