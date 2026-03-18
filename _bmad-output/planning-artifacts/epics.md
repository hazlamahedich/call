---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - "/Users/sherwingorechomante/call/_bmad-output/planning-artifacts/prd.md"
  - "/Users/sherwingorechomante/call/_bmad-output/planning-artifacts/architecture.md"
  - "/Users/sherwingorechomante/call/_bmad-output/planning-artifacts/ux-design-specification.md"
---

# AI Cold Caller SaaS - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for AI Cold Caller SaaS, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

- **FR1:** Users can manage a multi-layer hierarchy consisting of Platform Provider, Agency, and Client Sub-account.
- **FR2:** Users can configure a white-labeled portal including custom domain mapping, logos, and specific color schemes.
- **FR3:** System shall enforce hard usage caps and trigger soft alerts at 80% and 95% of the allocated monthly call balance per tenant.
- **FR4:** System shall maintain a voice pipeline latency of <500ms with support for natural lead interruptions.
- **FR5:** **Warm Transfer Opt-in:** System shall trigger AI-to-human handoff based on lead request or confidence score thresholds.
- **FR6:** **Handoff Latency:** System shall allow a live human to join an active session in <2 seconds.
- **FR7:** Users can ingest context via PDF, URL, and TXT files into isolated knowledge retrieval namespaces.
- **FR8:** System shall generate dynamic call icebreakers based on lead public signals (LinkedIn/News).
- **FR9:** System shall generate objection responses using knowledge base context with >95% factual accuracy.
- **FR10:** System shall automatically scrub lead lists against National, State, and internal DNC registries before dialing.
- **FR11:** System shall record jurisdiction-aware disclosures and verify lead consent based on 1-party or all-party state requirements.
- **FR12:** **Rejection Shield:** System shall automatically flag and filter call outcomes with sentiment scores indicating hostility or abuse from standard management feeds.
- **FR13:** **CRM Outcome Sync:** System shall push call dispositions, notes, and tags to GoHighLevel within 2 seconds of call termination.
- **FR14:** **Real-time Appointment Booking:** System shall verify Calendly availability and execute booking confirmation during the call session upon lead request.
- **FR15:** **Gamification System:** Users can earn "Century Club" and "Rainmaker" badges and maintain login streaks to motivate performance.
- **FR16:** **Momentum Starter:** System shall prioritize and queue "warmest" leads first for early session success.
- **FR17:** **Outreach Expansion:** System shall trigger automated post-call SMS follow-up sequences based on call outcomes/dispositions.
- **FR18:** **Advanced Analytics:** System shall track and visualize a "15-Second Retention Tracker" (North Star metric).
- **FR19:** **Hybrid Call Engine:** System shall support seamless switching between AI Voice Mode and Human "Agent Cockpit" Mode.

### NonFunctional Requirements

- **NFR.P1:** Voice Latency: <500ms end-to-end for 95% of calls as measured by edge-node telemetry.
- **NFR.P2:** Retrieval Latency: Knowledge base search and context injection in <200ms for 95th percentile.
- **NFR.P3:** Sync Speed: CRM outcome posting in <2s post-call.
- **NFR.R1:** Uptime: 99.9% for calling bridge and core API as measured by external health checks.
- **NFR.R2:** Provider Fallback: Auto-failover to secondary telephony provider in <3s without session drop.
- **NFR.S1:** Concurrency: Support 1,000+ simultaneous AI voice sessions per tenant namespace.
- **NFR.Sec1:** Data Isolation: Mandatory tenant-level logical separation of all database objects and files; validated by cross-tenant query audits.
- **NFR.Sec2:** Immutable Auditing: Call recordings and consent records stored for a minimum of 7 years with tamper-evident logs.
- **NFR.Sec3:** Encryption: AES-256 for recordings at rest; TLS 1.3 for all data in transit.

### Additional Technical Requirements (Architecture)

- **ARCH1 (Starter):** Unified Hybrid Monorepo (Turborepo + VapiBlocks + FastAPI). Initialization: `npx create-turbo@latest ./`, integrate VapiBlocks into `/apps/web`, FastAPI into `/apps/api`.
- **ARCH2 (Data):** SQLModel as source of truth. Automated TS interfaces. PostgreSQL RLS for tenant boundaries.
- **ARCH3 (Auth):** Clerk (Organizations -> Agencies; Members -> Clients).
- **ARCH4 (Safety):** `snake_case` (backend) -> `camelCase` (frontend) via `AliasGenerator`. `turbo run types:sync` for schema changes.
- **ARCH5 (Errors):** Standardized JSON errors. Shared registry in `packages/constants`.
- **ARCH6 (Monorepo Docs):** Structure: `apps/web` (Next.js 15), `apps/api` (FastAPI), `packages/compliance`, `packages/types`, `packages/constants`.
- **ARCH7 (Guardrails):** TTFB Gate (<100ms processing). Load simulation with Neon Branching (50k leads).
- **ARCH8 (Cache):** Compliance status (DNC/TCPA) cached in Redis at `Streaming Gateway`.
- **ARCH9 (Observability):** Asynchronous telemetry sidecars for voice event loop non-blocking.
- **ARCH10 (Master Join):** Predictive Audio Buffer (shadow-bridge @ 60% confidence, human alert @ 85%). QUIC transport. Context Triad via gRPC <30ms before audio.
- **ARCH11 (Infra):** Vercel (Frontend), AWS App Runner (Voice Backend), Neon (PostgreSQL 17), Cloudflare Railgun/Warp (Routing).

