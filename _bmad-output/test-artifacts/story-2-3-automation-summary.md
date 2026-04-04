---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-identify-targets']
lastStep: 'step-02-identify-targets'
lastSaved: '2026-04-01T19:10:00+08:00'
inputDocuments:
  - '_bmad-output/implementation-artifacts/2-3-low-latency-tts-provider-fallback-logic.md'
  - 'apps/api/services/tts/factory.py'
  - 'apps/api/services/tts/orchestrator.py'
  - 'apps/api/services/tts/elevenlabs.py'
  - 'apps/api/services/tts/cartesia.py'
  - 'apps/api/services/tts/base.py'
  - 'apps/api/routers/tts.py'
---

# Story 2.3 Test Automation Summary

## Preflight

- **Stack**: fullstack (Python backend + TypeScript frontend)
- **Framework**: pytest + asyncio (backend), Playwright (frontend E2E)
- **Mode**: BMad-Integrated (story spec with acceptance criteria)

## Coverage Gap Analysis

### Existing Tests: 75 tests across 11 files

### Gaps Identified

| Priority | Count | Key Gaps |
|----------|-------|----------|
| P0 | 8 | Factory lifecycle, provider resolution, no-providers, lifespan, webhook reset |
| P1 | 13 | Auth errors, voice event exceptions, mid-range latency, voice model override |
| P2 | 6 | Idempotent reset, content-type defaults, empty audio, p95 single entry |

## New Tests Added: 35 tests across 5 files

### test_tts_factory.py (7 tests)
- [2.3-UNIT-012_P0] Factory creates orchestrator with correct providers based on API keys
- [2.3-UNIT-012_P0] Singleton caching verified (second call returns same instance)
- [2.3-UNIT-012_P0] Only ElevenLabs when Cartesia key missing
- [2.3-UNIT-012_P0] Only Cartesia when ElevenLabs key missing
- [2.3-UNIT-012_P0] Empty orchestrator when no keys configured
- [2.3-UNIT-012_P0] Shutdown lifecycle: stops task, closes providers, resets global
- [2.3-UNIT-012_P0] Shutdown when None is no-op

### test_tts_orchestrator_edges.py (13 tests)
- [2.3-UNIT-013_P0] Primary override not in providers falls back to settings
- [2.3-UNIT-013_P0] No providers raises TTSAllProvidersFailedError
- [2.3-UNIT-013_P0] Primary None swaps with fallback
- [2.3-UNIT-013_P1] Voice model override propagated to synthesize
- [2.3-UNIT-013_P1] Mid-range latency resets recovery healthy count
- [2.3-UNIT-013_P0] Primary error with no fallback provider
- [2.3-UNIT-013_P1] Voice event exception doesn't crash orchestrator
- [2.3-UNIT-013_P2] Latency history returns empty for unknown session
- [2.3-UNIT-013_P2] Reset session idempotent for nonexistent key
- [2.3-UNIT-013_P2] Fallback/recovery condition returns false for missing state
- [2.3-UNIT-013_P1] _get_or_create_session falls back to first available
- [2.3-UNIT-013_P2] stop_cleanup_task when None is no-op

### test_tts_provider_edges.py (9 tests)
- [2.3-UNIT-014_P1] Cartesia auth error 401
- [2.3-UNIT-014_P1] Cartesia auth error 403
- [2.3-UNIT-014_P1] ElevenLabs health_check with no API key
- [2.3-UNIT-014_P2] Content-type default when header missing (ElevenLabs)
- [2.3-UNIT-014_P2] Content-type default when header missing (Cartesia)
- [2.3-UNIT-014_P1] Provider aclose lifecycle (ElevenLabs)
- [2.3-UNIT-014_P1] Provider aclose lifecycle (Cartesia)
- [2.3-UNIT-014_P2] Empty audio response treated as success (ElevenLabs)
- [2.3-UNIT-014_P2] Empty audio response treated as success (Cartesia)

### test_tts_api_edges.py (2 tests)
- [2.3-UNIT-015_P1] P95 calculation with single latency entry
- [2.3-UNIT-015_P1] P95 calculation with 10 latency entries

### test_tts_record_edges.py (4 tests)
- [2.3-UNIT-016_P1] _record_all_failed per-provider insert exception handled
- [2.3-UNIT-016_P1] _record_all_failed flush exception handled
- [2.3-UNIT-016_P1] _perform_switch continues to emit voice event after switch insert failure
- [2.3-UNIT-016_P2] TTSAllProvidersFailedError message includes both provider errors

## Results

```
110 passed, 0 failures, 2 warnings in 3.87s
```

## Remaining Gaps (deferred — lower priority or require running infrastructure)

| Gap | Reason |
|-----|--------|
| Lifespan integration (main.py startup/shutdown) | Requires running FastAPI app with DB |
| Webhook call-end → reset_session | Requires webhook handler integration test |
| Settings validation (negative thresholds) | Pydantic validation, low risk |
| Router auth edge cases (missing org_id) | Requires auth middleware setup |
