# Blind Hunter Review - Story 2.4

## Instructions
You are a cynical, jaded reviewer with zero patience for sloppy work. Review this diff and find at least 10 issues. Be skeptical of everything.

## Diff Content

```
GIT DIFF OUTPUT:

(See commit 4763ac7: feat(story-2.4): implement asynchronous telemetry sidecars for voice events)

Full diff saved at: /tmp/story-2.4-diff.txt

Key files changed:
- apps/api/main.py - Telemetry lifecycle integration
- apps/api/config/settings.py - Queue settings
- apps/api/models/voice_telemetry.py - SQLModel (NEW)
- apps/api/services/telemetry/queue.py - TelemetryQueue (NEW)
- apps/api/services/telemetry/worker.py - TelemetryWorker (NEW)
- apps/api/services/telemetry/hooks.py - VoiceEventHooks (NEW)
- apps/api/routers/telemetry.py - API endpoints (NEW)
- apps/api/tests/test_telemetry_*.py - 6 test files (NEW)
- packages/types/telemetry.ts - TypeScript types (NEW)
```

## Your Task
Review with extreme skepticism. Find problems in:
- Code quality and design
- Missing error handling
- Security issues
- Performance problems
- Testing gaps

## Output Format
Return findings as a markdown list with one-line descriptions.

---
**IMPORTANT**: This review must be run in a FRESH SESSION with no conversation history.
Run this prompt, then paste the findings back into the main review session.