### UX Design Requirements

- **UX-DR1:** **Pulse-Maker:** Subtle, rhythmic visual pulse that quickens as calls transition from 'Cold' to 'Hot'.
- **UX-DR2:** **ROI Dashboard:** Visualize "Total Rejections Handled" in terms of "Agent Hours Saved".
- **UX-DR3:** **Transparency Toggles:** Show "Differential Insight" to explain why AI suggests script changes.
- **UX-DR4:** **Sentiment Ticker:** High-density, real-time telemetry feed of call sentiment sub-harmonics.
- **UX-DR5:** **Fleet View:** "Command Center" dashboard monitoring sentiment velocity across multiple streams using "Heat Ripple" visuals.
- **UX-DR6:** **Threaded Context:** Synchronized playhead with 30s threaded transcript for human "catch-up".
- **UX-DR7:** **Obsidian Theme:** Obsidian Black (`#09090B`), Neon sign colors (Emerald, Crimson, Blue, Zinc).
- **UX-DR8:** **Tactical Typography:** Geist Sans (Headings) & Geist Mono (Telemetry/Transcripts).
- **UX-DR9:** **Grid System:** 4x4 Grid with Glassmorphism for "Command Bridge" layout.
- **UX-DR10:** **Sensory Cues:** Binaural Whoosh & Vibe Borders for state transitions.
- **UX-DR11:** **Coded Redaction:** Hostile leads masked via moving data block animations (Rejection Shield).
- **UX-DR12:** **System Boot Ritual:** Grid scan & Neon ignition transition from "Zen" to "Obsidian".
- **UX-DR13:** **10-Minute Launch Onboarding:** Low-friction "Zen" mode with Drag-and-Drop KB ingestion and 5-Question Wizard.
- **UX-DR14:** **Accessibility:** WCAG AAA for text, motion reduction options, semantic HTML5 landmarks.
- **UX-DR15:** **Reusable Components:** `ConfirmActions`, `StatusMessage`, `EmptyState`, `FocusIndicator`.
- **UX-DR16:** **Pre-Flight Calibration:** Interactive voice/goal selection during background KB ingestion.
- **UX-DR17:** **Feedback Patterns:** "Success Bloom" (volumetric emerald flood) and "Context Flicker" (dimming on confidence drop).
- **UX-DR18:** **Interaction Recovery:** "Desaturation Pulse" (Cognitive Reset) and "Telemetry Anchor" (Bottom-anchored scrolling).

### FR Coverage Map

- **FR1:** Epic 1 - Multi-tenant Foundation & Identity
- **FR2:** Epic 1 - Multi-tenant Foundation & Identity
- **FR3:** Epic 1 - Multi-tenant Foundation & Identity
- **FR4:** Epic 2 - High-Performance AI Voice Engine
- **FR5:** Epic 5 - The "Master Join" & Human Cockpit
- **FR6:** Epic 5 - The "Master Join" & Human Cockpit
- **FR7:** Epic 3 - Collaborative RAG & Scripting Logic
- **FR8:** Epic 3 - Collaborative RAG & Scripting Logic
- **FR9:** Epic 3 - Collaborative RAG & Scripting Logic
- **FR10:** Epic 4 - Compliance Guardrail & Rejection Shield
- **FR11:** Epic 4 - Compliance Guardrail & Rejection Shield
- **FR12:** Epic 4 - Compliance Guardrail & Rejection Shield
- **FR13:** Epic 6 - CRM Ecosystem & Dynamic Personalization
- **FR14:** Epic 6 - CRM Ecosystem & Dynamic Personalization
- **FR15:** Epic 7 - Performance Analytics & Gamification
- **FR16:** Epic 7 - Performance Analytics & Gamification
- **FR17:** Epic 6 - CRM Ecosystem & Dynamic Personalization
- **FR18:** Epic 7 - Performance Analytics & Gamification
- **FR19:** Epic 5 - The "Master Join" & Human Cockpit

### Epic List

#### Epic 1: Multi-tenant Foundation & Identity (The "Sub-account" Era)

