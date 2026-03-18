---
stepsCompleted: ["step-01-init", "step-02-discovery", "step-02b-vision", "step-02c-executive-summary", "step-03-success", "step-04-journeys", "step-05-domain", "step-06-innovation", "step-07-project-type", "step-08-scoping", "step-09-functional", "step-10-nonfunctional", "step-e-01-discovery", "step-e-02-review", "step-e-03-edit"]
vision:
  statement: 'Redefine outbound sales by making AI the universal business partner for any company that needs to have calls with prospects or customers'
  oneLiner: 'Your always-on outbound sales partner, for any business'
  differentiator: 'Not a dialer tool — a learning business partner that adapts to any vertical or business model'
  coreInsight: 'AI voice has matured enough to replace human SDRs at the quality level (not just cost level) for the first time'
  ambitionLevel: 'category_definer'
  gtmBeachhead: 'marketing_agencies'
  expansionVision: 'any_business_with_outbound_needs'
inputDocuments:
  - '/Users/sherwingorechomante/call/_bmad-output/brainstorming/brainstorming-session-2026-03-16-025800.md'
  - '/Users/sherwingorechomante/call/_bmad-output/planning-artifacts/product-brief-call-2026-03-16.md'
  - '/Users/sherwingorechomante/call/ai_cold_caller_saas_prp.md'
  - '/Users/sherwingorechomante/call/_bmad-output/planning-artifacts/research/domain-ai-cold-caller-saas-research-2026-03-16.md'
  - '/Users/sherwingorechomante/call/_bmad-output/planning-artifacts/research/market-ai-cold-caller-saas-market-research-2026-03-16.md'
  - '/Users/sherwingorechomante/call/_bmad-output/planning-artifacts/research/technical-comprehensive-ai-cold-caller-research-2026-03-16.md'
workflowType: 'prd'
project_name: 'AI Cold Caller SaaS'
user_name: 'team mantis a'
date: '2026-03-16'
classification:
  projectType: 'saas_b2b'
  projectVariant: 'platform_play'
  domain: 'agency_operating_infrastructure'
  domainTags: ['martech', 'sales_automation', 'outbound_voice', 'compliance_regulated']
  complexity: 'high'
  complexityDrivers:
    - 'Real-time voice pipeline with sub-500ms latency requirements'
    - 'Multi-layer tenancy (agency > client > lead)'
    - 'Compliance automation (TCPA, FCC 2024, DNC lists, consent recording)'
lastEdited: '2026-03-16'
editHistory:
  - date: '2026-03-16'
    changes: 'Enhanced traceability with UJ4 (White-label) and FR13/14 (Integrations). Removed implementation leakage (RAG/CNAME). Added Governance and Compliance matrices. Refined requirement measurability.'
---

# Product Requirements Document: Call

**Author:** team mantis a
**Status:** Polished / Review Pending
**Date:** 2026-03-16

---

## Executive Summary

**Call** is a category-defining AI outbound sales platform that replaces the traditional SDR workflow with an always-on AI business partner. It is architected for the **agency operating model**: one team managing many clients, each with separate leads, knowledge bases, and compliance obligations.

### The Problem
- **Agency Bottleneck:** Agencies currently spend 3+ days setting up manual cold calling for each new client.
- **Compliance Barrier:** FCC 2024 rulings have made reckless dialers a major legal liability.
- **Generic Outreach:** Traditional scripts lack depth and fail to adapt to lead objections in real-time.

### The Solution: "The 10-Minute Promise"
Call enables agencies to launch a bespoke, context-aware campaign in under 10 minutes.
- **RAG-Powered Scripts:** AI trains itself on client PDFs/URLs to generate intelligent, non-templated conversations.
- **Compliance-by-Design:** Automated TCPA disclosure, DNC scrubbing, and consent recording are intrinsic to the voice pipeline.
- **Adaptive Interaction:** Sub-500ms voice latency with real-time sentiment detection and objection handling.

---

## Success Criteria

