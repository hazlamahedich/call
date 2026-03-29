import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import path from "path";

const CSS_PATH = "../app/globals.css";

describe("[CROSS-STORY][Design Tokens] — globals.css token verification", () => {
  const cssContent = readFileSync(path.resolve(__dirname, CSS_PATH), "utf-8");

  const EXPECTED_TOKENS: Record<string, string> = {
    "--color-background": "#09090b",
    "--color-foreground": "#fafafa",
    "--color-card": "#18181b",
    "--color-neon-emerald": "#10b981",
    "--color-neon-crimson": "#f43f5e",
    "--color-neon-blue": "#3b82f6",
    "--color-border": "#27272a",
    "--color-ring": "#3b82f6",
    "--color-destructive": "#f43f5e",
  };

  const EXPECTED_CUSTOM_TOKENS = [
    "--color-glass",
    "--color-glass-heavy",
    "--blur-glass",
    "--border-glass",
    "--shadow-glow-emerald",
    "--shadow-glow-crimson",
    "--shadow-glow-blue",
    "--text-xs",
    "--text-sm",
    "--text-md",
    "--text-lg",
    "--text-2xl",
    "--duration-fast",
    "--duration-normal",
    "--duration-slow",
  ];

  it("[TOKEN-001][P0] Given core color tokens, When CSS is loaded, Then all Obsidian color tokens are defined", () => {
    for (const [token, value] of Object.entries(EXPECTED_TOKENS)) {
      expect(cssContent).toContain(token);
      expect(cssContent).toContain(value);
    }
  });

  it("[TOKEN-002][P1] Given glassmorphism tokens, When CSS is loaded, Then all glass tokens are defined", () => {
    for (const token of EXPECTED_CUSTOM_TOKENS) {
      expect(cssContent).toContain(token);
    }
  });

  it("[TOKEN-003][P1] Given animation keyframes, When CSS is loaded, Then pulse-emerald and jitter-crimson are defined", () => {
    expect(cssContent).toContain("pulse-emerald");
    expect(cssContent).toContain("jitter-crimson");
    expect(cssContent).toContain("glitch-pip");
    expect(cssContent).toContain("boot-glow");
  });

  it("[TOKEN-004][P2] Given animation utility classes, When CSS is loaded, Then animate-* classes reference keyframes", () => {
    expect(cssContent).toContain("animate-pulse-emerald");
    expect(cssContent).toContain("animate-jitter-crimson");
    expect(cssContent).toContain("animate-glitch-pip");
    expect(cssContent).toContain("animate-boot-glow");
  });

  it("[TOKEN-005][P1] Given typography scale, When CSS is loaded, Then text sizes matches UX spec", () => {
    expect(cssContent).toContain("--text-xs: 11px");
    expect(cssContent).toContain("--text-sm: 13px");
    expect(cssContent).toContain("--text-md: 16px");
    expect(cssContent).toContain("--text-lg: 20px");
    expect(cssContent).toContain("--text-2xl: 32px");
  });
});
