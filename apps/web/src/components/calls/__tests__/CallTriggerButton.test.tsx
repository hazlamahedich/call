import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";

const mockTriggerCall = vi.fn();

vi.mock("@/actions/calls", () => ({
  triggerCall: (...args: unknown[]) => mockTriggerCall(...args),
}));

describe("[2.1][CallTriggerButton] — UI component for triggering calls", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("[2.1-UNIT-500][P0] Given rendered, When clicking trigger, Then calls triggerCall action", async () => {
    mockTriggerCall.mockResolvedValue({
      data: { call: { id: 1, vapiCallId: "v1", status: "pending" } },
      error: null,
    });

    const { CallTriggerButton } =
      await import("@/components/calls/CallTriggerButton");
    render(<CallTriggerButton phoneNumber="+1234567890" agentId={5} />);

    const button = screen.getByRole("button", { name: "Start Call" });
    await fireEvent.click(button);

    await waitFor(() => {
      expect(mockTriggerCall).toHaveBeenCalledWith({
        phoneNumber: "+1234567890",
        agentId: 5,
        leadId: undefined,
        campaignId: undefined,
      });
    });
  });

  it("[2.1-UNIT-501][P0] Given error response, When clicking trigger, Then shows error message", async () => {
    mockTriggerCall.mockResolvedValue({
      data: null,
      error: "Monthly call limit reached",
    });

    const { CallTriggerButton } =
      await import("@/components/calls/CallTriggerButton");
    render(<CallTriggerButton phoneNumber="+1234567890" />);

    const button = screen.getByRole("button", { name: "Start Call" });
    await fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Monthly call limit reached",
      );
    });
  });

  it("[2.1-UNIT-502][P1] Given empty phone number, When rendered, Then button is disabled", async () => {
    const { CallTriggerButton } =
      await import("@/components/calls/CallTriggerButton");
    render(<CallTriggerButton phoneNumber="" />);

    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });

  it("[2.1-UNIT-503][P1] Given loading state, When click triggered, Then button shows loading text", async () => {
    mockTriggerCall.mockReturnValue(new Promise(() => {}));

    const { CallTriggerButton } =
      await import("@/components/calls/CallTriggerButton");
    render(<CallTriggerButton phoneNumber="+1234567890" />);

    const button = screen.getByRole("button", { name: "Start Call" });
    await fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole("button")).toHaveTextContent("Calling...");
    });
  });

  it("[2.1-UNIT-504][P1] Given success, When call triggered, Then invokes onCallTriggered callback", async () => {
    const mockData = {
      call: { id: 1, vapiCallId: "v1", status: "pending" },
    };
    mockTriggerCall.mockResolvedValue({ data: mockData, error: null });
    const onCallTriggered = vi.fn();

    const { CallTriggerButton } =
      await import("@/components/calls/CallTriggerButton");
    render(
      <CallTriggerButton
        phoneNumber="+1234567890"
        onCallTriggered={onCallTriggered}
      />,
    );

    const button = screen.getByRole("button", { name: "Start Call" });
    await fireEvent.click(button);

    await waitFor(() => {
      expect(onCallTriggered).toHaveBeenCalledWith(mockData);
    });
  });
});
