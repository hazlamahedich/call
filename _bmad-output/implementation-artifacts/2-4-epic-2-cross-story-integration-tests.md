# Story 2.4: Epic 2 Cross-Story Integration Tests

Status: ready-for-dev

## Story

As a Technical Lead,
I want cross-story integration tests that validate the full voice pipeline works end-to-end,
so that Stories 2.1 (Telephony Bridge), 2.2 (Transcription), and 2.3 (TTS Fallback) operate correctly as a unified system.

## Context

Epic 2 implements three independently tested stories:
- **2.1**: Vapi webhook reception → call record persistence → status lifecycle
- **2.2**: Transcript events → `transcript_entries` persistence → speech events → interruption detection → WebSocket broadcast → call-end transcript aggregation
- **2.3**: TTS provider abstraction → latency tracking → automatic fallback → circuit breaker → recovery → all-providers-failed handling → session TTL cleanup

Each story has strong unit test coverage (97/100 for 2.3, 93/100 for 2.1). However, the seams between stories have not been tested. This story covers the integration surface where Stories 2.1, 2.2, and 2.3 interact.

## Acceptance Criteria

1. **Lifespan Startup/Shutdown Integration**: Given the FastAPI application lifespan, when the app starts, then `get_tts_orchestrator()` is called, `start_cleanup_task()` runs, and on shutdown `shutdown_tts()` cleanly closes all HTTP clients. The lifespan context manager yields without error and cleans up even if startup raises. [Source: apps/api/main.py — lifespan function, ARCH9]

2. **Webhook call-end → TTS Session Reset**: Given an active call with an ongoing TTS session, when a `call-end` webhook is received at `POST /webhooks/vapi/call-events`, then the TTS orchestrator's `reset_session(vapi_call_id)` is called BEFORE the call record is updated to `completed`, and the session state for that call is fully evicted from the in-memory `_session_state` dict. [Source: apps/api/routers/webhooks_vapi.py:108-109, apps/api/services/tts/orchestrator.py — reset_session]

3. **Full Fallback Round-Trip with Mocked HTTP**: Given an active call session with ElevenLabs as primary provider, when 3 consecutive slow responses (>500ms) are simulated via mocked HTTP servers, then the orchestrator switches to Cartesia, records a `tts_provider_switches` row, emits a `voice_event`, and subsequent requests use Cartesia without error. The round-trip covers: `synthesize_for_call()` → provider HTTP call → latency check → fallback decision → DB write → voice event. [Source: Story 2.3 AC3, AC5; NFR.P1]

4. **Circuit Breaker Across Sessions**: Given the circuit breaker is tripped for ElevenLabs (3+ session-level fallbacks), when a new call session is created, then the orchestrator skips ElevenLabs and starts the new session on Cartesia. After the circuit cooldown elapses, the next session retries ElevenLabs. [Source: Story 2.3 carry-forward — ProviderCircuitBreaker]

5. **Transcript + TTS During Active Call**: Given an active call with TTS running, when a `transcript` webhook arrives mid-call, then both the TTS synthesis pipeline and the transcript handler operate without interfering with each other. The transcript is persisted, the TTS session state is untouched, and both services share the same `vapi_call_id` and `org_id` for correlation. [Source: Stories 2.2 + 2.3 intersection in webhooks_vapi.py]

6. **Call-End Triggers Transcript Aggregation AND TTS Cleanup**: Given a call that has accumulated transcript entries and an active TTS session, when `call-end` is received, then (a) transcript aggregation populates `calls.transcript`, (b) TTS session is reset, and (c) the call status transitions to `completed` — all in the correct order without conflicts. [Source: Stories 2.1, 2.2, 2.3 convergence at call-end]

7. **Tenant Isolation Across Voice Pipeline**: Given two concurrent calls from different orgs, when each call has its own TTS session and transcript events, then TTS session state, transcript entries, and provider switches are fully isolated by `org_id`. Cross-tenant queries return zero results. [Source: NFR.Sec1, ARCH2 — RLS]

## Tasks / Subtasks

### Phase 1: Lifespan & Factory Integration (AC 1)

- [ ] Create `apps/api/tests/test_epic2_lifespan_integration.py`
  - [ ] Test lifespan startup creates orchestrator and starts cleanup task
  - [ ] Test lifespan shutdown calls `shutdown_tts()` and closes clients
  - [ ] Test shutdown is safe even if startup partially failed
  - [ ] Test factory singleton behavior across multiple `get_tts_orchestrator()` calls

### Phase 2: Webhook → TTS Session Reset Integration (AC 2)

- [ ] Create `apps/api/tests/test_epic2_webhook_tts_reset.py`
  - [ ] Test `call-end` webhook calls `reset_session(vapi_call_id)` before call status update
  - [ ] Test reset evicts session from `_session_state`
  - [ ] Test reset is safe when no TTS session exists for the call
  - [ ] Test `call-failed` also resets TTS session (defensive — prevents memory leak)

