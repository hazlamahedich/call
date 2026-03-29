# Story 1.4: "Obsidian" Design System Foundation & Reusable Components

Status: complete (26/26 test suites, 217/217 tests green, code review passed, all findings fixed, pushed to origin)

## Story

As a UI Designer,
I want a base design system using Radix UI and the Obsidian theme,
so that all future features have a consistent and premium visual language.

## Acceptance Criteria

1. **Component Library**: Given the `apps/web` project, when I browse the component library, then foundational components `CockpitContainer`, `VibeBorder`, and `ContextTriad` are implemented with Glassmorphism effects. [Source: epics.md#Story 1.4]

2. **Obsidian Theme**: Given the component library, when any component renders, then colors align with `#09090B` Obsidian Black base and Neon Emerald (`#10B981`) / Crimson (`#F43F5E`) / Blue (`#3B82F6`) accent scheme. [Source: epics.md#Story 1.4]

3. **Typography** *(Verification Only — Already Configured)*: Given the design system, when components render text, then Geist Sans is used for headings/labels and Geist Mono for telemetry/data. Fonts are already loaded via `next/font/google` in `layout.tsx` — DO NOT reconfigure. [Source: epics.md#Story 1.4, ux-design-specification.md#Step 8]

4. **Reusable Primitives**: Given the design system, when building new pages, then primitive components (`Button`, `StatusMessage`, `EmptyState`, `ConfirmAction`, `FocusIndicator`) are available and composability-tested. [Source: epics.md#Epic 1, ux-design-specification.md#UX-DR15]

5. **Radix UI Integration**: Given the component library, when complex interactions are needed, then Radix UI primitives (`Dialog`, `Tooltip`, `Popover`, `ScrollArea`, `Tabs`, `Switch`) are wrapped with Obsidian-themed styling. [Source: ux-design-specification.md#Step 11]

6. **Accessibility**: Given the design system components, when evaluated for accessibility, then all interactive elements meet WCAG 2.1 AA with shape+color indicators, keyboard navigation, and ARIA attributes. [Source: ux-design-specification.md#Step 13, project-context.md]

7. **Existing Page Migration** *(GATED — Execute LAST after ACs 1-6 are stable)*: Given dashboard pages currently using hardcoded hex colors, when the design system is applied, then `clients/page.tsx` and `organizations/new/page.tsx` are refactored to use design system tokens instead of raw hex values. [Source: codebase analysis — styling inconsistency]

## Tasks / Subtasks

> **EXECUTION ORDER IS MANDATORY.** Tasks build on each other. Do not skip ahead.
> **GATE:** Do not start AC 7 (page migration) until ACs 1–6 are complete and component APIs are stable.

### Phase 1: Foundation (ACs 2, 3)

- [x] Install Radix UI primitives (AC: 5)
  - [x] Add `@radix-ui/react-dialog`, `@radix-ui/react-tooltip`, `@radix-ui/react-popover`, `@radix-ui/react-scroll-area`, `@radix-ui/react-tabs`, `@radix-ui/react-switch` to `apps/web/package.json`
  - [x] Verify no peer dependency conflicts with React 19 / Next.js 15

- [x] Expand design tokens in `globals.css` (AC: 2, 3)
  - [x] Add glassmorphism tokens: `--color-glass`, `--color-glass-heavy`, `--blur-glass`, `--border-glass`
  - [x] Add neon glow shadow tokens: `--shadow-glow-emerald`, `--shadow-glow-crimson`, `--shadow-glow-blue`
  - [x] Add typography scale tokens per UX spec: `--text-xs` (11px), `--text-sm` (13px), `--text-md` (16px), `--text-lg` (20px), `--text-2xl` (32px)
  - [x] Add animation tokens: `--duration-fast` (100ms), `--duration-normal` (300ms), `--duration-slow` (800ms), `--ease-default`, `--ease-bounce`
  - [x] Verify existing tokens (`--color-background`, `--color-neon-emerald`, etc.) remain unchanged

### Phase 2: Primitives (ACs 4, 6)

- [x] Create primitive UI components (AC: 4, 6)
  - [x] `apps/web/src/components/ui/button.tsx` — Button with variants: `primary` (neon emerald), `secondary` (zinc-800), `destructive` (crimson ghost), `ghost`; sizes: `sm`, `md`, `lg`; using CVA (`class-variance-authority` already installed)
  - [x] `apps/web/src/components/ui/status-message.tsx` — StatusMessage with variants: `success`, `warning`, `error`, `info`; includes icon + message slot
  - [x] `apps/web/src/components/ui/empty-state.tsx` — EmptyState with icon, title, description, and optional action slot
  - [x] `apps/web/src/components/ui/confirm-action.tsx` — ConfirmAction wrapping Radix Dialog with destructive/neutral variants
  - [x] `apps/web/src/components/ui/focus-indicator.tsx` — FocusIndicator with visible focus ring matching `--color-ring`
  - [x] `apps/web/src/components/ui/input.tsx` — Input with Obsidian styling, error state, and focus ring
  - [x] `apps/web/src/components/ui/card.tsx` — Card with glassmorphism variant and standard variant
  - [x] All primitives must use `cn()` from `@/lib/utils` and accept `className` prop
  - [x] All animated primitives must accept optional `reducedMotion?: boolean` prop to disable/simplify animations (future Vibe Slider integration per ux-design-specification.md#Step 12 §1.4)

### Phase 3: Radix Wrappers (ACs 5, 6)

- [x] Create Radix UI wrapped components (AC: 5, 6)
  - [x] `apps/web/src/components/ui/dialog.tsx` — Wraps `@radix-ui/react-dialog` with Obsidian glassmorphism styling
  - [x] `apps/web/src/components/ui/tooltip.tsx` — Wraps `@radix-ui/react-tooltip` with dark neon border styling
  - [x] `apps/web/src/components/ui/popover.tsx` — Wraps `@radix-ui/react-popover` for contextual menus
  - [x] `apps/web/src/components/ui/scroll-area.tsx` — Wraps `@radix-ui/react-scroll-area` with custom scrollbar
  - [x] `apps/web/src/components/ui/tabs.tsx` — Wraps `@radix-ui/react-tabs` with neon underline indicator
  - [x] `apps/web/src/components/ui/switch.tsx` — Wraps `@radix-ui/react-switch` with emerald active state

### Phase 4: Signature Obsidian Components (AC 1)

- [x] Create shared types for design system (AC: 1)
  - [x] Create `packages/types/transcript.ts` with `TranscriptEntry` interface (see Dev Notes §Missing Type)
  - [x] Add export to `packages/types/index.ts`
  - [x] Run `turbo run types:sync`

- [x] Create signature "Obsidian" components (AC: 1)
  - [x] `apps/web/src/components/obsidian/cockpit-container.tsx` — Top-level shell with translucent glass surface, 4x4 grid overlay, optional ambient neon glow pulse. Props: `active` (triggers boot animation), `onBootComplete` callback
  - [x] `apps/web/src/components/obsidian/vibe-border.tsx` — Reactive emotional border. States: `neutral` (zinc), `positive` (emerald pulse 800ms), `hostile` (crimson jitter). Must include ARIA live region for sentiment changes. Props: `sentiment: 'neutral' | 'positive' | 'hostile'`, `reducedMotion?: boolean`
    - **Hostile animation MUST feel aggressive and irregular** — NOT a smooth sine wave. Use stepped, glitchy keyframes with uneven timing (e.g., `0%, 10%, 40%, 45%, 100%` with abrupt translateX jumps of varying magnitude ±1-3px). Combine with irregular `box-shadow` bursts. See VibeBorder CSS Keyframes section below.
  - [x] `apps/web/src/components/obsidian/context-triad.tsx` — High-contrast 3-bullet tactical briefing in Geist Mono. Props: `why: string`, `mood: string`, `target: string`. Automatically appears during binaural-whoosh phase.
    - **Rendering spec:** Each bullet renders with an ALL-CAPS label in Geist Mono 11px (`--text-xs`) followed by the prop value: `WHY: {why}`, `MOOD: {mood}`, `TARGET: {target}`. Labels use `text-muted-foreground uppercase tracking-[0.05em]`. Values use `text-foreground font-mono text-sm`. [Source: ux-design-specification.md#Step 8 — Labels: 11px All-Caps]
  - [x] `apps/web/src/components/obsidian/glitch-pip.tsx` — 4x4px micro-indicator with coded-redaction CSS keyframe. Props: `active: boolean`, `reducedMotion?: boolean`.
    - **Visual intention:** At 4×4px, the animation should create a "data corruption" effect: rapid opacity flicker (0→1→0.5→1 at 60ms intervals) combined with a 1px horizontal `translateX` slide, giving the impression of a tiny corrupted data block. Use `rgba(244, 63, 94, 0.6→1.0)` crimson with occasional brief white flash (1 frame). When `reducedMotion=true`, render as a static crimson dot with no animation.
  - [x] `apps/web/src/components/obsidian/telemetry-stream.tsx` — Optimized transcript feed using Geist Mono 13px (`--text-sm`). Props: `entries: TranscriptEntry[]`, `onScrollBottom` callback, `reducedMotion?: boolean`. Uses bottom-anchored scrolling (newest at bottom, auto-scrolls down) per UX-DR18 "Telemetry Anchor".

### Phase 5: Barrel Exports & Types (AC 4)
  - [x] Create `apps/web/src/components/ui/index.ts` exporting all primitives
  - [x] Create `apps/web/src/components/obsidian/index.ts` exporting signature components

### Phase 6: Page Migration — GATED (AC 7)

> **GATE:** Do not start this phase until Phase 1–5 are complete and component APIs are stable.
> Premature migration against an unstable API causes double-refactoring.

- [x] Refactor `apps/web/src/app/(dashboard)/dashboard/clients/page.tsx` — replace hardcoded hex (`bg-[#09090B]`, `border-[#27272A]`, `bg-[#18181B]`, `bg-[#10B981]`) with semantic tokens (`bg-background`, `border-border`, `bg-card`, `bg-neon-emerald`)
- [x] Refactor `apps/web/src/app/(dashboard)/dashboard/organizations/new/page.tsx` — same hex-to-token migration
- [x] Replace inline button elements with `<Button>` component
- [x] Replace inline status messages with `<StatusMessage>` component
- [x] Verify visual regression: pages must look identical after refactor

### Phase 7: Command Center Refactor (AC 1, 4)

- [x] Update existing Command Center components to use shared primitives (AC: 1, 4)
  - [x] Refactor `FleetNavigator.tsx` — extract reusable sidebar pattern, use `<Button>` and `<Card>`
  - [x] Refactor `TelemetryStream.tsx` — use `<ScrollArea>` from Radix, `<Card>` for wrapper
  - [x] Refactor `RejectionShield.tsx` — use `<Card>` and `<StatusMessage>`
  - [x] Maintain backward compatibility — `command-center/page.tsx` must work unchanged

### Phase 8: Component Tests (AC 4, 6)

- [x] Install `vitest-axe` for automated accessibility testing: `pnpm add -D vitest-axe --filter web`
- [x] Write component tests in `apps/web/src/components/ui/__tests__/`
  - [x] `button.test.tsx` — Test: (a) each variant applies correct CSS class, (b) `disabled` state prevents interaction and applies `disabled:opacity-20`, (c) `asChild` forwarding works if used. **Do NOT test all 12 variant×size permutations** — CVA is a well-tested library.
  - [x] `card.test.tsx` — Test standard variant and glassmorphism variant render correct classes
  - [x] `input.test.tsx` — Test error state applies `aria-invalid` and error styling
  - [x] `status-message.test.tsx` — Test all 4 variants render correct icon + message
  - [x] `empty-state.test.tsx` — Test icon, title, description, and optional action slot
  - [x] `confirm-action.test.tsx` — Test dialog open/close cycle, destructive vs neutral variant
  - [x] `dialog.test.tsx` — Test Obsidian styling applied; **do NOT test Radix keyboard nav** (Radix tests their own)
  - [x] `tabs.test.tsx` — Test neon underline indicator styling applied
  - [x] `switch.test.tsx` — Test emerald active state styling applied
- [x] Write Obsidian component tests in `apps/web/src/components/obsidian/__tests__/`
  - [x] `cockpit-container.test.tsx` — Test boot animation triggers on `active` prop change
  - [x] `vibe-border.test.tsx` — Test: (a) correct CSS class per sentiment state, (b) `aria-live="polite"` exists, (c) ARIA live region text updates on sentiment change. **Do NOT test CSS keyframe values in jsdom** — animation is CSS-only.
  - [x] `context-triad.test.tsx` — Test all 3 bullets render with ALL-CAPS labels (`WHY:`, `MOOD:`, `TARGET:`)
  - [x] `glitch-pip.test.tsx` — Test: (a) renders as 4×4px, (b) `active` prop toggles animation class, (c) `reducedMotion` renders static dot
- [x] Run automated accessibility audit: `axe()` from `vitest-axe` on all interactive components — pattern: `const results = await axe(container); expect(results.violations).toHaveLength(0);`
- [x] Verify all interactive elements have `focus-visible:ring-2 focus-visible:ring-ring`
- [x] Coverage target: >80% for design system components
- [x] Expanded test automation (2026-03-29): 5 new test suites (Tooltip, ScrollArea, Popover, FocusIndicator, TelemetryStreamObsidian), 13 existing suites enhanced with accessibility audits, design token verification, and interaction tests
- [x] Test quality review remediated (2026-03-29): All 21 test suites rewritten with BDD Given/When/Then naming, `[1.4-UNIT-XXX]` traceability IDs, `[P0]`/`[P1]`/`[P2]` priority markers. CockpitContainer `setTimeout` replaced with `vi.useFakeTimers` + `vi.advanceTimersByTime(300)`. Created `createTranscriptEntry()` data factory. Quality score: 97/100 (A+ - Excellent). See `_bmad-output/test-artifacts/story-1-4-test-quality-review.md`.
- [x] Command Center component tests created (2026-03-29): FleetNavigator (10 tests), TelemetryStream (11 tests), RejectionShield (11 tests) — previously deferred as P2
- [x] Design token verification tests (2026-03-29): `__tests__/design-tokens.test.ts` reads `globals.css` via `readFileSync` and asserts all 18 design tokens present
- [x] Barrel export verification tests (2026-03-29): `__tests__/barrel-exports.test.ts` dynamically imports `ui/index.ts` and `obsidian/index.ts`, verifies all named exports resolve
- [x] E2E page navigation tests (2026-03-29): `tests/e2e/pages.spec.ts` — homepage render, command-center navigation (7 tests)
- [x] All 26 test suites passing, 217/217 tests green.

## Dev Notes

### Architecture Compliance

- **UI Framework**: Next.js 15 App Router, Vanilla CSS via Tailwind v4. [Source: project-context.md]
- **Design System**: Radix UI (logic/accessibility) + Vanilla CSS (Obsidian aesthetic). NO shadcn/ui. [Source: ux-design-specification.md#Step 6]
- **Styling**: Tailwind v4 with `@theme` block in `globals.css` for tokens. All custom CSS uses `@apply` or utility classes. [Source: codebase analysis]
- **Fonts**: Geist Sans (UI), Geist Mono (telemetry) — already loaded via `next/font/google` in `layout.tsx`. [Source: layout.tsx]

### CRITICAL: What Already Exists — DO NOT recreate

These are already implemented and working:

| Item | Location | Status |
|------|----------|--------|
| Tailwind v4 with `@theme` tokens | `apps/web/src/app/globals.css` | 8 color tokens, 6 spacing tokens, font vars, 4 radius tokens |
| Geist Sans + Geist Mono fonts | `apps/web/src/app/layout.tsx` | Loaded via `next/font/google`, CSS vars `--font-geist-sans`, `--font-geist-mono` |
| `cn()` utility | `apps/web/src/lib/utils.ts` | `clsx` + `tailwind-merge` |
| CVA (`class-variance-authority`) | `apps/web/package.json` | Installed but NOT used yet |
| `lucide-react` icons | `apps/web/package.json` | v0.577.0 installed |
| 3 Command Center components | `apps/web/src/components/command-center/` | FleetNavigator, TelemetryStream, RejectionShield — use semantic tokens |
| Design system tokens doc | `design-artifacts/D-Design-System/00-design-system.md` | 8 color tokens, typography scale, spacing tokens |

### Existing Styling Inconsistencies to Fix

Dashboard pages (`clients/page.tsx`, `organizations/new/page.tsx`) use **hardcoded hex colors** instead of semantic tokens:
- `bg-[#09090B]` → should be `bg-background`
- `border-[#27272A]` → should be `border-border`
- `bg-[#18181B]` → should be `bg-card`
- `bg-[#10B981]` → should be `bg-neon-emerald`
- `text-[#71717A]` → should be `text-muted-foreground`

Command Center pages already use semantic tokens correctly. This story MUST normalize all pages.

### Radix UI Integration Pattern

Wrap Radix primitives with Obsidian styling — DO NOT abstract away Radix's API:

```tsx
// apps/web/src/components/ui/dialog.tsx
"use client"

import * as DialogPrimitive from "@radix-ui/react-dialog"
import { cn } from "@/lib/utils"

const Dialog = DialogPrimitive.Root
const DialogTrigger = DialogPrimitive.Trigger
const DialogClose = DialogPrimitive.Close
const DialogPortal = DialogPrimitive.Portal

const DialogOverlay = ({ className, ...props }) => (
  <DialogPrimitive.Overlay
    className={cn(
      "fixed inset-0 z-50 bg-background/80 backdrop-blur-sm",
      "data-[state=open]:animate-in data-[state=closed]:animate-out",
      className
    )}
    {...props}
  />
)

const DialogContent = ({ className, ...props }) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      className={cn(
        "fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2",
        "w-full max-w-lg rounded-lg border border-border bg-card p-lg",
        "shadow-[0_0_30px_rgba(0,0,0,0.5)]",
        className
      )}
      {...props}
    />
  </DialogPortal>
)
```

### CVA Button Pattern (class-variance-authority)

CVA is already in `package.json` but unused. Use it for Button:

```tsx
// apps/web/src/components/ui/button.tsx
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-20",
  {
    variants: {
      variant: {
        primary: "bg-neon-emerald text-background shadow-[0_0_8px_rgba(16,185,129,0.5)] hover:bg-neon-emerald/90",
        secondary: "border border-border bg-transparent text-foreground hover:bg-muted",
        destructive: "border border-destructive/50 bg-transparent text-destructive hover:bg-destructive/10",
        ghost: "text-muted-foreground hover:text-foreground hover:bg-muted",
      },
      size: {
        sm: "h-8 px-sm text-xs",
        md: "h-10 px-md text-sm",
        lg: "h-12 px-lg text-base",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
)
```

### VibeBorder CSS Keyframes

```css
/* Add to globals.css @theme or @layer utilities */
@keyframes pulse-emerald {
  0%, 100% { box-shadow: 0 0 4px rgba(16, 185, 129, 0.3); }
  50% { box-shadow: 0 0 12px rgba(16, 185, 129, 0.6); }
}

/* CRITICAL: Hostile jitter MUST be irregular and aggressive — NOT a smooth sine wave.
   The uneven keyframe stops (0%, 10%, 40%, 45%, 100%) create a glitchy,
   unpredictable feel. The varying translateX magnitudes (±1-3px) prevent
   any sense of rhythm — this is "jagged", not "wobble". */
@keyframes jitter-crimson {
  0%, 10% { transform: translateX(0); box-shadow: 0 0 4px rgba(244, 63, 94, 0.3); }
  15% { transform: translateX(-2px); box-shadow: 0 0 8px rgba(244, 63, 94, 0.5); }
  40% { transform: translateX(1px); }
  45% { transform: translateX(-3px); box-shadow: 0 0 12px rgba(244, 63, 94, 0.7); }
  50% { transform: translateX(0); box-shadow: 0 0 4px rgba(244, 63, 94, 0.3); }
  100% { transform: translateX(0); box-shadow: 0 0 4px rgba(244, 63, 94, 0.3); }
}
```

### Animation Testing Strategy

> **IMPORTANT:** CSS keyframes cannot be meaningfully unit-tested in jsdom.
> The dev agent MUST NOT attempt to assert `transform: translateX(-2px)` in Vitest.
>
> **What to test:**
> - Correct CSS class is applied per state (e.g., `vibe-border--hostile` class exists)
> - `aria-live="polite"` attribute is present on VibeBorder
> - ARIA live region text content updates when `sentiment` prop changes
> - `reducedMotion` prop applies static styling instead of animation class
>
> **What NOT to test:**
> - Animation frame values (CSS-only, not testable in jsdom)
> - Radix UI keyboard navigation (Radix tests their own components)
> - CVA variant×size matrix exhaustively (CVA is a well-tested library)
>
> Animation correctness should be verified via **visual review** or **Playwright screenshot comparison** during Phase 6 (page migration).

### Reduced Motion Prop Pattern

All animated components MUST accept an optional `reducedMotion?: boolean` prop:

```tsx
// Pattern for all animated components
const VibeBorder = ({ sentiment, reducedMotion = false, className }) => {
  const animationClass = reducedMotion
    ? "border-2"  // Static border, no animation
    : cn({
        "animate-pulse-emerald": sentiment === "positive",
        "animate-jitter-crimson": sentiment === "hostile",
      })

  return (
    <div
      className={cn("border-2 border-zinc-700", animationClass, className)}
      aria-live="polite"
      aria-label={`Sentiment: ${sentiment}`}
    />
  )
}
```

This prop prepares components for the future "Vibe Intensity Slider" (UX Step 12 §1.4) without implementing the slider itself. The app will eventually read `prefers-reduced-motion` media query and/or a user preference from a context provider.

### Glassmorphism Pattern

```tsx
// Glass card styling
className={cn(
  "bg-card/40 backdrop-blur-md border border-border/50",
  "shadow-[0_0_30px_rgba(0,0,0,0.3)]",
  "rounded-lg"
)}
```

### Accessibility Requirements (WCAG 2.1 AA)

Every interactive component MUST:
1. Have `focus-visible:ring-2 focus-visible:ring-ring` for keyboard users
2. Use shape+color for state (not color alone) — e.g., GlitchPip has icon + color
3. VibeBorder uses ARIA live region: `aria-live="polite"` for sentiment changes
4. Dialog traps focus, returns focus on close
5. Switch has `aria-label` or associated label
6. Test keyboard navigation: Tab, Enter, Space, Escape — **custom components only**, not Radix wrappers

### Party Mode Review (2026-03-29)

Post-creation review by Winston (Architect), Sally (UX), Amelia (Dev), Murat (Test Architect), John (PM).

**Critical fixes applied:**
- AC 7 gated behind component API stability — page migration is Phase 6, executes LAST
- VibeBorder hostile animation redefined: irregular glitchy keyframes, NOT smooth sine wave
- GlitchPip 4x4px animation specified: rapid opacity flicker + 1px translateX "data corruption" effect
- AC 3 marked as verification-only (fonts already configured)
- Task ordering made explicit: Tokens → Primitives → Radix wrappers → Obsidian components → Exports → Migration
- TranscriptEntry type creation elevated to explicit subtask

**Enhancements applied:**
- `reducedMotion` prop pattern added to all animated components (future Vibe Slider readiness)
- Testing strategy overhauled: automated `vitest-axe` replaces manual accessibility checks
- Animation testing strategy documented: test CSS class + ARIA, not keyframe values
- CVA test strategy optimized: 3-4 targeted tests instead of 12 permutation tests
- Radix keyboard test strategy: skip (Radix tests their own), focus on custom components
- ContextTriad label rendering specified: ALL-CAPS Geist Mono 11px labels

### Previous Story Learnings

**From Story 1-1:**
- Monorepo established with Turborepo + pnpm
- `apps/web` uses Next.js 15 App Router + Tailwind v4 + Vanilla CSS
- `apps/api` uses FastAPI + SQLModel
- Testing: Playwright (E2E), Vitest (frontend unit), Pytest (backend)

**From Story 1-2:**
- Clerk auth integrated with ClerkProvider in root layout
- `class-variance-authority` installed but unused
- `lucide-react` v0.577.0 installed for icons
- `clsx` + `tailwind-merge` available via `cn()` utility
- Dashboard pages (`clients/`, `organizations/new/`) use hardcoded hex — inconsistent with command center
- No shared layout components — each page handles its own layout
- No component library or reusable primitives yet
- Vitest configured in `apps/web/vitest.config.ts` for frontend unit tests

**From Story 1-3:**
- Backend RLS fully implemented
- No frontend changes from 1-3
- `packages/types/tenant.ts` added tenant TypeScript interfaces

### Type Collision Warning

`Call` type is defined in both `packages/types/call.ts` and `packages/types/tenant.ts`. When building components that reference call data, explicitly import from one source to avoid confusion. This is a pre-existing issue — do NOT fix it in this story.

### Missing Type: TranscriptEntry

The `TelemetryStream` component references `TranscriptEntry[]` but this type does not yet exist in `packages/types`. The dev agent MUST create `packages/types/transcript.ts` with:

```typescript
export interface TranscriptEntry {
  id: string;
  role: "assistant-ai" | "assistant-human" | "lead";
  text: string;
  timestamp: number;
  sentiment?: "positive" | "neutral" | "hostile";
}
```

Add the export to `packages/types/index.ts`. This aligns with the `role` tagging pattern from architecture.md#Step 7 (Role Tagging: `assistant-human` / `assistant-ai`).

### Testing Standards

- **Unit Tests**: Vitest in `apps/web/src/components/*/`, following the targeted test strategy in Phase 8
- **Accessibility Tests**: `vitest-axe` `axe()` + `results.violations` assertion on all interactive components (automated, not manual). NOTE: `vitest-axe` does NOT export `toHaveNoViolations` — use `const results = await axe(container); expect(results.violations).toHaveLength(0);`
- **Visual Regression**: Verify refactored pages look identical via Playwright screenshot comparison during Phase 6
- **Animation Tests**: Test CSS class application + ARIA attributes only. DO NOT test keyframe values in jsdom — see Animation Testing Strategy section
- **Coverage Target**: >80% for design system components
- **Keyboard Tests**: Focus on custom components only (VibeBorder, CockpitContainer, GlitchPip). Radix UI tests their own keyboard navigation — do not duplicate.

### File Structure

```
apps/web/src/
├── app/
│   ├── globals.css                    # EXPAND: add glassmorphism, glow, animation tokens
│   ├── layout.tsx                     # NO CHANGES (fonts already configured)
│   ├── (dashboard)/
│   │   └── dashboard/
│   │       ├── clients/page.tsx       # REFACTOR: hex → tokens, use Button/StatusMessage
│   │       └── organizations/new/page.tsx  # REFACTOR: hex → tokens, use Button/Input
│   └── command-center/page.tsx        # NO CHANGES
├── components/
│   ├── ui/                            # NEW — Primitives
│   │   ├── index.ts                   # Barrel export
│   │   ├── button.tsx                 # CVA variants
│   │   ├── card.tsx                   # Standard + glass variant
│   │   ├── input.tsx                  # Input with error state
│   │   ├── status-message.tsx         # Success/warning/error/info
│   │   ├── empty-state.tsx            # Icon + title + description + action
│   │   ├── confirm-action.tsx         # Radix Dialog wrapper
│   │   ├── focus-indicator.tsx        # Focus ring wrapper
│   │   ├── dialog.tsx                 # Radix Dialog Obsidian wrapper
│   │   ├── tooltip.tsx                # Radix Tooltip Obsidian wrapper
│   │   ├── popover.tsx                # Radix Popover Obsidian wrapper
│   │   ├── scroll-area.tsx            # Radix ScrollArea Obsidian wrapper
│   │   ├── tabs.tsx                   # Radix Tabs Obsidian wrapper
│   │   ├── switch.tsx                 # Radix Switch Obsidian wrapper
│   │   └── __tests__/                 # Component tests
│   │       ├── button.test.tsx
│   │       ├── card.test.tsx
│   │       ├── input.test.tsx
│   │       ├── status-message.test.tsx
│   │       ├── empty-state.test.tsx
│   │       ├── confirm-action.test.tsx
│   │       ├── focus-indicator.test.tsx  # NEW (test automation)
│   │       ├── dialog.test.tsx
│   │       ├── tooltip.test.tsx          # NEW (test automation)
│   │       ├── popover.test.tsx          # NEW (test automation)
│   │       ├── scroll-area.test.tsx      # NEW (test automation)
│   │       ├── tabs.test.tsx
│   │       └── switch.test.tsx
│   ├── obsidian/                      # NEW — Signature components
│   │   ├── index.ts                   # Barrel export
│   │   ├── cockpit-container.tsx      # Glass shell + boot animation
│   │   ├── vibe-border.tsx            # Sentiment-reactive border
│   │   ├── context-triad.tsx          # 3-bullet tactical briefing
│   │   ├── glitch-pip.tsx             # 4x4px coded-redaction indicator
│   │   ├── telemetry-stream.tsx       # Transcript feed (refactored from command-center/)
│   │   └── __tests__/                 # Component tests
│   │       ├── cockpit-container.test.tsx
│   │       ├── vibe-border.test.tsx
│   │       ├── context-triad.test.tsx
│   │       ├── glitch-pip.test.tsx
│   │       └── telemetry-stream.test.tsx  # NEW (test automation)
│   └── command-center/                # REFACTOR: use shared primitives
│       ├── FleetNavigator.tsx         # Use Card, Button
│       ├── TelemetryStream.tsx        # Use ScrollArea, Card
│       └── RejectionShield.tsx        # Use Card, StatusMessage
├── lib/
│   └── utils.ts                       # NO CHANGES (cn() already exists)
└── middleware.ts                       # NO CHANGES
```

### References

- [Epic: epics.md#Epic 1 — Story 1.4]
- [UX Design System: ux-design-specification.md#Step 6 — Radix UI + Vanilla CSS]
- [UX Color System: ux-design-specification.md#Step 8 — Obsidian & Neon]
- [UX Components: ux-design-specification.md#Step 11 — Component Strategy]
- [UX Consistency: ux-design-specification.md#Step 12 — Button Hierarchy & Feedback]
- [UX Accessibility: ux-design-specification.md#Step 13 — WCAG AA]
- [Design Tokens: design-artifacts/D-Design-System/00-design-system.md]
- [User Journey: design-artifacts/USER-JOURNEY-WORKFLOW.md — Component Hierarchy]
- [Architecture: architecture.md#Step 5 — Implementation Patterns]
- [Project Context: project-context.md — Technology Stack]
- [Previous Story 1-2: 1-2-multi-layer-hierarchy-clerk-auth-integration.md — styling inconsistencies]
- [Existing CSS: apps/web/src/app/globals.css — current token definitions]

## Dev Agent Record

### Agent Model Used

Claude (claude-sonnet-4-20250514) via opencode

### Debug Log References

- Pre-existing peer dependency warnings for @clerk/nextjs (React 19 / Next.js 15 version mismatch) — not caused by our changes
- Pre-existing TS errors in `organization.test.ts` (FeatureSettings type mismatch) — not related to our work
- ESLint config is empty — no lint rules enforced currently

### Completion Notes List

1. All 8 phases completed in order: Foundation → Primitives → Radix Wrappers → Obsidian Components → Exports → Page Migration → Command Center Refactor → Tests
2. Test automation expanded (2026-03-29): **26 test suites, 217 tests, all passing**
3. Test quality review remediated (2026-03-29): All suites rewritten with BDD naming, traceability IDs, priority markers, fake timers, data factory. **217/217 tests passing, quality score 97/100 (A+)**
4. TypeScript strict mode passes with zero new errors
5. Installed `@testing-library/user-event` (was missing, needed by confirm-action tests)
6. Fixed TS error in migrated `clients/page.tsx` — cast `userRole` from `string` to `OrgRole`
7. Vitest config updated: environment changed from `node` to `jsdom`, added setup file and path aliases
8. `vitest-axe` installed for automated accessibility testing
9. All animated components accept `reducedMotion?: boolean` prop per spec
10. VibeBorder hostile animation uses irregular/glitchy keyframes (not smooth sine wave) per spec
11. CVA test strategy: targeted 3-4 tests per component, not full variant×size matrix
12. No Radix keyboard navigation tests (Radix tests their own)
13. No CSS keyframe value assertions in jsdom (tested CSS class + ARIA only)
14. **5 new test suites created:** Tooltip, ScrollArea, Popover, FocusIndicator, TelemetryStreamObsidian
15. **13 existing test suites enhanced** with axe accessibility audits, design token assertions, and interaction coverage
16. **jsdom/Radix discoveries documented** in `test-automation-summary-1-4.md` — workarounds for `scrollIntoView`, Radix double-render, `aria-modal`, `data-orientation`, PopoverContent wrapper
17. **Command Center component tests created** (previously deferred as P2): FleetNavigator (10 tests), TelemetryStream (11 tests), RejectionShield (11 tests)
18. **Test quality review remediated** (2026-03-29): BDD Given/When/Then naming, `[1.4-UNIT-XXX]` traceability IDs, `[P0]`/`[P1]`/`[P2]` priority markers applied to all tests
19. **CockpitContainer**: `setTimeout` replaced with `vi.useFakeTimers` + `vi.advanceTimersByTime(300)` — deterministic, no flakiness
20. **Data factory**: `createTranscriptEntry()` created at `apps/web/src/test/factories/transcript.ts`
21. **Fake timer + axe conflict resolved**: `vi.useRealTimers()` called before axe audit test to prevent async hang
22. Quality score: 87/100 → 97/100 (A+ - Excellent). All 6 violations resolved. Approved.
23. **Sentiment enum alignment**: Command center page `negative` → `hostile` to match TelemetryStream prop type and TranscriptEntry type
24. **barrel-exports test fix**: TS7053 dynamic index error resolved with `Record<string, unknown>` type assertion
25. **organization.test.ts fix**: FeatureSettings type corrected from `string[]` to `{ featureName: boolean }` object
26. **Design token verification**: dedicated test reads `globals.css` via `fs.readFileSync` (CSS `?raw` imports don't work in Vitest)
27. **Code review fixes committed and pushed** (7e66936): sentiment enum, hex→token migration, button opacity (50%), confirm-action dialog close, jitter animation keyframes

### File List

**NEW files (52):**
- `apps/web/vitest.setup.ts`
- `apps/web/src/test/factories/transcript.ts` *(test quality remediation — data factory)*
- `apps/web/src/components/ui/button.tsx`
- `apps/web/src/components/ui/card.tsx`
- `apps/web/src/components/ui/input.tsx`
- `apps/web/src/components/ui/status-message.tsx`
- `apps/web/src/components/ui/empty-state.tsx`
- `apps/web/src/components/ui/confirm-action.tsx`
- `apps/web/src/components/ui/focus-indicator.tsx`
- `apps/web/src/components/ui/dialog.tsx`
- `apps/web/src/components/ui/tooltip.tsx`
- `apps/web/src/components/ui/popover.tsx`
- `apps/web/src/components/ui/scroll-area.tsx`
- `apps/web/src/components/ui/tabs.tsx`
- `apps/web/src/components/ui/switch.tsx`
- `apps/web/src/components/ui/index.ts`
- `apps/web/src/components/obsidian/cockpit-container.tsx`
- `apps/web/src/components/obsidian/vibe-border.tsx`
- `apps/web/src/components/obsidian/context-triad.tsx`
- `apps/web/src/components/obsidian/glitch-pip.tsx`
- `apps/web/src/components/obsidian/telemetry-stream.tsx`
- `apps/web/src/components/obsidian/index.ts`
- `apps/web/src/components/ui/__tests__/button.test.tsx`
- `apps/web/src/components/ui/__tests__/card.test.tsx`
- `apps/web/src/components/ui/__tests__/input.test.tsx`
- `apps/web/src/components/ui/__tests__/status-message.test.tsx`
- `apps/web/src/components/ui/__tests__/empty-state.test.tsx`
- `apps/web/src/components/ui/__tests__/confirm-action.test.tsx`
- `apps/web/src/components/ui/__tests__/dialog.test.tsx`
- `apps/web/src/components/ui/__tests__/tabs.test.tsx`
- `apps/web/src/components/ui/__tests__/switch.test.tsx`
- `apps/web/src/components/ui/__tests__/tooltip.test.tsx` *(test automation)*
- `apps/web/src/components/ui/__tests__/scroll-area.test.tsx` *(test automation)*
- `apps/web/src/components/ui/__tests__/popover.test.tsx` *(test automation)*
- `apps/web/src/components/ui/__tests__/focus-indicator.test.tsx` *(test automation)*
- `apps/web/src/components/obsidian/__tests__/cockpit-container.test.tsx`
- `apps/web/src/components/obsidian/__tests__/vibe-border.test.tsx`
- `apps/web/src/components/obsidian/__tests__/context-triad.test.tsx`
- `apps/web/src/components/obsidian/__tests__/glitch-pip.test.tsx`
- `apps/web/src/components/obsidian/__tests__/telemetry-stream.test.tsx` *(test automation)*
- `apps/web/src/components/command-center/__tests__/FleetNavigator.test.tsx` *(tea-automate)*
- `apps/web/src/components/command-center/__tests__/TelemetryStream.test.tsx` *(tea-automate)*
- `apps/web/src/components/command-center/__tests__/RejectionShield.test.tsx` *(tea-automate)*
- `apps/web/src/__tests__/design-tokens.test.ts` *(tea-automate — design token verification)*
- `apps/web/src/__tests__/barrel-exports.test.ts` *(tea-automate — barrel export verification)*
- `tests/e2e/pages.spec.ts` *(tea-automate — E2E page navigation)*
- `packages/types/transcript.ts`
- `_bmad-output/test-artifacts/story-1-4-test-quality-review.md` *(test quality review report)*
- `_bmad-output/test-artifacts/storiess-1-4-automation-summary.md` *(tea-automate summary)*
- `_bmad-output/test-artifacts/stories-1-through-1-4-automation-summary.md` *(expanded tea-automate summary)*
- `_bmad-output/implementation-artifacts/test-automation-summary-1-4.md` *(automation report)*

**MODIFIED files (16):**
- `apps/web/package.json` (added 6 Radix UI packages, testing libs, user-event)
- `apps/web/vitest.config.ts` (jsdom env, setup file, path aliases)
- `apps/web/src/app/globals.css` (glassmorphism, glow, typography, animation tokens + keyframes)
- `apps/web/src/app/(dashboard)/dashboard/clients/page.tsx` (hex→tokens, design system components)
- `apps/web/src/app/(dashboard)/dashboard/organizations/new/page.tsx` (hex→tokens, design system components)
- `apps/web/src/app/command-center/page.tsx` (sentiment enum: negative→hostile)
- `apps/web/src/components/command-center/FleetNavigator.tsx` (Button, Card)
- `apps/web/src/components/command-center/TelemetryStream.tsx` (Card, Button, ScrollArea, sentiment enum fix)
- `apps/web/src/components/command-center/RejectionShield.tsx` (Card, StatusMessage)
- `apps/web/src/components/ui/button.tsx` (disabled opacity 50%)
- `apps/web/src/components/ui/confirm-action.tsx` (dialog close fix)
- `apps/web/src/components/obsidian/cockpit-container.tsx` (boot state reset, ref for onBootComplete)
- `apps/web/src/components/obsidian/vibe-border.tsx` (props spread order fix)
- `apps/web/src/components/obsidian/telemetry-stream.tsx` (refs, scroll guard, timestamp/role guards)
- `packages/types/index.ts` (added transcript export)
- `apps/web/src/actions/organization.test.ts` (FeatureSettings type fix)

### Change Log

- 2026-03-29: Story completed. All 8 phases done. 74/74 tests pass. Zero new TS errors. Status → review.
- 2026-03-29: Test automation expanded via bmad-testarch-automate workflow. 5 new test suites (Tooltip, ScrollArea, Popover, FocusIndicator, TelemetryStreamObsidian). 13 existing suites enhanced with axe accessibility, design token checks, and interaction tests. 21/21 suites passing, 175/175 tests green. See `test-automation-summary-1-4.md`.
- 2026-03-29: Test quality review (bmad-testarch-test-review) scored 87/100. All 6 violations remediated: BDD naming, traceability IDs, priority markers, fake timers, data factory. 21/21 suites passing, 176/176 tests green. Score → 97/100 (A+). See `_bmad-output/test-artifacts/story-1-4-test-quality-review.md`.
- 2026-03-29: Code review (bmad-code-review) via 3 adversarial layers (Blind Hunter, Edge Case Hunter, Acceptance Auditor). All 7 ACs PASS. 14 patch findings identified, all fixed. 8 pre-existing issues deferred. 176/176 tests green post-fix.
  - **fix(confirm-action):** Wrapped confirm button in `DialogPrimitive.Close` — dialog now closes on confirm (was staying open)
  - **fix(TelemetryStream):** Aligned sentiment enum `"negative"` → `"hostile"` to match canonical `TranscriptEntry` type
  - **fix(cockpit-container):** Reset `booted` state when `active` goes false; stored `onBootComplete` in ref to prevent effect churn
  - **fix(orgs/new):** Added `htmlFor`/`id` pairs on all 3 labels (WCAG 1.3.1); extracted duplicated select `className` to `selectClassName` constant
  - **fix(globals.css):** Changed jitter animation from `steps(1)` to `steps(4, start)` to preserve irregular keyframe detail
  - **fix(button):** Changed `disabled:opacity-20` → `disabled:opacity-50` for dark-theme visibility
  - **fix(vibe-border):** Moved `{...props}` spread before explicit `aria-live`/`aria-label` to prevent a11y override
  - **fix(telemetry-stream):** Used refs for `onScrollBottom` callback; only scrolls on entry count change; guarded timestamp against NaN/Infinity and role against undefined
  - **fix(clients/page):** Added `deleting` boolean state to prevent concurrent delete race condition
- 2026-03-29: tea-automate expanded to stories 1-1 through 1-4. 5 new test suites created (Command Center: FleetNavigator 10 tests, TelemetryStream 11 tests, RejectionShield 11 tests; Cross-cutting: design-tokens 5 tests, barrel-exports 4 tests). 26/26 suites, 217/217 tests green. All committed and pushed.
- 2026-03-29: Code review fixes committed and pushed (7e66936). Sentiment enum alignment (negative→hostile), hex→token migration for clients/orgs pages, button disabled opacity 50%, confirm-action dialog close, jitter animation keyframes.
- 2026-03-29: BDD test rewrites committed (e036068). All 13 UI + Obsidian test suites rewritten with `[1.4-UNIT-XXX]` traceability IDs and BDD Given/When/Then naming. Fixed TS errors: barrel-exports `Record<string, unknown>` cast, organization.test FeatureSettings `string[]` → object.
- 2026-03-29: New component tests committed (126eee3). FocusIndicator, Popover, ScrollArea, Tooltip (5 tests each), TelemetryStreamObsidian (8 tests).
- 2026-03-29: Test data factory committed (0ef4b5a). `apps/web/src/test/factories/transcript.ts`.
- 2026-03-29: LeadFactory created and RLS test files refactored (18fc5e2). `apps/api/tests/support/factories.py` with `build()` and `build_batch(name_prefix=)`. All 3 RLS test files adopted. 78/78 backend tests passing. Beads issue call-0mf closed.
- 2026-03-29: Story 1-4 status → complete. 26/26 test suites, 217/217 frontend tests + 78/78 backend tests. TS typecheck clean. All pushed to origin.
