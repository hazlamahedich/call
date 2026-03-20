# 01-Command Center (Fleet View)

## Page Metadata

| Property | Value |
|----------|-------|
| **Scenario** | Fleet Pulse & Rejection Shield |
| **Page Number** | 01 |
| **Platform** | Desktop |
| **Page Type** | Full Page |
| **Viewport** | Desktop-first |
| **Interaction** | Mouse+keyboard |
| **Visibility** | Authenticated (Agency Admin/Manager) |

---

## Overview

**Page Purpose:** Provide a high-density, real-time "Mission Control" for monitoring multi-tenant AI call performance (Fleet View) and intervention (Master Join).

**User Situation:** Agency Marcus logs in to monitor his 50+ concurrent AI streams across 5 clients. He needs to see at-a-glance health, sentiment velocity, and identify high-value calls requiring human takeover.

**Success Criteria:**
- Monitors 1,000+ simultaneous calls without lag.
- Identifies hostile sentiment in <500ms.
- Success "Master Join" transitions in <200ms.

**Entry Points:**
- Dashboard Login
- Sidebar "Command Center" link

**Exit Points:**
- Client Settings
- Call Log Details
- Analytics Dashboard

---

## Reference Materials

**Strategic Foundation:**
- [PRD](../../E-PRD/prd.md)
- [UX Specification](../../ux-design-specification.md)

**Design System:**
- [Design Tokens](../../D-Design-System/00-design-system.md)

---

## Layout Structure

The page follows a "Command Bridge" layout: a vertical navigation sidebar, a central telemetry grid, and a right-hand operational metrics panel.

```
+------------------+--------------------------------------------+------------------+
|                  | Header: COMMAND CENTER [Time] [Search]     |                  |
| FLEET NAVIGATOR  +--------------------------------------------| ACTIONS &        |
|                  |                                            | METRICS          |
| [Status Pips]    | [TELEMETRY GRID]                           |                  |
| [Client List]    | +--------------------+--------------------+ | [Wellness]       |
|                  | | Call Node A        | Call Node B        | | [ROI Shield]     |
| [Active Agents]  | | [Waveform]         | [Waveform]         | | [Alerts]         |
|                  | | [Sentiment]        | [Sentiment]        | |                  |
|                  | +--------------------+--------------------+ |                  |
| [Settings]       | | Call Node C        | Call Node D        | |                  |
|                  | +--------------------+--------------------+ |                  |
+------------------+--------------------------------------------+------------------+
```

---

## Spacing

**Scale:** [Spacing Scale](../../D-Design-System/00-design-system.md#spacing-scale)

| Property | Token |
|----------|-------|
| Page padding (horizontal) | `space-xl` (32px) |
| Section gap | `space-lg` (24px) |
| Element gap | `space-md` (16px) |
| Component gap | `space-sm` (8px) |

---

## Typography

**Scale:** [Type Scale](../../D-Design-System/00-design-system.md#type-scale)

| Element | Semantic | Size | Weight | Typeface |
|---------|----------|------|--------|----------|
| Page title | H1 | `text-2xl` | Bold | Geist Sans |
| Section heading | H2 | `text-lg` | Semibold | Geist Sans |
| Telemetry row | p | `text-sm` | Normal | **Geist Mono** |
| Label (Small) | span | `text-xs` | Bold | Geist Sans (Caps) |

---

## Page Sections

### Section: Fleet Navigator (Sidebar)

**OBJECT ID:** `cmd-fleet-navigator`

| Property | Value |
|----------|-------|
| Purpose | Global navigation and multi-client switching. |
| Component | `SidebarContainer` |
| Background | `bg-zinc-900` |

#### Client Selection
- **ID:** `cmd-client-selector`
- **EN:** "Switch Client"
- **Behavior:** Dropdown / Accordion listing active clients.

---

### Section: Main Telemetry (Central)

**OBJECT ID:** `cmd-main-telemetry`

| Property | Value |
|----------|-------|
| Purpose | Real-time monitoring of active calls. |
| Component | `TelemetryGrid` |
| Gap | `space-md` |

#### Call Node (Component)
- **ID:** `cmd-telemetry-node`
- **EN:** "Active Call Instance"
- **Elements:** 
    - `VibeBorder`: Top-border pulsing based on context sentiment.
    - `TranscriptStream`: Geist Mono feed of real-time speech.
    - `JoinButton`: High-glow action for Master Join.

---

### Section: Operational Metrics (Right Panel)

**OBJECT ID:** `cmd-operational-metrics`

| Property | Value |
|----------|-------|
| Purpose | Aggregated performance and emotional ROI tracking. |
| Component | `MetricsPanel` |

#### Rejection Shield Tracker
- **ID:** `cmd-rejection-shield-roi`
- **EN:** "Morale Saved" / "Bridges Protected"
- **Behavior:** Dynamically counts blocked hostile interactions.

---

## Page States

| State | When | Appearance | Actions |
|-------|------|------------|---------|
| Default | Live calling active. | Normal Obsidian/Neon telemetry. | Takeover, Monitor, Mute. |
| Loading | Page initialization. | Grid Scan animation (System Boot). | None. |
| Empty | No active calls. | Zinc-muted "Standby" grid overlay. | Launch Campaign. |
| Alert | Critical failure (Telephony). | Crimson pulse border on affected node. | Failover switch. |

---

## Technical Notes
- **Latency**: Telemetry stream must update in <100ms from WebSocket event.
- **Performance**: Use CSS-hardware acceleration for "Vibe" animations.
- **Data Isolation**: Ensure client telemetry filter is hard-gated at the API level.

---

## Checklist
- [x] Page purpose clear
- [x] All Object IDs assigned
- [x] Components reference design system
- [ ] Translations complete (SE/EN)
- [x] States documented
