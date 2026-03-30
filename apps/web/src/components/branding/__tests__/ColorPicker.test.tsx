import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { axe } from "vitest-axe";
import { ColorPicker } from "../ColorPicker";

describe("[1.5-AC1][ColorPicker] — Hex color picker", () => {
  it("[1.5-UNIT-010][P0] Given ColorPicker, When rendered, Then color input and text input are present", () => {
    render(<ColorPicker value="#10B981" onChange={vi.fn()} />);
    const textInput = screen.getByPlaceholderText("#10B981");
    expect(textInput).toBeTruthy();
  });

  it("[1.5-UNIT-011][P1] Given valid hex, When rendered, Then preview strip shows color", () => {
    const { container } = render(
      <ColorPicker value="#FF5500" onChange={vi.fn()} />,
    );
    const strip = container.querySelector("[style*='background-color']");
    expect(strip).toBeTruthy();
  });

  it("[1.5-UNIT-012][P0] Given ColorPicker, When text input changes to valid hex, Then onChange fires after debounce", () => {
    vi.useFakeTimers();
    const onChange = vi.fn();
    render(<ColorPicker value="#10B981" onChange={onChange} />);
    const input = screen.getByPlaceholderText("#10B981");
    fireEvent.change(input, { target: { value: "#FF5500" } });
    expect(onChange).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(400);
    });
    expect(onChange).toHaveBeenCalledWith("#FF5500");
    vi.useRealTimers();
  });

  it("[1.5-UNIT-013][P1] Given ColorPicker, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <ColorPicker value="#10B981" onChange={vi.fn()} />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });

  it("[1.5-UNIT-014][P1] Given ColorPicker, When invalid hex entered, Then onChange is NOT called after debounce", () => {
    vi.useFakeTimers();
    const onChange = vi.fn();
    render(<ColorPicker value="#10B981" onChange={onChange} />);
    const input = screen.getByPlaceholderText("#10B981");
    fireEvent.change(input, { target: { value: "#GGGGGG" } });
    act(() => {
      vi.advanceTimersByTime(400);
    });
    expect(onChange).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("[1.5-UNIT-015][P1] Given ColorPicker, When invalid 7-char hex entered, Then error message is shown", () => {
    render(<ColorPicker value="#10B981" onChange={vi.fn()} />);
    const input = screen.getByPlaceholderText("#10B981");
    fireEvent.change(input, { target: { value: "#GGGGGG" } });
    expect(screen.getByText("Invalid hex color")).toBeTruthy();
  });
});