Establish the hierarchical, white-labeled core with secure tenant separation, branding capabilities, and initial onboarding.

- **FRs covered:** FR1, FR2, FR3
- **NFRs:** NFR.Sec1, NFR.Sec3
- **Technical/UX:** ARCH1, ARCH2, ARCH3, ARCH6, UX-DR7, UX-DR8, UX-DR9, UX-DR15, UX-DR14

### Story 1.1: Hybrid Monorepo & Core Infrastructure Scaffolding

As a Developer,
I want a unified monorepo structure with Turborepo, FastAPI, and Next.js,
So that I can build the frontend and backend in a synchronized workspace.

**Acceptance Criteria:**

- **Given** I run the initialization script
- **When** the environment setup is complete
- **Then** `apps/web` contains a Next.js 15 app and `apps/api` contains a FastAPI service
- **And** `turbo.json` defines pipelines for `build`, `dev`, and `typecheck` across all apps and packages
- **And** `packages/types` is accessible by both `web` and `api` projects

### Story 1.2: Multi-layer Hierarchy & Clerk Auth Integration

As a Platform Provider,
I want to manage Agency and Client sub-accounts using Clerk Organizations,
So that I can maintain a strict three-tier business hierarchy.

**Acceptance Criteria:**

- **Given** a user is logged into the management portal
- **When** they create a new Agency organization
- **Then** they can assign Client sub-accounts to that Agency within the Clerk dashboard/API
- **And** user permissions (Admin, Member) are correctly scoped to their specific Organization level
- **And** authentication middleware in `apps/api` validates the `org_id` for every request

### Story 1.3: Tenant-Isolated Data Persistence with PostgreSQL RLS

As a Security Officer,
I want to enforce Row-Level Security (RLS) on all database tables,
So that data from one tenant is never accessible to another.

**Acceptance Criteria:**

- **Given** a Neon PostgreSQL database with multiple tenants
- **When** a query is executed from the FastAPI service
- **Then** the `jwt.org_id` from the Clerk token is used to set the `app.current_org_id` session variable
- **And** PostgreSQL RLS policies deny access to any rows where `tenant_id != current_org_id`
- **And** unit tests verify that a query for `Tenant A` returns zero results for `Tenant B` data

### Story 1.4: "Obsidian" Design System Foundation & Reusable Components

As a UI Designer,
I want a base design system using Radix UI and the Obsidian theme,
So that all future features have a consistent and premium visual language.

**Acceptance Criteria:**

- **Given** the `apps/web` project
- **When** I browse the component library
- **Then** foundational components like `CockpitContainer`, `VibeBorder`, and `ContextTriad` are implemented with Glassmorphism
- **And** colors align with the `#09090B` Obsidian Black and Neon Emerald/Crimson scheme
- **And** Geist Sans and Geist Mono fonts are correctly configured

### Story 1.5: White-labeled Admin Portal & Custom Branding

As an Agency Owner,
I want to customize the portal branding (logo, colors, domain),
So that I can present a professional, white-labeled experience to my Clients.

**Acceptance Criteria:**

- **Given** an Agency account
- **When** I upload a logo and set a primary hex color in the settings
- **Then** the portal UI updates in real-time to reflect the new theme
- **And** custom domain mapping (CNAME) routing is configured and validated via Cloudflare/Vercel
- **And** tenant branding settings are persisted in the `Agencies` table

### Story 1.6: 10-Minute Launch Onboarding Wizard

As a New User,
I want a 5-Question onboarding ritual,
So that I can set up my first AI agent and begin dialing in under 10 minutes.

**Acceptance Criteria:**

- **Given** a freshly created Client sub-account
- **When** the user starts the "Zen" onboarding flow
- **Then** they are guided through 5 questions: business goal, primary script context, voice selection, integration choice, and safety level
- **And** completion of the wizard automatically creates the first `Agent` and `Script` records
- **And** progress is visualized with a minimalist status bridge

### Story 1.7: Resource Guardrails: Usage Monitoring & Hard Caps

As a Platform Admin,
I want to enforce call balance caps and trigger alerts,
So that I can prevent overages and maintain tenant profitability.

**Acceptance Criteria:**

- **Given** a tenant reaching their call limit
- **When** their monthly balance hits 80% or 95%
- **Then** a `StatusMessage` alert is displayed in their dashboard
- **And** once the 100% hard cap is reached, new call requests are rejected with a standardized `403-LIMIT-EXCEEDED` error
- **And** usage is tracked in real-time in the `usage_logs` table

#### Epic 2: High-Performance AI Voice Engine (The "Sound of Speed")

Implement the core low-latency voice pipeline including telephony bridge, transcription, and TTS with real-time telemetry.

