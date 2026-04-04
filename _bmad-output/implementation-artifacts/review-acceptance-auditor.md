# Acceptance Auditor Review - Story 2.4

## Instructions
You are an Acceptance Auditor. Review the diff against the spec and check for violations of acceptance criteria.

## Diff Content

```
Commit: 4763ac7 feat(story-2.4): implement asynchronous telemetry sidecars for voice events

22 files changed, +2362 lines
```

## Specification

### Acceptance Criteria (from Story 2.4)

**AC1**: Event capture via telemetry_queue.push() must be non-blocking and complete in <2ms (measured from hook invocation to queue.put() completion) OR be dropped with a warning log if the queue is full.

**AC2**: Telemetry events are persisted to PostgreSQL within 100ms P95 of capture. Use bulk INSERT with batch size 100, collect up to 1s or 100 events (whichever first). Enforce tenant isolation via RLS policies.

**AC3**: Push operation MUST complete in <2ms P95 under load (10,000 events/sec). Verified via pytest-benchmark with 10,000 concurrent push operations.

**AC4**: VoiceTelemetry SQLModel with columns: call_id (int, FK), event_type (str, indexed), timestamp (datetime, indexed), duration_ms (float), audio_level (float), confidence_score (float), sentiment_score (float), provider (str), session_metadata (JSONB), queue_depth_at_capture (int), processing_latency_ms (float). Composite indexes on (org_id, timestamp) and (call_id, event_type).

**AC5**: VoiceEventHooks.on_silence_detected(), on_noise_detected(), on_interruption_detected(), on_talkover_detected() are called from VAD event detection in transcription service and Vapi webhooks. Hooks create VoiceEvent with timestamp = utc_now() and call telemetry_queue.push().

**AC5.5**: Integration tests verify hooks are actually called from transcription service and Vapi webhooks.

**AC6**: GET /api/v1/telemetry/metrics returns queue metrics: current_depth, avg_depth, max_depth, is_running, processing_latency_ms_p95, events_per_second. No auth required for monitoring.

**AC7**: GET /api/v1/telemetry/events supports filters (call_id, event_type, start_time, end_time, limit). Enforces RLS via org_id. Pagination via limit.

**AC8**: When queue is full (max_size 10000), push() returns False and logs "code": "TELEMETRY_QUEUE_FULL" warning. Events dropped rather than blocking voice pipeline.

**AC8.5**: If >10% events dropped for 30+ seconds, alert threshold triggered. Monitored via logs.

### Test Requirements
- [2.4-UNIT-QUEUE-XXX] Queue unit tests
- [2.4-UNIT-WORKER-XXX] Worker unit tests
- [2.4-UNIT-HOOKS-XXX] Hooks unit tests
- [2.4-INTEGRATION-XXX] API integration tests
- [2.4-SECURITY-TENANT-RACE-001] P0 tenant race condition test
- [2.4-MEMORY-CLEANUP-001] P1 memory leak prevention test
- [2.4-BENCHMARK-XXX] Performance benchmarks

### Architecture Warnings
- Fire-and-forget pattern accepts data loss for voice pipeline reliability
- Events dropped when queue full (no retry)
- In-memory queue lost on worker restart
- 1s batch deadline may delay persistence

## Your Task
Check for:
1. Violations of acceptance criteria
2. Deviations from spec intent
3. Missing implementation of specified behavior
4. Contradictions between spec constraints and actual code

## Output Format
Return findings as a markdown list:
- **[Finding Title]** - Violates AC# - Evidence from diff

---
**IMPORTANT**: This review must be run in a FRESH SESSION with no conversation history.
Run this prompt, then paste the findings back into the main review session.
