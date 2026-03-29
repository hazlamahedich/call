import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { ConfirmAction } from "../confirm-action";

describe("[1.4-AC3][ConfirmAction] — Confirmation dialog with destructive and neutral variants", () => {
  it("[1.4-UNIT-056][P0] Given trigger clicked, When clicked, Then dialog opens with title and description", async () => {
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

  it("[1.4-UNIT-057][P1] Given variant=destructive, When dialog opens, Then destructive styling is applied to confirm button", async () => {
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

  it("[1.4-UNIT-058][P0] Given confirm clicked, When clicked, Then onConfirm callback fires", async () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmAction
        title="Confirm?"
        description="Proceed?"
        confirmLabel="Yes"
        onConfirm={onConfirm}
      >
        <button>Open</button>
      </ConfirmAction>,
    );

    await userEvent.click(screen.getByText("Open"));
    await userEvent.click(screen.getByText("Yes"));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("[1.4-UNIT-059][P1] Given variant=neutral, When dialog opens, Then neon-emerald styling is applied to confirm button", async () => {
    render(
      <ConfirmAction
        variant="neutral"
        title="Switch?"
        description="Change?"
        confirmLabel="Switch"
        onConfirm={() => {}}
      >
        <button>Trigger</button>
      </ConfirmAction>,
    );

    await userEvent.click(screen.getByText("Trigger"));
    const confirmBtn = screen.getByText("Switch");
    expect(confirmBtn.className).toContain("brand-primary");
  });

  it("[1.4-UNIT-060][P2] Given no custom labels, When dialog opens, Then default Confirm/Cancel labels are used", async () => {
    render(
      <ConfirmAction title="Test" description="Desc" onConfirm={() => {}}>
        <button>Open</button>
      </ConfirmAction>,
    );

    await userEvent.click(screen.getByText("Open"));
    expect(screen.getByText("Confirm")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("[1.4-UNIT-061][P2] Given custom labels, When dialog opens, Then custom confirmLabel and cancelLabel are used", async () => {
    render(
      <ConfirmAction
        title="Test"
        description="Desc"
        confirmLabel="Yes, do it"
        cancelLabel="Nope"
        onConfirm={() => {}}
      >
        <button>Open</button>
      </ConfirmAction>,
    );

    await userEvent.click(screen.getByText("Open"));
    expect(screen.getByText("Yes, do it")).toBeInTheDocument();
    expect(screen.getByText("Nope")).toBeInTheDocument();
  });

  it("[1.4-UNIT-062][P1] Given ConfirmAction, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <ConfirmAction title="Test" description="Desc" onConfirm={() => {}}>
        <button>Open</button>
      </ConfirmAction>,
    );

    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