- **FRs covered:** FR4
- **NFRs:** NFR.P1, NFR.R1, NFR.R2, NFR.S1
- **Technical/UX:** ARCH11, ARCH9, UX-DR1, UX-DR16

### Story 2.1: Vapi Telephony Bridge & Webhook Integration

As a Developer,
I want to connect the API to the Vapi telephony bridge,
So that I can trigger and manage inbound/outbound calls via secure webhooks.

**Acceptance Criteria:**

- **Given** a valid Vapi API key and workspace
- **When** an outbound call is triggered via the `/calls/trigger` endpoint
- **Then** Vapi initiates the call to the target phone number
- **And** `apps/api` receives a `call.started` webhook with a valid `call_id`
- **And** all webhook events are validated using the Vapi signature header

### Story 2.2: Real-time Audio Stream & Transcription Pipeline

As a Speech Scientist,
I want a transcription pipeline with <200ms latency,
So that the AI can perceive and respond to lead speech instantly.

**Acceptance Criteria:**

- **Given** an active call session
- **When** the lead speaks into the telephony bridge
- **Then** Deepgram (or Vapi-native) transcription events are streamed to the backend
- **And** the 95th percentile latency from "Speech End" to "Text Received" is <200ms
- **And** lead interruptions (talk-over) are detected and flagged in the event stream

### Story 2.3: Low-Latency TTS & Provider Fallback Logic

As a Technical Lead,
I want an automated fallback between TTS providers (ElevenLabs & Cartesia),
So that call quality is maintained even during provider latency spikes.

**Acceptance Criteria:**

- **Given** a primary TTS provider (ElevenLabs) is experiencing high latency (>500ms)
- **When** the system detects three consecutive slow responses
- **Then** it automatically switches the session to the secondary provider (Cartesia)
- **And** the switch happens mid-call without audible session artifacts
- **And** the system logs the provider switch event for auditing

### Story 2.4: Asynchronous Telemetry Sidecars for Voice Events

As a System Architect,
I want to capture voice events using non-blocking sidecars,
So that logging and performance tracking do not delay the AI response loop.

**Acceptance Criteria:**

- **Given** a high-concurrency calling environment
- **When** a voice event (silence, noise, interruption) is detected
- **Then** the event is pushed to an in-memory queue for background processing
- **And** the sidecar service persists the event to the `voice_telemetry` table asynchronously
- **And** load tests confirm that telemetry logging adds <2ms to the message processing time

### Story 2.5: "Pulse-Maker" Visual Visualizer Component

As a User,
I want a rhythmic visual "pulse" on my dashboard,
So that I can see the "heartbeat" and health of the active call at a glance.

**Acceptance Criteria:**

- **Given** an active call being monitored in the Fleet View
- **When** voice activity is detected (VAD)
- **Then** the `Pulse-Maker` component animates its rhythm and intensity based on audio volume
- **And** the pulse color transitions from Zinc to Emerald as lead engagement increases
- **And** the animation responds to interruptions with a distinct "ripple" effect

### Story 2.6: Pre-Flight Calibration Dashboard

As an Agent Manager,
I want to calibrate my AI's voice and goals before dialing,
So that I can ensure the output is perfect before live engagement.

**Acceptance Criteria:**

- **Given** the 10-Minute Launch onboarding is complete
- **When** the user enters the "Pre-Flight" calibration module
- **Then** they can trigger a 10rd audio test to hear the selected voice
- **And** they can adjust "Speech Speed" and "Stability" settings with instant feedback
- **And** the configuration is persisted to the `AgentConfig` table only after explicit save

#### Epic 3: Collaborative RAG & Scripting Logic (The "Smart Script")

Enable multi-format knowledge ingestion into isolated namespaces and dynamic script execution with factual accuracy.

- **FRs covered:** FR7, FR8, FR9
- **NFRs:** NFR.A1, NFR.P2
- **Technical/UX:** ARCH2, UX-DR3

### Story 3.1: Multi-Format Knowledge Ingestion & Validation

As an Agency Admin,
I want to upload PDFs, URLs, and text blocks to a knowledge base,
So that my AI agent can learn about my specific products and services.

**Acceptance Criteria:**

- **Given** a tenant dashboard
- **When** a user uploads a PDF or provides a URL
- **Then** the system extracts text content and parses it into semantic chunks
- **And** broken URLs (404s) or incompatible files are flagged with a "Validation Error" notification
- **And** the status of the ingestion (Processing/Ready) is reflected in the UI

### Story 3.2: Per-Tenant RAG Namespacing with "Namespace Guard"

As a Security Architect,
I want to ensure a strict isolation of knowledge bases between clients,
So that sensitive information from one client never appears in another's scripts.

**Acceptance Criteria:**

