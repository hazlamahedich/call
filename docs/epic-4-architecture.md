# Epic 4: Compliance Guardrail & Rejection Shield — Architecture Design

**Status:** DRAFT  
**Date:** 2026-04-10  
**Author:** Team Mantis A  
**Epic Scope:** Stories 4.1–4.6

---

## Table of Contents

1. [Current State Assessment](#1-current-state-assessment)
2. [Data Models](#2-data-models)
3. [Call State Machine](#3-call-state-machine)
4. [DNC Registry Integration (Story 4.1)](#4-dnc-registry-integration)
5. [State-Aware Regulatory Filter (Story 4.2)](#5-state-aware-regulatory-filter)
6. [Rejection Shield (Story 4.3)](#6-rejection-shield)
7. [Compliance Audit Logging (Story 4.4)](#7-compliance-audit-logging)
8. [Compliance Dashboard (Story 4.5)](#8-compliance-dashboard)
9. [Real-Time Escalation Bridge (Story 4.6)](#9-real-time-escalation-bridge)
10. [Settings & Configuration](#10-settings--configuration)
11. [Migration Plan](#11-migration-plan)
12. [Risk Assessment](#12-risk-assessment)

---

## 1. Current State Assessment

### What Exists

| Component                 | Status                                                       | Location                             |
| ------------------------- | ------------------------------------------------------------ | ------------------------------------ |
| `Call` model              | Basic: `pending → in_progress → completed/failed`            | `models/call.py`                     |
| `Lead` model              | Minimal: `name, email, phone, status, custom_fields`         | `models/lead.py`                     |
| `packages/compliance`     | **Stub** — 2 constants, no logic                             | `packages/compliance/index.ts`       |
| `_compliance_pre_check()` | **Placeholder** — imports from stub, does nothing            | `routers/calls.py:31`                |
| `VoiceEvent` model        | Speech events only (start/end/interruption)                  | `models/voice_event.py`              |
| `TranscriptEntry` model   | Real-time transcript entries                                 | `models/transcript.py`               |
| `FactualVerificationLog`  | Epic 3 pattern — good reference for compliance logging       | `models/factual_verification_log.py` |
| WebSocket manager         | In-memory broadcast by call_id                               | `services/ws_manager.py`             |
| VAPI webhook handler      | call-start, call-end, call-failed, transcript, speech events | `routers/webhooks_vapi.py`           |

### What's Missing (Gaps)

1. **No DNC check logic** — `_compliance_pre_check()` is a no-op
2. **No blocklist model** — no way to store DNC-blocked or tenant-blocked leads
3. **No state-aware calling hours** — no timezone/state → calling window mapping
4. **No sentiment analysis** — no hostility detection on live transcripts
5. **No compliance audit log** — no immutable, hash-chained log table
6. **No consent capture** — no recording disclosure or verbal consent tracking
7. **No escalation bridge** — no real-time supervisor alert for compliance events
8. **Call model lacks compliance states** — only `pending/in_progress/completed/failed`

### Key Design Constraints

- **VAPI is the telephony layer** — all call lifecycle events come through webhooks. We cannot inject compliance checks _inside_ VAPI's dial logic. We must intercept **before** calling VAPI's `initiate_call()` API.
- **Transcript events are real-time** — we can analyze lead speech for hostility as it arrives.
- **Redis is available** — for DNC cache, real-time blocklist lookups, and pub/sub for escalation alerts.
- **PostgreSQL RLS is the tenant isolation mechanism** — all new models inherit `TenantModel`.

---

## 2. Data Models

### 2.1 New Models

#### `DncCheckLog` — Story 4.1

Records every DNC check (both at upload and pre-dial) for audit trail.

```python
# apps/api/models/dnc_check_log.py

class DncCheckLog(TenantModel, table=True):
    __tablename__ = "dnc_check_logs"

    phone_number: str           # E.164 format, indexed
    check_type: str             # "upload_scrub" | "pre_dial" | "manual"
    source: str                 # "national_dnc" | "state_dnc" | "tenant_blocklist"
    result: str                 # "clear" | "blocked" | "error"
    lead_id: Optional[int]      # FK to leads.id
    campaign_id: Optional[int]  # context
    call_id: Optional[int]      # FK to calls.id (for pre-dial checks)
    response_time_ms: int       # latency of the check
    raw_response: Optional[str] # JSON blob from DNC provider (for audit)
    checked_at: datetime        # when the check happened
```

#### `BlocklistEntry` — Stories 4.1, 4.3

Tenant-level DNC/blocklist. Combines DNC registry results with manual and auto-blocked entries.

```python
# apps/api/models/blocklist_entry.py

class BlocklistEntry(TenantModel, table=True):
    __tablename__ = "blocklist_entries"

    phone_number: str           # E.164, indexed (unique per org_id)
    source: str                 # "national_dnc" | "state_dnc" | "tenant_manual" | "rejection_shield"
    reason: Optional[str]       # free-text reason
    lead_id: Optional[int]      # FK to leads.id
    auto_blocked_at: Optional[datetime]  # when auto-blocked (rejection shield)
    expires_at: Optional[datetime]       # TTL for temporary blocks (NULL = permanent)
```

#### `ComplianceLog` — Story 4.4

Immutable, hash-chained audit log. INSERT-only — no UPDATE/DELETE allowed.

```python
# apps/api/models/compliance_log.py

class ComplianceLog(TenantModel, table=True):
    __tablename__ = "compliance_logs"

    event_type: str             # "consent_capture" | "recording_disclosure" | "dnc_block" |
                                # "graceful_goodnight" | "rejection_shield" | "escalation"
    call_id: Optional[int]      # FK to calls.id
    lead_id: Optional[int]      # FK to leads.id
    phone_number: Optional[str] # E.164
    content_hash: str           # SHA-256 of content_snapshot
    content_snapshot: str       # JSON: { transcript_snippet, audio_ref, etc. }
    prev_hash: Optional[str]    # hash of previous row → chain
    ntp_timestamp: Optional[float]  # from NTP server
    sequence_number: int        # monotonic counter per org_id
    actor: str                  # "system" | "agent" | "supervisor" | "lead"
    metadata: Optional[dict]    # flexible JSON for event-specific data
```

#### `StateRegulation` — Story 4.2

State-specific calling rules. Seeded from FCC/TCPA data.

```python
# apps/api/models/state_regulation.py

class StateRegulation(TenantModel, table=True):
    __tablename__ = "state_regulations"

    state_code: str             # "CA", "NY", "FL", etc. (indexed, unique per org or global)
    country_code: str           # "US" default
    calling_hours_start: str    # "08:00" (local time)
    calling_hours_end: str      # "21:00" (local time)
    timezone: str               # "America/Los_Angeles"
    consent_type: str           # "one_party" | "two_party" | "all_party"
    recording_disclosure_required: bool
    disclosure_template: Optional[str]  # what to say
    is_global: bool             # true = shared across all orgs
```

#### `EscalationEvent` — Story 4.6

Tracks supervisor escalation alerts and responses.

```python
# apps/api/models/escalation_event.py

class EscalationEvent(TenantModel, table=True):
    __tablename__ = "escalation_events"

    call_id: int                # FK to calls.id
    trigger_type: str           # "compliance_sensitive" | "hostility" | "legal_threat" | "credit_card"
    severity: str               # "low" | "medium" | "high" | "critical"
    transcript_snapshot: Optional[str]  # last N turns at trigger time
    supervisor_id: Optional[str]        # Clerk user ID
    action_taken: Optional[str]         # "takeover" | "force_close" | "dismissed" | "timeout"
    action_at: Optional[datetime]
    alert_sent_at: datetime
    resolved_at: Optional[datetime]
```

### 2.2 Call Model Extension

Add new status values and compliance fields to the existing `Call` model:

```python
# Extend Call model
class Call(TenantModel, table=True):
    # ... existing fields ...

    # New compliance fields
    compliance_status: Optional[str] = Field(default=None, max_length=30)
    # "unchecked" | "passed" | "blocked_dnc" | "blocked_hours" | "blocked_consent"

    state_code: Optional[str] = Field(default=None, max_length=5)
    # Lead's state (derived from area code) for regulatory lookup

    consent_captured: bool = Field(default=False)
    # Whether recording disclosure was played and consent obtained

    graceful_goodnight_triggered: bool = Field(default=False)
    # Whether the Graceful Goodnight protocol was activated
```

**New valid `status` values:**

- `blocked_dnc` — Pre-dial DNC check failed
- `blocked_hours` — Outside legal calling window
- `graceful_goodnight` — Call ended via Graceful Goodnight protocol
- `escalated` — Supervisor took over (transition state)

### 2.3 ER Diagram (Text)

```
leads ─────────┐
  │             │
  │ 1:N         │ 1:N
  ▼             ▼
calls ──────── dnc_check_logs
  │             blocklist_entries
  │ 1:N         compliance_logs
  ├── transcript_entries    escalation_events
  ├── voice_events          state_regulations
  ├── dnc_check_logs
  ├── compliance_logs
  └── escalation_events

state_regulations (global shared data, no FK dependencies)
```

---

## 3. Call State Machine

### Current Flow

```
pending → in_progress → completed
                      → failed
```

### Extended Flow (Epic 4)

```
                    ┌─────────────┐
                    │   pending   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ DNC check   │──fail──► blocked_dnc (terminal)
                    └──────┬──────┘
                           │ pass
                    ┌──────▼──────┐
                    │ Hours check │──fail──► blocked_hours (terminal, scheduled)
                    └──────┬──────┘
                           │ pass
                    ┌──────▼──────┐
                    │in_progress  │
                    └──┬──┬──┬──┬─┘
                       │  │  │  │
            graceful   │  │  │  │ normal
            goodnight  │  │  │  │ end
                       │  │  │  │
          ┌────────────┘  │  │  └────► completed
          │               │  │
          ▼               │  │    escalated (supervisor takeover)
  graceful_goodnight      │  │        │
      (terminal)          │  │        ├──► completed (supervisor ends)
                          │  │        └──► in_progress (bounced back to AI)
                          │  │
                    rejection  failed
                    shield     (terminal)
                          │
                          ▼
                    completed
                    (lead auto-blocklisted)
```

### Key State Transitions

| From        | To                 | Trigger                        | Handler                                     |
| ----------- | ------------------ | ------------------------------ | ------------------------------------------- |
| pending     | blocked_dnc        | DNC check fails                | `services/compliance/dnc.py`                |
| pending     | blocked_hours      | Outside calling window         | `services/compliance/regulatory.py`         |
| pending     | in_progress        | All checks pass, VAPI confirms | `services/vapi.py::handle_call_started`     |
| in_progress | graceful_goodnight | Time → 8:59 PM local           | `services/compliance/graceful_goodnight.py` |
| in_progress | completed          | Normal call end                | `services/vapi.py::handle_call_ended`       |
| in_progress | completed          | Rejection Shield triggered     | `services/compliance/rejection_shield.py`   |
| in_progress | escalated          | Supervisor takes over          | `services/compliance/escalation.py`         |
| escalated   | completed          | Supervisor ends call           | WebSocket event                             |

---

## 4. DNC Registry Integration (Story 4.1)

### Architecture: "Double-Hop" Pattern

```
┌─────────────────────┐     ┌─────────────────────┐
│  HOP 1: UPLOAD SCRUB│     │  HOP 2: PRE-DIAL    │
│  (batch, async)     │     │  (real-time, <50ms) │
│                     │     │                     │
│  Lead list upload   │     │  trigger_outbound_  │
│       │             │     │  call() pipeline    │
│       ▼             │     │       │             │
│  Batch DNC lookup   │     │       ▼             │
│  (full API call)    │     │  Redis cache check  │
│       │             │     │       │             │
│       ▼             │     │  (cache miss?)      │
│  Mark blocked leads │     │       ▼             │
│  Create DncCheckLog │     │  Real-time API call │
│  Create Blocklist   │     │       │             │
│  entries            │     │       ▼             │
└─────────────────────┘     │  Pass/Fail → VAPI   │
                            │  Create DncCheckLog │
                            └─────────────────────┘
```

### DNC API Provider Recommendation

**Recommended: [DNC.com API](https://www.dnc.com/api/)** (also known as Gryphon Networks / PossibleNOW)

**Why:**

- Industry-standard scrub API with real-time and batch endpoints
- Covers National DNC + State DNC + litigator lists
- ~$0.01–0.03/check at scale (batch), ~$0.05/check real-time
- Response time: <100ms for real-time endpoint
- REST API with JSON responses
- Alternative: **LeadSpend** (acquired byMeta), **Scrubit**

**Integration Pattern:**

```python
# services/compliance/dnc.py

async def check_dnc_realtime(phone_number: str, org_id: str) -> DncCheckResult:
    # 1. Check Redis cache first (TTL: 24h)
    cached = await redis.get(f"dnc:{org_id}:{phone_number}")
    if cached:
        return DncCheckResult(result=cached, source="cache")

    # 2. Check tenant blocklist
    blocked = await check_tenant_blocklist(session, phone_number, org_id)
    if blocked:
        return DncCheckResult(result="blocked", source="tenant_blocklist")

    # 3. Call DNC provider API
    result = await dnc_api_client.lookup(phone_number)

    # 4. Cache result
    await redis.setex(f"dnc:{org_id}:{phone_number}", 86400, result.status)

    # 5. Log the check
    await create_dnc_check_log(...)

    return result
```

### Pre-Dial Integration Point

The DNC check must be injected into `trigger_outbound_call()` in `services/vapi.py` **before** the `initiate_call()` VAPI API call:

```python
# services/vapi.py — modified trigger_outbound_call()

async def trigger_outbound_call(session, org_id, phone_number, ...):
    # NEW: Pre-dial compliance gate
    from services.compliance.dnc import check_dnc_realtime
    from services.compliance.regulatory import check_calling_hours

    dnc_result = await check_dnc_realtime(phone_number, org_id)
    if dnc_result.is_blocked:
        # Create blocked call record
        call = Call(phone_number=phone_number, status="blocked_dnc",
                    compliance_status="blocked_dnc")
        call = await _call_service.create(session, call)
        await create_compliance_log(session, org_id, "dnc_block", call.id, ...)
        raise ComplianceBlockError("DNC_BLOCKED", phone_number)

    hours_result = await check_calling_hours(phone_number, org_id)
    if not hours_result.is_within_window:
        call = Call(phone_number=phone_number, status="blocked_hours",
                    compliance_status="blocked_hours", state_code=hours_result.state_code)
        call = await _call_service.create(session, call)
        raise ComplianceBlockError("OUTSIDE_CALLING_HOURS", phone_number,
                                   next_available=hours_result.next_window)

    # ... existing VAPI initiation logic ...
```

---

## 5. State-Aware Regulatory Filter (Story 4.2)

### Architecture

```
Phone Number (E.164)
       │
       ▼
  Area Code → State Mapping
       │
       ▼
  StateRegulation lookup (Redis-cached)
       │
       ├── calling_hours_start/end → Is now within window?
       │     NO → Block + schedule for next window
       │     YES → Continue
       │
       ├── consent_type == "two_party"?
       │     YES → Queue recording disclosure for call start
       │
       └── recording_disclosure_required?
             YES → Inject disclosure into first AI turn
```

### Area Code → State Mapping

Use a static lookup table (~300 US area codes). Cached in Redis.

```python
# services/compliance/area_code_map.py

AREA_CODE_TO_STATE: dict[str, str] = {
    "201": "NJ", "202": "DC", "203": "CT", "205": "AL", ...
}
```

### Graceful Goodnight Protocol

When a call is approaching the calling window cutoff:

```
1. Background task checks active calls every 30 seconds
2. For each active call, compute time remaining in local window
3. If remaining < 5 minutes:
   - Send WebSocket alert to supervisor dashboard
   - Inject "wind-down" instruction into AI via VAPI assistant update
4. If remaining < 1 minute:
   - Force "Graceful Goodnight" — AI delivers closing script:
     "I appreciate your time today. I have to let you go now,
      but I'd love to continue this conversation tomorrow.
      Have a wonderful evening!"
   - End call via VAPI API
   - Set call status = "graceful_goodnight"
   - Log to ComplianceLog
```

**VAPI Integration:** Use VAPI's `PATCH /call/{id}` to inject a system message that overrides the current conversation flow, or use the `end-call` tool in the assistant config.

### Two-Party Consent Flow

For states requiring two-party consent (e.g., CA, CT, FL, IL, MD, MA, MI, MT, NV, NH, OR, PA, WA):

```
1. Call starts → VAPI sends call-start webhook
2. handle_call_started() checks StateRegulation for lead's state
3. If consent_type == "two_party":
   a. Queue first AI turn as disclosure:
      "Before we begin, I want to let you know this call is being
       recorded for quality and training purposes. Is that okay?"
   b. Set call.consent_captured = False
   c. Listen for lead's affirmative response in transcript
   d. On affirmative → set consent_captured = True, log to ComplianceLog
   e. On negative → trigger Graceful Goodnight, log refusal
```

---

## 6. Rejection Shield (Story 4.3)

### Architecture: Multi-Stage Detection Pipeline

```
Live Transcript Entry (lead role)
       │
       ▼
┌──────────────────────────────┐
│  Stage 1: Keyword Detection  │  (< 5ms, regex)
│  "stop calling", "sue",      │
│  "remove me", "don't call",  │
│  "attorney", "harassment"    │
└──────────┬───────────────────┘
           │ match?
           ▼
┌──────────────────────────────┐
│  Stage 2: Sentiment Check    │  (< 50ms, LLM or local)
│  Analyze last 3 turns for    │
│  hostility score             │
└──────────┬───────────────────┘
           │ hostility > threshold?
           ▼
┌──────────────────────────────┐
│  Stage 3: Shield Activation  │
│  1. Override AI script node  │
│  2. Execute Polite Retreat   │
│  3. Auto-blocklist lead      │
│  4. Pulse-Maker → RED alert  │
│  5. Log to ComplianceLog     │
│  6. WebSocket alert to       │
│     supervisor dashboard     │
└──────────────────────────────┘
```

### Keyword Patterns (Tier 1 — Immediate Shield)

```python
REJECTION_SHIELD_KEYWORDS = [
    r"\bstop\s+call", r"\bdon'?t\s+call", r"\bdo\s+not\s+call",
    r"\bremove\s+me", r"\btake\s+me\s+off",
    r"\bsue\s+you", r"\blawsuit", r"\battorney", r"\blawyer",
    r"\bharass", r"\bpolice", r"\breport\s+you",
    r"\bfuck\s*(off|you)?", r"\bgo\s+to\s+hell",
]
```

### Sentiment Scoring (Tier 2)

**Approach: Lightweight local classifier** (no external API call for latency)

Option A: Use `VADER` sentiment analysis (Python `nltk.sentiment.vader`) — zero latency, no API key needed.  
Option B: Use the LLM provider to score hostility in a single prompt (< 200ms).

**Recommendation:** Start with VADER for Tier 2 (fast, free, local). Add LLM fallback for ambiguous cases.

### Polite Retreat Templates

```python
POLITE_RETREAT_TEMPLATES = [
    "I completely understand, and I sincerely apologize for the inconvenience. "
    "I'll remove your number from our list right away. Have a wonderful day.",

    "Of course, I respect your wishes. I'll make sure you're not contacted again. "
    "Thank you for your time, and I hope you have a great day.",

    "I'm sorry to have bothered you. I'll remove you from our call list immediately. "
    "Please don't hesitate to reach out if you ever change your mind. Take care!",
]
```

### Integration Point: `handle_transcript_event()`

```python
# services/transcription.py — modified handle_transcript_event()

async def handle_transcript_event(session, vapi_call_id, org_id, transcript_data):
    entry = await _create_transcript_entry(...)

    # NEW: Rejection Shield analysis (only for lead speech)
    if entry.role == "lead":
        from services.compliance.rejection_shield import analyze_lead_turn
        shield_result = await analyze_lead_turn(session, entry.text, org_id, entry.call_id)
        if shield_result.should_activate:
            await activate_rejection_shield(session, entry.call_id, org_id, shield_result)

    # ... existing WebSocket broadcast ...
```

### Pulse-Maker UI Integration

Via WebSocket broadcast when Rejection Shield activates:

```json
{
  "type": "compliance_alert",
  "alertType": "rejection_shield",
  "callId": 123,
  "severity": "high",
  "message": "Lead requested removal. Polite Retreat activated.",
  "uiAction": { "pulseMakerColor": "red", "showAlert": true }
}
```

---

## 7. Compliance Audit Logging (Story 4.4)

### Hash Chain Architecture

```
┌──────────────────────────────────────────────────┐
│  compliance_logs table (INSERT only)             │
│                                                  │
│  Row 1: seq=1, content_hash=SHA256(data),        │
│         prev_hash=NULL (genesis)                  │
│                                                  │
│  Row 2: seq=2, content_hash=SHA256(data),        │
│         prev_hash=Row1.content_hash               │
│                                                  │
│  Row 3: seq=3, content_hash=SHA256(data),        │
│         prev_hash=Row2.content_hash               │
│  ...                                             │
│                                                  │
│  Verification: SHA256(prev_hash + content_snapshot│
│  + ntp_timestamp + org_id) == content_hash       │
└──────────────────────────────────────────────────┘
```

### Hash Chain Implementation

```python
# services/compliance/audit.py

import hashlib
import ntplib

async def append_compliance_log(
    session: AsyncSession,
    org_id: str,
    event_type: str,
    content_snapshot: dict,
    call_id: int = None,
    lead_id: int = None,
    phone_number: str = None,
    actor: str = "system",
) -> ComplianceLog:
    # 1. Get NTP timestamp
    ntp_ts = await _get_ntp_timestamp()

    # 2. Get previous hash (highest sequence for this org)
    prev = await session.execute(
        text("SELECT content_hash, sequence_number FROM compliance_logs "
             "WHERE org_id = :org_id ORDER BY sequence_number DESC LIMIT 1"),
        {"org_id": org_id}
    )
    prev_row = prev.first()
    prev_hash = prev_row[0] if prev_row else "0" * 64
    next_seq = (prev_row[1] + 1) if prev_row else 1

    # 3. Compute hash
    snapshot_json = json.dumps(content_snapshot, sort_keys=True)
    hash_input = f"{prev_hash}:{snapshot_json}:{ntp_ts}:{org_id}:{next_seq}"
    content_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    # 4. Insert (raw SQL — no ORM update/delete possible)
    log = ComplianceLog(
        org_id=org_id,
        event_type=event_type,
        call_id=call_id,
        lead_id=lead_id,
        phone_number=phone_number,
        content_hash=content_hash,
        content_snapshot=snapshot_json,
        prev_hash=prev_hash,
        ntp_timestamp=ntp_ts,
        sequence_number=next_seq,
        actor=actor,
    )
    session.add(log)
    await session.flush()
    return log
```

### Immutability Enforcement

1. **Database level:** Row-Level Security policy preventing UPDATE/DELETE on `compliance_logs`
2. **Application level:** No ORM update methods on the model
3. **Verification endpoint:** `GET /compliance/audit/verify` walks the chain and reports any tampering

```sql
-- Migration: prevent updates/deletes on compliance_logs
CREATE POLICY compliance_logs_insert_only ON compliance_logs
    FOR INSERT TO app_user;
-- No SELECT, UPDATE, or DELETE policies for app_user
-- Admin-only SELECT policy for audit queries
```

### NTP Timestamp Source

Use `ntp.org` pool servers. Fallback to system clock if NTP fails (with flag in log entry).

```python
# services/compliance/ntp.py

_NTP_SERVERS = ["pool.ntp.org", "time.google.com", "time.cloudflare.com"]

async def get_ntp_timestamp() -> tuple[float, bool]:
    """Returns (timestamp, is_ntp_synchronized)"""
    client = ntplib.NTPClient()
    for server in _NTP_SERVERS:
        try:
            response = client.request(server, version=3, timeout=2)
            return response.tx_time, True
        except Exception:
            continue
    return time.time(), False  # fallback to system clock
```

---

## 8. Compliance Dashboard (Story 4.5)

### API Endpoints

```
GET  /compliance/dashboard              — Risk score summary
GET  /compliance/dashboard/campaigns    — Per-campaign risk breakdown
GET  /compliance/audit                  — Paginated audit log viewer
GET  /compliance/audit/verify           — Chain integrity verification
POST /compliance/audit/export           — PDF/CSV export of compliance proof
GET  /compliance/blocklist              — Blocklist management
POST /compliance/blocklist              — Add manual block
DELETE /compliance/blocklist/{id}       — Remove block (audit-logged)
```

### Risk Score Computation

```python
def compute_risk_score(org_id: str, period: date_range) -> RiskScore:
    total_calls = count_calls(org_id, period)
    dnc_blocks = count_dnc_blocks(org_id, period)
    rejection_shield_activations = count_shield_events(org_id, period)
    consent_failures = count_consent_failures(org_id, period)
    hour_violations = count_hour_violations(org_id, period)

    # Weighted risk score (0-100, lower = better)
    score = (
        dnc_blocks * 5 +
        rejection_shield_activations * 3 +
        consent_failures * 10 +
        hour_violations * 8
    ) / max(total_calls, 1) * 100

    return RiskScore(
        score=min(score, 100),
        level="low" if score < 20 else "medium" if score < 50 else "high",
        dnc_blocks=dnc_blocks,
        shield_activations=rejection_shield_activations,
        consent_failures=consent_failures,
        hour_violations=hour_violations,
    )
```

### Verification Badge (UX-DR14)

Campaigns with 100% compliance (zero violations in period) get a verified badge:

```json
{
  "campaign_id": 42,
  "campaign_name": "Q2 Outreach",
  "total_calls": 500,
  "compliance_score": 100,
  "verification_badge": true,
  "checks": {
    "dnc_compliant": true,
    "hours_compliant": true,
    "consent_compliant": true,
    "shield_activations": 0
  }
}
```

---

## 9. Real-Time Escalation Bridge (Story 4.6)

### Architecture

```
Live Transcript Entry
       │
       ▼
  Compliance Topic Detector
  (credit card, SSN, legal threats, explicit content)
       │ match?
       ▼
  Create EscalationEvent
       │
       ├── WebSocket alert to supervisor dashboard
       │   (call_id, trigger_type, severity, transcript snapshot)
       │
       └── Wait for supervisor response (timeout: 30s)
            │
            ├── "takeover" → VAPI bridge API → audio reroute
            ├── "force_close" → VAPI end-call API
            ├── "dismiss" → log, continue
            └── timeout → auto-dismiss + log warning
```

### VAPI Bridge Integration

VAPI supports supervisor monitoring and takeover via its API:

```python
# services/compliance/escalation.py

async def supervisor_takeover(vapi_call_id: str, supervisor_phone: str):
    """Bridge supervisor into active call via VAPI"""
    url = f"{settings.VAPI_BASE_URL}/call/{vapi_call_id}/phone"
    headers = {"Authorization": f"Bearer {settings.VAPI_API_KEY}"}
    payload = {
        "assistantId": None,  # Remove AI assistant
        "transfer": {
            "destination": supervisor_phone,
            "type": "blind"
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.patch(url, json=payload, headers=headers)
        response.raise_for_status()
```

### WebSocket Alert Format

```json
{
  "type": "escalation_alert",
  "escalationId": 789,
  "callId": 123,
  "triggerType": "credit_card",
  "severity": "critical",
  "transcriptSnapshot": "...last 5 turns...",
  "actions": ["takeover", "force_close", "dismiss"],
  "timeoutSeconds": 30
}
```

### Compliance-Sensitive Topics

```python
COMPLIANCE_SENSITIVE_PATTERNS = [
    (r"\bcredit\s+card\b", "credit_card", "high"),
    (r"\bssn\b|\bsocial\s+security", "pii_ssn", "critical"),
    (r"\bbank\s+account\b|\brouting\s+number", "financial_info", "high"),
    (r"\bsue\b|\blawsuit\b|\battorney\b", "legal_threat", "medium"),
    (r"\bI\s+record\b|\brecording\b", "recording_concern", "low"),
]
```

---

## 10. Settings & Configuration

New settings to add to `config/settings.py`:

```python
# DNC Registry
DNC_API_KEY: str = ""
DNC_API_BASE_URL: str = "https://api.dnc.com/v1"
DNC_CACHE_TTL_SECONDS: int = 86400  # 24 hours
DNC_BATCH_SIZE: int = 1000
DNC_PRE_DIAL_TIMEOUT_MS: int = 100

# Regulatory
CALLING_WINDOW_DEFAULT_START: str = "08:00"
CALLING_WINDOW_DEFAULT_END: str = "21:00"
GRACEFUL_GOODNIGHT_BUFFER_MINUTES: int = 5
GRACEFUL_GOODNIGHT_CHECK_INTERVAL_SECONDS: int = 30
CONSENT_CAPTURE_ENABLED: bool = True

# Rejection Shield
REJECTION_SHIELD_ENABLED: bool = True
REJECTION_SHIELD_HOSTILITY_THRESHOLD: float = 0.6
REJECTION_SHIELD_USE_LLM_SENTIMENT: bool = False
REJECTION_SHIELD_AUTO_BLOCKLIST: bool = True

# Escalation
ESCALATION_ENABLED: bool = True
ESCALATION_TIMEOUT_SECONDS: int = 30
ESCALATION_AUTO_DISMISS: bool = True

# Audit
COMPLIANCE_AUDIT_ENABLED: bool = True
NTP_SERVERS: str = "pool.ntp.org,time.google.com"
NTP_TIMEOUT_SECONDS: int = 2

# Dashboard
COMPLIANCE_DASHBOARD_CACHE_TTL: int = 300
```

---

## 11. Migration Plan

### New Alembic Migrations (in order)

1. **`t6u7v8w9x0y1_create_compliance_tables.py`** — Creates:
   - `dnc_check_logs`
   - `blocklist_entries`
   - `compliance_logs` (with INSERT-only policy)
   - `state_regulations`
   - `escalation_events`
   - Adds compliance columns to `calls` table

2. **`u7v8w9x0y1z2_seed_state_regulations.py`** — Seeds US state calling regulations

### New Dependencies

```
nltk>=3.8          # VADER sentiment analysis
ntplib>=0.4        # NTP timestamp source
```

### New Package Structure

```
apps/api/services/compliance/
├── __init__.py
├── dnc.py                    # Story 4.1 — DNC registry check
├── regulatory.py             # Story 4.2 — State-aware calling rules
├── graceful_goodnight.py     # Story 4.2 — Wind-down protocol
├── consent.py                # Story 4.2 — Two-party consent flow
├── rejection_shield.py       # Story 4.3 — Hostility detection + polite retreat
├── audit.py                  # Story 4.4 — Hash-chained audit logging
├── ntp.py                    # Story 4.4 — NTP timestamp source
├── escalation.py             # Story 4.6 — Supervisor escalation
├── risk_score.py             # Story 4.5 — Risk computation
└── area_code_map.py          # Area code → state mapping
```

### New Routers

```
apps/api/routers/compliance.py    # Dashboard, audit, blocklist endpoints
```

### Modified Files

| File                        | Change                                                           |
| --------------------------- | ---------------------------------------------------------------- |
| `services/vapi.py`          | Add pre-dial compliance gate to `trigger_outbound_call()`        |
| `services/transcription.py` | Add Rejection Shield + escalation analysis to transcript handler |
| `routers/webhooks_vapi.py`  | Add consent capture flow to `handle_call_started`                |
| `models/call.py`            | Add compliance fields                                            |
| `config/settings.py`        | Add compliance settings                                          |
| `main.py`                   | Mount compliance router, start background tasks                  |
| `requirements.txt`          | Add nltk, ntplib                                                 |

---

## 12. Risk Assessment

### Technical Risks

| Risk                              | Impact                         | Mitigation                               |
| --------------------------------- | ------------------------------ | ---------------------------------------- |
| DNC API latency spikes (>100ms)   | Call trigger timeout           | Redis cache + timeout circuit breaker    |
| NTP server unreachable            | Audit timestamp accuracy       | Fallback to system clock + flag          |
| Hash chain corruption             | Audit integrity                | Verification endpoint + alerting         |
| Graceful Goodnight race condition | Call extends past legal cutoff | Force-end via VAPI API as failsafe       |
| Rejection Shield false positives  | Premature call termination     | Two-tier detection (keyword + sentiment) |
| VADER misses sarcasm/subtext      | Hostility not detected         | Optional LLM sentiment fallback          |
| WebSocket not connected           | Supervisor misses alert        | Fallback to email/push notification      |

### Legal Risks

| Risk                          | Mitigation                                              |
| ----------------------------- | ------------------------------------------------------- |
| DNC data stale                | 24-hour cache TTL + pre-dial recheck                    |
| State regulation changes      | Configurable `StateRegulation` table + update mechanism |
| Consent not captured properly | Immutable audit log + verification                      |
| Recording disclosure missed   | Auto-inject into first AI turn for two-party states     |

---

## Story Dependency Graph

```
4.1 (DNC) ──────┐
                 ├──► 4.5 (Dashboard)
4.2 (Regulatory)─┤
                 │
4.3 (Shield) ───┤
                 │
4.4 (Audit Log)─┘  ← all other stories write to audit log
                 │
                 └──► 4.6 (Escalation) ← depends on 4.3 + 4.4
```

**Recommended implementation order:** 4.1 → 4.4 → 4.2 → 4.3 → 4.5 → 4.6

- 4.1 first (DNC is highest legal risk)
- 4.4 second (audit log needed by all other stories)
- 4.2 then 4.3 (core compliance logic)
- 4.5 (dashboard aggregates data from all above)
- 4.6 last (escalation depends on shield + audit)

---

_End of Epic 4 Architecture Design_