### User Success
- **10-Minute Launch:** Users go from signup to live campaign in <10 minutes.
- **Aha! Moment:** Achieving the first booked meeting with zero human intervention.
- **White-Label Delivery:** Agencies deliver a fully branded portal to their clients immediately.
- **Zero-Anxiety Compliance:** 100% automated enforcement of DNC and consent laws.

### Business & Technical Targets
- **NPS:** >50 among agency power users.
- **Voice Latency:** End-to-end response <500ms (95th percentile).
- **RAG Accuracy:** >90% script relevance score on knowledge base queries.
- **Scalability:** 1,000+ concurrent calls per tenant without quality degradation.

---

## User Journeys

### 1. The 10-Minute Launch (Marcus, Agency Owner)
Marcus signs up, uploads a client's product doc, and launches a campaign across 1,000 leads. He hears the AI handle a "no vendor" objection using his client's specific differentiator. A meeting is booked on the client's Calendly within hour one.

### 2. High-Trust Handoff (Sarah, Enterprise Sales)
The AI encounters an enterprise-level technical question not in the knowledge base. It triggers **Warm Transfer Opt-in**, asking the prospect: "That's a technical detail—would you like me to connect you with our specialist Sarah right now?" Upon opt-in, Sarah joins the call seamlessly.

### 3. Emotional Protection (The Rejection Shield)
A harsh, rude lead yells at the AI. The AI de-escalates ("Understood, I'll remove you from our list."), and the **Rejection Shield** filters this interaction from the human manager's feed, showing only the neutral/positive interactions to preserve team morale.

### 4. White-Labeled Client Onboarding (Agency Scale)
Marcus closes a new client. He enters their brand colors and logo into his Call dashboard and maps a custom domain. He sends the login to his client. The client logs in to a fully branded portal, uploads their own knowledge base, and sees their unique AI "Avery" ready to call—never seeing a reference to the underlying "Call" platform.

---

## Product Scope & Phasing

### Phase 1: Platform MVP (The Agency Foundation)

- **Multi-tenant Infrastructure:** Isolated client sub-accounts and namespaces.
- **Contextual Knowledge Base:** Document ingestion → Contextual script generation.
- **Hybrid Call Engine:** AI Voice Mode + Human "Agent Cockpit" Mode.
- **Core Integrations:** GoHighLevel sync (outcomes/tags) + Calendly booking triggers.
- **Compliance Guard:** 100% automated scrub against DNC registries + jurisdiction-aware consent recording.

### Phase 2: Growth & Retention

- **Gamification System:** "Century Club" (100 calls) and "Rainmaker" (10 closes) badges + login streaks.
- **Momentum Starter:** Smart queuing of warmest leads first to ensure early session success.
- **Outreach Expansion:** Post-call SMS follow-up sequences based on dispositions.
- **Advanced Analytics:** 15-second retention tracker (North Star metric).

### Phase 3: Vision (The Category King)
- **Autonomous Sales Orchestration:** Cross-channel (Call + SMS + Email) AI agents.
- **Global Expansion:** Multi-language support and EU/Global data residency.
- **Marketplace:** Vertical-specific AI personas and agency-contributed script templates.

---

## Domain Compliance Matrix

| Regulation | Product Capability | Verification Method |
| :--- | :--- | :--- |
| **TCPA (Telephone Consumer Protection Act)** | Automated opt-out processing and revocation management. | Weekly audit of "removed" lead logs. |
| **FCC 2024 Ruling** | 1-to-1 express written consent validation before dialing triggers. | Real-time API check for consent timestamps. |
| **State DNC Laws (Florida, Oklahoma)** | Jurisdiction-aware cooling-off periods and calling hours logic. | Automated dialer gating based on area code / local time. |
| Consent Recording | 100% encrypted call recordings with "This call is recorded" disclosure logic. | Random 5% recording audit against disclosure timestamp. |

---

## Governance & SaaS Model

### Tenant Hierarchy

- **Platform Provider:** Global system config, telephony provider management, billing.
- **Agency:** Multi-client management, branded portal settings, aggregate usage billing.
- **Client (Sub-account):** Knowledge base management, lead uploads, campaign execution.

### RBAC Matrix