- **Given** a vector search query
- **When** the query is processed by the "Namespace Guard" middleware
- **Then** the search is strictly limited to vectors matching the active `client_id`
- **And** the query fails with a `403 Forbidden` if a cross-tenant ID is attempted
- **And** the distance filtering logic (pgvector) ensures results are only retrieved from the relevant namespace

### Story 3.3: Script Generation Logic with Grounding Constraints

As a Script Designer,
I want the AI to generate responses based strictly on the provided knowledge base,
So that it avoids making up false information or "hallucinating."

**Acceptance Criteria:**

- **Given** a lead question during a call
- **When** the RAG engine retrieves relevant knowledge chunks
- **Then** the LLM prompt enforces a "No-Knowledge-No-Answer" policy (return a polite "I don't have that info")
- **And** the generated response uses the retrieved chunks as the sole source of truth
- **And** the system logs "Grounding Confidence" scores for every response

### Story 3.4: Dynamic Variable Injection for Hyper-Personalization

As a Marketing Manager,
I want to inject lead-specific data into the script,
So that the AI can mention specific details like company name or previous purchase.

**Acceptance Criteria:**

- **Given** a lead CSV or CRM integration
- **When** the script reaches a node with `{{variable_name}}` syntax
- **Then** the system dynamically replaces the placeholder with the lead's actual data
- **And** custom fields beyond the standard set (e.g., `{{last_interaction}}`) are supported
- **And** if a variable is missing, a pre-defined fallback string is used instead

### Story 3.5: The "Script Lab" with Source Attribution

As an AI Trainer,
I want to test my script in a sandbox and see which sources the AI is citing,
So that I can verify the grounding and improve the knowledge base.

**Acceptance Criteria:**

- **Given** the Script Lab interface
- **When** a tester interacts with the agent
- **Then** for every response, the UI displays a "Source Attribution" tooltip
- **And** clicking the tooltip reveals the specific document chunk used to generate that answer
- **And** the lab supports "Scenario Overlays" to test how the agent handles variables (e.g., "Assume Name is John")

### Story 3.6: Real-time "Self-Correction" Factual Hook

As a Quality Engineer,
I want the system to verify factuality before the AI speaks,
So that we can catch hallucinations in real-time.

**Acceptance Criteria:**

- **Given** an AI-generated script line
- **When** the "Verification Hook" detects a factual claim
- **Then** it performs a secondary similarity check against the knowledge base
- **And** if the claim is unsupported, the system triggers a "Self-Correction" loop to re-phrase the line
- **And** the corrected line must pass the verification check before being sent to the TTS pipeline

#### Epic 4: Compliance Guardrail & Rejection Shield (The "Safe Dial")

Implement legal filters, state-specific rules, DNC checks, and "Rejection Shield" logic to ensure every call is legal and ethical.

- **FRs covered:** FR10, FR11, FR12
- **NFRs:** NFR.C1, NFR.C2, NFR.Sec2
- **Technical/UX:** ARCH8, UX-DR4, UX-DR11, UX-DR14

### Story 4.1: Automated "Double-Hop" DNC Registry Check

As a Compliance Officer,
I want the system to check the DNC registry twice (at upload and millisecond-before-dialing),
So that we minimize the risk of calling a lead who recently registered for the blocklist.

**Acceptance Criteria:**

- **Given** a campaign about to start
- **When** the lead list is first uploaded, the system performs an initial scrub against the Global DNC and tenant blocklists
- **Then** millisecond-before-dialing, a second "Double-Hop" check is performed against the real-time cache
- **And** if a lead is flagged, the call is canceled and the status is updated to `Blocked (DNC)`
- **And** the `packages/compliance` service logs each check result for the audit trail

### Story 4.2: State-Aware Regulatory Filter & "Graceful Goodnight"

As a Legal Advisor,
I want the system to enforce legal calling hours and recording disclosures per state,
So that we remain compliant with TCPA and two-party consent laws.

**Acceptance Criteria:**

- **Given** a lead's area code or geographic data
- **When** a dial is attempted outside the legal window (8am-9pm local time)
- **Then** the system blocks the dial and schedules it for the next valid window
- **And** if a call is ongoing at 8:59 PM, the AI triggers a "Graceful Goodnight" protocol to wrap up and end the call before the cutoff
- **And** for "Two-Party" consent states, the AI automatically plays the mandatory recording disclosure at session start

### Story 4.3: "Rejection Shield" - Adaptive De-escalation & Polite Retreat

As a Quality Manager,
I want the AI to detect hostility or explicit rejection,
So that it can pivot to de-escalation or immediately honor a "Remove Me" request.

**Acceptance Criteria:**

