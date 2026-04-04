# Edge Case Hunter Review - Story 2.4

## Instructions
You are a pure path tracer. List ONLY missing handling for unhandled edge cases. Do NOT comment on whether code is good or bad.

## Diff Content

```
GIT DIFF OUTPUT:

(See commit 4763ac7: feat(story-2.4): implement asynchronous telemetry sidecars for voice events)

Key files changed:
- apps/api/services/telemetry/queue.py - TelemetryQueue with asyncio.wait_for
- apps/api/services/telemetry/worker.py - Batch processor with graceful degradation
- apps/api/services/telemetry/hooks.py - Event hooks
- apps/api/routers/telemetry.py - API endpoints
- apps/api/tests/test_telemetry_*.py - Test suite
```

## Your Task
Walk every branching path and boundary condition. Report ONLY unhandled paths as JSON:

```json
[{
  "location": "file:start-end or file:line",
  "trigger_condition": "one-line description (max 15 words)",
  "guard_snippet": "minimal code sketch that closes the gap",
  "potential_consequence": "what could go wrong (max 15 words)"
}]
```

Discard handled paths silently. No editorializing.

## Key Areas to Trace
- Queue full scenarios
- Timeout handling (asyncio.wait_for)
- Race conditions in concurrent pushes
- Batch processing errors
- Tenant context isolation
- Memory management (queue depth gauge)

---
**IMPORTANT**: This review must be run in a FRESH SESSION with no conversation history.
Run this prompt, then paste the findings back into the main review session.