| Role | Lead Management | KB Management | Billing Access | Portal Branding |
| :--- | :---: | :---: | :---: | :---: |
| **Platform Admin** | Full | Full | Full | Full |
| **Agency Admin** | Full | Client-level | Full | Full |
| **Client User** | Selected | Full | Restricted | None |

### Subscription Tiers
- **Seed (Entry-level):** 1 Agency, 3 Clients, 1,000 calls/mo, standard GHL integration.
- **Scale (Professional):** 1 Agency, Unlimited Clients, 25,000 calls/mo, Full White-Labeling.
- **Apex (Enterprise):** Unified Agency + Direct API, Custom LLM endpoints, Dedicated concurrency.

---

## Functional Requirements

### 1. Agency & Tenant Management
- **FR1:** Users can manage a multi-layer hierarchy consisting of Platform Provider, Agency, and Client Sub-account.
- **FR2:** Users can configure a white-labeled portal including custom domain mapping, logos, and specific color schemes.
- **FR3:** System shall enforce hard usage caps and trigger soft alerts at 80% and 95% of the allocated monthly call balance per tenant.

### 2. AI Voice & Telephony
- **FR4:** System shall maintain a voice pipeline latency of <500ms with support for natural lead interruptions.
- **FR5:** **Warm Transfer Opt-in:** System shall trigger AI-to-human handoff based on lead request or confidence score thresholds.
- **FR6:** **Handoff Latency:** System shall allow a live human to join an active session in <2 seconds.

### 3. Knowledge Base & Personalization
- **FR7:** Users can ingest context via PDF, URL, and TXT files into isolated knowledge retrieval namespaces.
- **FR8:** System shall generate dynamic call icebreakers based on lead public signals (LinkedIn/News).
- **FR9:** System shall generate objection responses using knowledge base context with >95% factual accuracy.

### 4. Compliance & Operations
- **FR10:** System shall automatically scrub lead lists against National, State, and internal DNC registries before dialing.
- **FR11:** System shall record jurisdiction-aware disclosures and verify lead consent based on 1-party or all-party state requirements.
- **FR12:** **Rejection Shield:** System shall automatically flag and filter call outcomes with sentiment scores indicating hostility or abuse from standard management feeds.

### 5. Integrations & CRM
- **FR13:** **CRM Outcome Sync:** System shall push call dispositions, notes, and tags to GoHighLevel within 2 seconds of call termination.
- **FR14:** **Real-time Appointment Booking:** System shall verify Calendly availability and execute booking confirmation during the call session upon lead request.

---

## Non-Functional Requirements

### 1. Performance
- **NFR.P1:** Voice Latency: <500ms end-to-end for 95% of calls as measured by edge-node telemetry.
- **NFR.P2:** Retrieval Latency: Knowledge base search and context injection in <200ms for 95th percentile.
- **NFR.P3:** Sync Speed: CRM outcome posting in <2s post-call.

### 2. Reliability & Scalability
- **NFR.R1:** Uptime: 99.9% for calling bridge and core API as measured by external health checks.
- **NFR.R2:** Provider Fallback: Auto-failover to secondary telephony provider in <3s without session drop.
- **NFR.S1:** Concurrency: Support 1,000+ simultaneous AI voice sessions per tenant namespace.

### 3. Security & Legal
- **NFR.Sec1:** Data Isolation: Mandatory tenant-level logical separation of all database objects and files; validated by cross-tenant query audits.
- **NFR.Sec2:** Immutable Auditing: Call recordings and consent records stored for a minimum of 7 years with tamper-evident logs.
- **NFR.Sec3:** Encryption: AES-256 for recordings at rest; TLS 1.3 for all data in transit.

---

## Innovation Analysis

- **Sales Partner, Not Dialer:** Call is the first platform to use RAG to create individual sales "minds" for every client, rather than executing static scripts.
- **The Psychology of Momentum:** By applying **Momentum Starter** (warmest leads first) and **Gamification**, we solve the psychological friction of outbound sales.
- **Emotional AI:** The **Rejection Shield** is a novel B2B pattern that treats the user's emotional state as a resource to be protected by the AI.