- **Given** an active call stream
- **When** the sentiment engine detects high hostility or keywords like "Stop calling" or "Sue you"
- **Then** the `Rejection Shield` logic overrides the current script node
- **And** the AI performs a "Polite Retreat" (e.g., "I understand, I'll remove you from our list right away. Have a nice day.")
- **And** the lead is automatically moved to the tenant-level blocklist
- **And** the `Pulse-Maker` UI component turns Red to alert the supervisor

### Story 4.4: Hashed Consent Capture & Immutable Audit Logging

As a Security Lead,
I want verbal consent events to be hashed and stored with trusted timestamps,
So that our compliance logs are provable and tamper-resistant for legal audits.

**Acceptance Criteria:**

- **Given** a successful verbal agreement or consent capture
- **When** the event is recorded in the `compliance_logs` table
- **Then** the record includes a SHA-256 hash of the specific audio snippet/transcript and a timestamp from a trusted NTP source
- **And** the API prevents any `UPDATE` or `DELETE` operations on existing compliance log entries
- **And** the log entry is linked to the session-specific `call_id` for cross-referencing

### Story 4.5: Compliance Dashboard & Enterprise Risk Scoring

As an Enterprise User,
I want a high-level view of my organization's compliance health,
So that I can identify and mitigate risks across multiple clients/agencies.

**Acceptance Criteria:**

- **Given** the Admin Portal
- **When** viewing the "Compliance Dashboard"
- **Then** the system displays a "Risk Score" for each campaign based on DNC hits and objection rates
- **And** the UI shows a "Verification Badge" (UX-DR14) for campaigns that meet 100% safety criteria
- **And** admins can export a "Compliance Proof" PDF package for any given time period

### Story 4.6: "Human-at-the-Helm" Real-time Escalation Bridge

As a Call Center Manager,
I want to be alerted when a call enters a high-risk compliance scenario,
So that I can take over or intervene before a legal breach occurs.

**Acceptance Criteria:**

- **Given** an active call being monitored
- **When** the AI detects a "Compliance-Sensitive" topic (e.g., credit card info, legal threats)
- **Then** the system triggers a "Cold Handoff" alert to the human cockpit
- **And** the human manager receives the full live transcript and context within <1 second
- **And** the human can choose to "Take Over" (bridging the audio instantly) or "Force Close" the session

#### Epic 5: The "Master Join" & Human Cockpit (The "Handoff Ritual")

Implement the zero-latency AI-to-Human handoff protocol and the unified cockpit for live intervention and context synchronization.

- **FRs covered:** FR5, FR6, FR19
- **NFRs:** NFR.P1 (<200ms)
- **Technical/UX:** ARCH10, UX-DR4, UX-DR6, UX-DR10, UX-DR17

### Story 5.1: Zero-Latency "Master Join" with Shadow Bridging

As a Sales Manager,
I want to join a live AI call instantly (<200ms),
So that the lead doesn't perceive any gap or silence during the handoff.

**Acceptance Criteria:**

- **Given** a human manager selects a call to monitor in the Cockpit
- **When** the manager arrives on the monitoring page, a "Shadow Bridge" (pre-warmed audio socket) is initialized
- **Then** when the "Join Call" button is pressed, the vapi bridge performs a metadata-only toggle to switch audio
- **And** the total measured latency from "Click" to "Human Audio Live" is <200ms
- **And** the transition is seamless with no audible "click" or session dropout

### Story 5.2: The "Human Cockpit" with Live Mood Wave Monitoring

As a Supervisor,
I want a unified dashboard to monitor live calls and lead sentiment,
So that I know exactly when to intervene and "Join" a call.

**Acceptance Criteria:**

