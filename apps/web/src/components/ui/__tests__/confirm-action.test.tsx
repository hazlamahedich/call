import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfirmAction } from "../confirm-action";

describe("ConfirmAction", () => {
  it("opens dialog on trigger click", async () => {
    render(
      <ConfirmAction
        title="Delete item?"
        description="This cannot be undone."
        confirmLabel="Delete"
        onConfirm={() => {}}
      >
        <button>Delete</button>
      </ConfirmAction>,
    );

    await userEvent.click(screen.getByText("Delete"));
    expect(screen.getByText("Delete item?")).toBeInTheDocument();
    expect(screen.getByText("This cannot be undone.")).toBeInTheDocument();
  });

  it("renders destructive variant styling", async () => {
    render(
      <ConfirmAction
        variant="destructive"
        title="Delete?"
        description="Sure?"
        confirmLabel="Delete"
        onConfirm={() => {}}
      >
        <button>Trigger</button>
      </ConfirmAction>,
    );

    await userEvent.click(screen.getByText("Trigger"));
    const confirmBtn = screen.getByText("Delete");
    expect(confirmBtn.className).toContain("border-destructive");
  });
});