### Phase 3: Full Fallback Round-Trip (AC 3)

- [ ] Create `apps/api/tests/test_epic2_fallback_roundtrip.py`
  - [ ] Test 3 slow responses trigger switch to fallback provider
  - [ ] Test provider switch writes to `tts_provider_switches` (mocked DB)
  - [ ] Test voice event is emitted on switch
  - [ ] Test post-switch requests use the new provider
  - [ ] Test round-trip from `synthesize_for_call()` entry to final response

### Phase 4: Circuit Breaker Cross-Session (AC 4)

- [ ] Create `apps/api/tests/test_epic2_circuit_breaker_cross_session.py`
  - [ ] Test tripped circuit causes new sessions to skip provider
  - [ ] Test circuit recovery after cooldown allows retry
  - [ ] Test circuit breaker state persists across `get_or_create_session` calls
  - [ ] Test circuit breaker resets on success after cooldown

### Phase 5: Multi-Story Convergence (ACs 5, 6, 7)

- [ ] Create `apps/api/tests/test_epic2_transcript_tts_coexistence.py`
  - [ ] Test transcript handler and TTS session don't interfere during active call
  - [ ] Test both services share `vapi_call_id` and `org_id`
- [ ] Create `apps/api/tests/test_epic2_call_end_convergence.py`
  - [ ] Test call-end triggers transcript aggregation + TTS reset + status update in order
  - [ ] Test all three operations complete without conflicts
- [ ] Create `apps/api/tests/test_epic2_tenant_isolation.py`
  - [ ] Test concurrent calls from different orgs maintain isolated TTS sessions
  - [ ] Test transcript entries are org-scoped
  - [ ] Test provider switches are org-scoped

### Phase 6: Quality Gates

- [ ] All tests pass: `PYTHONPATH=apps/api apps/api/.venv/bin/pytest apps/api/tests/test_epic2_*.py -v`
- [ ] No test file exceeds 300 lines
- [ ] All tests have `[2.4-INT-XXX]` traceability IDs
- [ ] All tests use `_make_settings(**overrides)` helper pattern
- [ ] Priority markers (`_P0_`, `_P1_`, `_P2_`) in test function names

## Technical Notes

### Test Infrastructure

- **Mock HTTP Servers**: Use `unittest.mock.AsyncMock` for TTS provider `synthesize()` methods rather than real HTTP servers. This follows the existing pattern in all `test_tts_*.py` files.
- **Database Mocking**: Use `unittest.mock.MagicMock` for `AsyncSession` with `_make_result()` and `_make_row()` helpers from `tests/support/mock_helpers.py`.
- **Settings Override**: Use `_make_settings(**overrides)` factory pattern consistent with all Story 2.3 tests.
- **Orchestrator Isolation**: Each test must call `factory_module._orchestrator = None` in teardown (use `@pytest.fixture(autouse=True)` following existing pattern).

### Order of Operations (AC 6)

The `call-end` handler in `webhooks_vapi.py` currently:
1. Resets TTS session (`orchestrator.reset_session`)
2. Calls `handle_call_ended` (which updates call status and aggregates transcript)

This order is correct — TTS cleanup should happen before call status transitions. Tests should verify this order is maintained.

### Integration Test IDs

Follow the project convention: `[2.4-INT-001]` through `[2.4-INT-NNN]` where `2.4` is the story number and `INT` indicates integration-level tests.

### Files to Create

| File | AC Coverage | Estimated Tests |
|------|------------|----------------|
| `test_epic2_lifespan_integration.py` | AC 1 | 4 |
| `test_epic2_webhook_tts_reset.py` | AC 2 | 4 |
| `test_epic2_fallback_roundtrip.py` | AC 3 | 5 |
| `test_epic2_circuit_breaker_cross_session.py` | AC 4 | 4 |
| `test_epic2_transcript_tts_coexistence.py` | AC 5 | 3 |
| `test_epic2_call_end_convergence.py` | AC 6 | 3 |
| `test_epic2_tenant_isolation.py` | AC 7 | 3 |
| **Total** | | **~26** |

## Dependencies

- Story 2.1: `apps/api/routers/webhooks_vapi.py`, `apps/api/services/vapi.py`, `apps/api/models/call.py`
- Story 2.2: `apps/api/services/transcription.py`, `apps/api/models/transcript.py`, `apps/api/models/voice_event.py`
- Story 2.3: `apps/api/services/tts/orchestrator.py`, `apps/api/services/tts/factory.py`, `apps/api/services/tts/base.py`
- Shared: `apps/api/config/settings.py`, `apps/api/main.py`, `apps/api/database/session.py`
