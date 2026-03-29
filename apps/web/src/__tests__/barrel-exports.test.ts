import { describe, it, expect } from "vitest";

describe("[CROSS-STORY][Barrel Exports] — Design system module export verification", () => {
  it("[EXPORT-001][P0] Given UI barrel, When imported, Then all primitives are exported", async () => {
    const ui = await import("../components/ui");

    expect(ui.Button).toBeDefined();
    expect(ui.buttonVariants).toBeDefined();
    expect(ui.Card).toBeDefined();
    expect(ui.CardHeader).toBeDefined();
    expect(ui.CardTitle).toBeDefined();
    expect(ui.CardDescription).toBeDefined();
    expect(ui.CardContent).toBeDefined();
    expect(ui.CardFooter).toBeDefined();
    expect(ui.Input).toBeDefined();
    expect(ui.StatusMessage).toBeDefined();
    expect(ui.EmptyState).toBeDefined();
    expect(ui.ConfirmAction).toBeDefined();
    expect(ui.FocusIndicator).toBeDefined();
    expect(ui.Dialog).toBeDefined();
    expect(ui.DialogTrigger).toBeDefined();
    expect(ui.DialogContent).toBeDefined();
    expect(ui.Tooltip).toBeDefined();
    expect(ui.TooltipTrigger).toBeDefined();
    expect(ui.TooltipContent).toBeDefined();
    expect(ui.TooltipProvider).toBeDefined();
    expect(ui.Popover).toBeDefined();
    expect(ui.PopoverTrigger).toBeDefined();
    expect(ui.PopoverContent).toBeDefined();
    expect(ui.ScrollArea).toBeDefined();
    expect(ui.Tabs).toBeDefined();
    expect(ui.TabsList).toBeDefined();
    expect(ui.TabsTrigger).toBeDefined();
    expect(ui.TabsContent).toBeDefined();
    expect(ui.Switch).toBeDefined();
  });

  it("[EXPORT-002][P0] Given Obsidian barrel, When imported, Then all signature components are exported", async () => {
    const obsidian = await import("../components/obsidian/index");

    expect(obsidian.CockpitContainer).toBeDefined();
    expect(obsidian.VibeBorder).toBeDefined();
    expect(obsidian.ContextTriad).toBeDefined();
    expect(obsidian.GlitchPip).toBeDefined();
    expect(obsidian.TelemetryStreamObsidian).toBeDefined();
  });

  it("[EXPORT-003][P1] Given UI barrel exports, When checked, Then all exports are truthy (not null/undefined)", async () => {
    const ui = await import("../components/ui");
    const exportNames = [
      "Button",
      "buttonVariants",
      "Card",
      "CardHeader",
      "CardTitle",
      "CardDescription",
      "CardContent",
      "CardFooter",
      "Input",
      "StatusMessage",
      "EmptyState",
      "ConfirmAction",
      "FocusIndicator",
      "Dialog",
      "DialogTrigger",
      "DialogContent",
      "Tooltip",
      "TooltipTrigger",
      "TooltipContent",
      "TooltipProvider",
      "Popover",
      "PopoverTrigger",
      "PopoverContent",
      "ScrollArea",
      "Tabs",
      "TabsList",
      "TabsTrigger",
      "TabsContent",
      "Switch",
    ];
    for (const name of exportNames) {
      expect(ui[name]).toBeDefined();
    }
  });

  it("[EXPORT-004][P1] Given Obsidian barrel exports, When checked, Then all exports are truthy (not null/undefined)", async () => {
    const obsidian = await import("../components/obsidian/index");
    const exportNames = [
      "CockpitContainer",
      "VibeBorder",
      "ContextTriad",
      "GlitchPip",
      "TelemetryStreamObsidian",
    ];
    for (const name of exportNames) {
      expect(obsidian[name]).toBeDefined();
    }
  });
});