- **Given** the Cockpit dashboard
- **When** calls are active, it displays a grid of "Live Tiles"
- **Then** each tile shows a real-time "Mood Wave" visual (Saga's requirement) based on sentiment offsets
- **And** tiles pulse or change border color (Zinc -> Red) if the AI detects a high-risk compliance or rejection event
- **And** a "One-Click Join" button is prominently displayed for every active session

### Story 5.3: Real-time Context Synchronization & "Key Moments" Feed

As a Human Agent,
I want to see a synced transcript and a summary of key moments before I join,
So that I can enter the conversation with full context without repeating questions.

**Acceptance Criteria:**

- **Given** a live-monitored call
- **When** the AI is speaking, the transcript scrolls in real-time on the Cockpit side
- **Then** a "Key Moments" panel highlights extracted entities (Name, Budget, Pain Points)
- **And** when the human joins, the AI hands over a "Context Buffer" (the last 3 turns) to the human's UI
- **And** if a human leaves and "Bounces" the call back to AI, the AI resumes using the updated context

### Story 5.4: "Whisper-Mode" - Coach-to-AI Private Bridge

As a Senior Sales Coach,
I want to coach the AI agent in real-time during a call,
So that I can guide its responses without the lead hearing me.

**Acceptance Criteria:**

- **Given** an active call in "Monitor Only" mode
- **When** the coach activates "Whisper-Mode"
- **Then** the coach's audio is routed strictly to the AI's internal response pipeline
- **And** the lead's audio channel is "Hard Muted" (ARCH10 safety check) so they cannot hear the coach
- **And** the AI acknowledges the coach's guidance and pivots its script accordingly

### Story 5.5: Multi-modal Sentiment Analysis Visualization

As an Agency Owner,
I want to see historical and real-time sentiment trends for my agents,
So that I can measure the effectiveness of the knowledge base and scripting.

**Acceptance Criteria:**

- **Given** the Cockpit Analytics view
- **When** calls are completed, sentiment data is aggregated into time-series charts
- **Then** the UI displays "Retention Strength" scores for different script variations
- **And** the visualizations highlight segments of calls where leads historically drop off
- **And** data is exportable in CSV format for further analysis

### Story 5.6: Session Scaling & Redis sharding

As a Backend Engineer,
I want the monitoring backplane to scale to 1,000+ concurrent views,
So that a large agency can monitor all its agents simultaneously without lag.

**Acceptance Criteria:**

- **Given** high global concurrency (1000+ active callers, 500+ supervisors)
- **When** live events are broadcasted via WebSockets
- **Then** the Redis pub/sub layer uses sharding to prevent a single-process bottleneck
- **And** the Cockpit dashboard maintains <100ms update frequency for transcripts
- **And** memory usage for "Context Buffers" is strictly capped per session

#### Epic 6: CRM Ecosystem & Dynamic Personalization (The "Perfect Sync")

Real-time integration with CRM tools for outcome syncing, appointment booking, and automated SMS follow-ups.

- **FRs covered:** FR13, FR14, FR17
- **NFRs:** NFR.P3 (<1s)
- **Technical/UX:** ARCH7, UX-DR3

### Story 6.1: Pluggable CRM Integration SDK (Adapter Pattern)

As a Developer,
I want a pluggable SDK for CRM integrations,
So that I can easily add support for GoHighLevel, HubSpot, and Salesforce using a unified interface.

**Acceptance Criteria:**

- **Given** the `packages/integrations` module
- **When** adding a new CRM provider
- **Then** the provider must implement the standard `ICRMAdapter` interface (Auth, LeadFetch, CallUpdate, Booking)
- **And** OAuth2 credentials for each tenant are stored securely in the `TenantIntegrations` table
- **And** the system supports a "Connection Health" check to alert users of expired tokens

### Story 6.2: Custom Disposition & Outcome Mapping

As an Agency Owner,
I want to map AI call outcomes to my specific CRM pipeline stages,
So that my existing sales workflows remain uninterrupted.

**Acceptance Criteria:**

- **Given** a connected CRM integration
- **When** configuring the "Disposition Map" in the dashboard
- **Then** the user can map AI sentiments (e.g., "Positive Interest") to specific CRM picklist values (e.g., "Stage: Qualified")
- **And** the system automatically updates the lead record post-call according to this map
- **And** a manual "Sync Override" button is available in the Cockpit for disputed outcomes

### Story 6.3: Proactive Appointment Booking Bridge (Cal.com/Calendly)

As a Lead,
I want the AI to suggest specific meeting times and book them for me,
So that I can confirm my interest without manual follow-up.

**Acceptance Criteria:**

- **Given** a script node configured for "Booking"
- **When** the lead expresses interest
- **Then** the AI pre-fetches real-time availability from the connected calendar (Cal.com/Calendly)
- **And** the AI suggests two upcoming slots (e.g., "How about tomorrow at 2 PM or Thursday at 10 AM?")
- **And** upon verbal confirmation, the appointment is booked and confirmed in the CRM
- **And** the system uses "Distributed Locking" to prevent double-bookings (Murat's requirement)

### Story 6.4: Multi-Channel Post-Call SMS Automation

As an Agency Admin,
I want to trigger personalized SMS follow-ups immediately after a call,
So that I can provide meeting links or summaries to the lead while interest is high.

**Acceptance Criteria:**

- **Given** a completed call session
- **When** the call disposition meets the trigger criteria (e.g., "Interested")
- **Then** the system sends a personalized SMS via Twilio or the native CRM API
- **And** the message content includes dynamic variables from the call (e.g., "Thanks John, here is the link we discussed...")
- **And** the SMS event is logged in the `communication_logs` table for tracking

### Story 6.5: Dynamic Personalization from Deep-Record Sync

As a Sales Strategist,
I want to use custom CRM fields in my AI script openers,
So that my outreach feels highly personalized and knowledgeable.

**Acceptance Criteria:**

- **Given** a lead synced from a CRM
- **When** the AI initializes the call context
- **Then** it pulls values from all mapped custom fields (e.g., `previous_purchase_date`, `industry_vertical`)
- **And** these values are available as RAG snippets or script variables
- **And** the UI shows a "Data Source" badge for every variable pulled from the CRM

### Story 6.6: Rate-Limit Aware Sync Retry Queue

As a DevOps Engineer,
I want a robust retry mechanism for CRM syncs,
So that data is never lost even if third-party APIs are down or rate-limiting us.

**Acceptance Criteria:**

- **Given** a failed CRM update (e.g., a 429 Rate Limit or 503 Outage)
- **When** the `IntegrationWorker` receives the error
- **Then** the task is moved to a "Tenant-Isolated Retry Queue"
- **And** the system applies exponential backoff for that specific tenant's tokens
- **And** a "Global Rate-Limiter" ensures total traffic to a provider (e.g., HubSpot) stays within safe bounds
- **And** persistent failures are alerted to the admin via the "Sync Health" dashboard

#### Epic 7: Performance Analytics & Gamification (The "Rainmaker" Suite)

Deep visualization of call performance, retention tracking, and gamified achievement systems to motivate performance.

- **FRs covered:** FR15, FR16, FR18
- **NFRs:** NFR.P3 (<1s)
- **Technical/UX:** ARCH5, UX-DR2, UX-DR5, UX-DR12, UX-DR18

### Story 7.1: Real-time "Rainmaker" Performance Dashboard

As an Agency Owner,
I want to see a real-time dashboard of my campaign KPIs,
So that I can measure ROI and agent performance at a glance.

**Acceptance Criteria:**

- **Given** the Rainmaker dashboard (UX-DR5)
- **When** the dashboard is loaded
- **Then** the system displays conversion rates (Bookings/Calls), average duration, and sentiment trends
- **And** the data is filtered by tenant and time-range
- **And** the total page render time for 1,000,000+ records is <1s (ARCH5)

### Story 7.2: Session-Level Sentiment & Tone Mapping (Heatmaps)

As a Sales Manager,
I want to see exactly where a lead's sentiment shifted during a call,
So that I can identify weak points in my script knowledge base.

**Acceptance Criteria:**

- **Given** a call recording playback
- **When** viewing the "Sentiment Map"
- **Then** the UI displays a second-by-second heatmap of sentiment (Zinc -> Red -> Emerald)
- **And** the heatmap is pre-rendered via a "Sentiment Sidecar" service (Winston's requirement) to ensure <500ms load time
- **And** hover-points show the specific transcript line associated with that sentiment score

### Story 7.3: Premium Gamified Achievement System & Badges

As an Agent Manager,
I want to motivate my AI training team with badges and achievements,
So that script optimization feels like a progress-based game.

**Acceptance Criteria:**

- **Given** the user profile and dashboard
- **When** specific milestones are reached (e.g., "100 Appointments Booked" or "90% Grounding Confidence")
- **Then** the system triggers a premium, glassmorphic "Achievement Badge" (UX-DR12)
- **And** the badge includes a subtle micro-animation for the initial reveal
- **And** the count of achievements contributes to a "Tenant Leaderboard"

### Story 7.4: "Momentum Starter" - Daily Goal Pursuit Widget

As an Agent,
I want a simple daily tracker for my bookings and call volume,
So that I can maintain momentum and stay focused on my targets.

**Acceptance Criteria:**

- **Given** the main dashboard
- **When** a call is completed or a meeting booked
- **Then** the "Momentum Starter" widget (FR16) updates its progress bar in real-time
- **And** the widget displays "Daily Goal: X/Y" and "Streak: Z Days"
- **And** the data points reset automatically at the tenant's local midnight hour

### Story 7.5: A/B Script Performance Comparative Analytics

As a Sales Specialist,
I want to compare the performance of two script variations side-by-side,
So that I can scientifically prove which knowledge base chunks drive more bookings.

**Acceptance Criteria:**

- **Given** two active script versions in a single campaign
- **When** analyzing the "Comparative View"
- **Then** the system displays a split chart showing Conversion and Retention for both Version A and B
- **And** the data is strictly attributed based on the `script_version` metadata linked to each `CallRecord`
- **And** the UI highlights the "Winner" based on statistically significant appointment data

### Story 7.6: Automated PDF "Sales Performance" Report Generator

As an Agency Owner,
I want to send beautiful, automated PDF reports to my clients every week,
So that I can demonstrate the value of our AI outreach without manual effort.

**Acceptance Criteria:**

- **Given** a scheduled reporting configuration
- **When** the scheduled time is reached (e.g., Monday 8 AM)
- **Then** the system generates a high-fidelity PDF containing conversion summaries and ROI charts
- **And** the report is automatically emailed to the configured client recipients
- **And** the PDF theme adheres to the "Obsidian" design system aesthetic
