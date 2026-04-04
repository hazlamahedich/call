# Story 2.6: Adversarial Review Action Plan

**Generated**: 2026-04-04
**Status**: 14 concerns identified | 0 resolved | 14 pending
**Goal**: Address all concerns to move from `needs-refinement` → `ready-for-dev`

---

## 🚨 CRITICAL PATH: Must Complete Before ANY Development

These are **blocking issues** - development should NOT start until these are resolved.

### Phase 0a: Product Validation (John's Concerns) - 3-5 days

**Owner**: Product Manager (John) + User Researcher
**Estimated Time**: 3-5 days
**Blocking**: 🔴 YES - Cannot validate technical approach without confirming user need

#### Task 0a.1: User Interviews (P0 - CRITICAL)
- [ ] Interview 5-10 Agent Managers who have completed onboarding
- [ ] Ask: "How often do you adjust voice settings after the first call?"
- [ ] Ask: "Have you ever made a call where the voice sounded wrong?"
- [ ] Ask: "Would a pre-call calibration step be valuable or annoying?"
- [ ] Document findings in `_bmad-output/research/voice-calibration-user-interviews.md`

**Decision Gate**:
- ✅ **PROCEED** if >30% express strong need for calibration
- ❌ **DEFER/RESCOPE** if <30% express need → consider different approach

**Deliverable**:
- User interview summary with quotes
- Quantified need (e.g., "7/10 users reported voice issues on first call")
- Go/no-go recommendation

#### Task 0a.2: Competitive Analysis (P0 - CRITICAL)
- [ ] Research Vapi, Retell, Vocode for pre-flight calibration features
- [ ] Document: Do they have it? How do they handle it?
- [ ] If competitors DON'T have it, understand why (maybe users don't need it)
- [ ] Document findings in `_bmad-output/research/voice-calibration-competitive-analysis.md`

**Decision Gate**:
- If competitors have similar feature → validate their approach
- If competitors don't have it → understand why (user research critical here)

**Deliverable**:
- Competitive matrix (features, screenshots, analysis)
- Key learnings from each competitor
- Recommended approach based on market

#### Task 0a.3: Success Metrics Definition (P0 - CRITICAL)
- [ ] Define baseline metrics from current data:
  - [ ] Current call redo rate (due to voice issues)
  - [ ] Current time to first successful call
  - [ ] Current user confidence scores (if available)
- [ ] Define success criteria:
  - [ ] Target: 20% reduction in call redos?
  - [ ] Target: 15% increase in user confidence?
  - [ ] Maximum acceptable drop-off rate during calibration?
- [ ] Define telemetry events to track:
  - [ ] `calibration_started`
  - [ ] `calibration_completed`
  - [ ] `calibration_skipped`
  - [ ] `first_call_quality`
  - [ ] `call_redo` (segment by calibrated vs non-calibrated)

**Deliverable**:
- Metrics baseline document
- Success criteria targets
- Telemetry event specification

---

### Phase 0b: Architecture Refinement (Winston's Concerns) - 2-3 days

**Owner**: System Architect (Winston) + Backend Developer
**Estimated Time**: 2-3 days
**Blocking**: 🔴 YES - Cannot implement without validated architecture

#### Task 0b.1: Provider Abstraction Layer (P0 - CRITICAL)
- [ ] Review Story 2.3's `TTSOrchestrator` in `apps/api/services/tts/orchestrator.py`
- [ ] Review `TTSProvider` base class in `apps/api/services/tts/base.py`
- [ ] Design AudioTestService to use existing orchestrator:
  ```python
  # Instead of:
  audio_test_service = AudioTestService()
  audio = await audio_test_service.generate_test_audio(...)

  # Use:
  orchestrator = get_tts_orchestrator()
  audio = await orchestrator.synthesize_for_call(...)
  ```
- [ ] Update story Phase 2 tasks to reflect this architecture
- [ ] Document how to add third provider without modifying AudioTestService

**Deliverable**:
- Architecture decision record (ADR)
- Updated Phase 2 tasks in story
- Diagram showing AudioTestService → TTSOrchestrator → Provider flow

#### Task 0b.2: State Management Strategy (P1 - HIGH)
- [ ] Define interim state storage approach:
  - [ ] Option A: `localStorage` with 1-hour TTL (recommended)
  - [ ] Option B: React Query with optimistic updates
  - [ ] Option C: In-memory state (fragile, not recommended)
- [ ] Document state lifecycle:
  - [ ] User adjusts slider → update localStorage
  - [ ] User navigates away → localStorage persists
  - [ ] User returns → restore from localStorage
  - [ ] User clicks Save → persist to DB, clear localStorage
- [ ] Add this strategy to Dev Notes section
- [ ] Update AC5 to explicitly state interim behavior

**Deliverable**:
- State management specification
- Updated AC5 language
- Code snippets for localStorage integration

#### Task 0b.3: Circuit Breaker Integration (P0 - CRITICAL)
- [ ] Verify AudioTestService uses TTSOrchestrator (from Task 0b.1)
- [ ] Add acceptance criterion:
  ```
  AC9: Given the TTS circuit breaker is tripped for a provider,
        When the user triggers an audio test,
        Then the test fails fast with a clear message:
        "Audio service temporarily unavailable. Please try again in a few minutes."
        And the UI remains functional for other adjustments.
  ```
- [ ] Add test: Verify circuit state affects audio tests
- [ ] Document: Audio tests participate in circuit breaker state

**Deliverable**:
- New AC9 added to story
- Test scenario for circuit breaker integration
- Documentation of circuit behavior

#### Task 0b.4: Performance Realism (P1 - HIGH)
- [ ] Update AC1 to reflect realistic latency:
  ```
  OLD: "the audio test plays immediately via the browser's Web Audio API"
  NEW: "the audio test plays within 3 seconds via the browser's Web Audio API"
  ```
- [ ] Add acceptance criterion for caching:
  ```
  AC10: Given the user triggers a second audio test with identical settings,
         When the test parameters match the previous test,
         Then the cached audio is played immediately (<500ms),
         And a "Cached" indicator appears in the UI.
  ```
- [ ] Design caching strategy:
  - [ ] Cache key: `(org_id, agent_id, voice_id, speech_speed, stability)`
  - [ ] Cache TTL: 1 hour
  - [ ] Cache storage: Redis or in-memory

**Deliverable**:
- Updated AC1 and AC10
- Caching strategy specification
- Updated Dev Notes

---

### Phase 0c: Testing Strategy Enhancement (Murat's Concerns) - 2-3 days

**Owner**: Test Architect (Murat) + QA Engineer
**Estimated Time**: 2-3 days
**Blocking**: 🟡 PARTIAL - Can start some tasks in parallel, but contract tests need architecture

#### Task 0c.1: Factory Functions (P0 - CRITICAL)
- [ ] Create `tests/factories/agent-config-factory.ts`:
  ```typescript
  export function createAgentId(): string {
    return `agent_${randomUUID()}`;
  }

  export function createVoiceId(): string {
    const voices = ['elevenlabs_abc', 'cartesia_xyz', 'openai_def'];
    return voices[Math.floor(Math.random() * voices.length)];
  }

  export function createAgentConfig(overrides?: Partial<AgentConfig>): AgentConfig {
    return {
      agentId: createAgentId(),
      voiceId: createVoiceId(),
      speechSpeed: 1.0,
      stability: 0.8,
      ...overrides,
    };
  }
  ```
- [ ] Update all E2E tests to use factories (replaces static IDs)
- [ ] Add to story Phase 6 tasks

**Deliverable**:
- Factory functions file
- Updated E2E tests
- Lesson learned documented (avoid Story 2.4's mistake)

#### Task 0c.2: Contract Testing Design (P0 - CRITICAL)
- [ ] Design contract test approach:
  - [ ] Option A: Pact (consumer-driven contracts)
  - [ ] Option B: One real provider test per CI run
  - [ ] Option C: Provider contract validation suite
- [ ] Add **Phase 5b: Contract Testing** to story:
  - [ ] Test: ElevenLabs real API contract validation
  - [ ] Test: Cartesia real API contract validation
  - [ ] Schedule: Run one real provider test per day (not every CI run)
- [ ] Document: Why mocking alone is insufficient

**Deliverable**:
- Contract testing strategy document
- New Phase 5b added to story
- Test schedule for CI/CD

#### Task 0c.3: Chaos Test Scenarios (P0 - CRITICAL)
- [ ] Add chaos tests to story Phase 5:
  - [ ] Test: ElevenLabs API returns 500 mid-generation
  - [ ] Test: Cartesia rate-limits during audio test
  - [ ] Test: Network timeout at 2.9 seconds
  - [ ] Test: User clicks Save while audio is generating
  - [ ] Test: User navigates away while audio is generating
- [ ] Use chaos engineering tools:
  - [ ] ToxiProxy for network failures
  - [ ] pytest-timeout for timeout tests
  - [ ] pytest-asyncio for concurrent operations

**Deliverable**:
- 5+ chaos test scenarios added to story
- Test implementation examples
- Chaos testing tool setup guide

#### Task 0c.4: Security Test Expansion (P0 - CRITICAL)
- [ ] Expand tenant isolation test (Story Phase 5):
  - [ ] Test: org1 creates 10,000 configs → verify rate limited
  - [ ] Test: 1GB `custom_voice_settings` dict → verify validation error
  - [ ] Test: SQL injection via `voice_id` → verify sanitized
  - [ ] Test: Agent ID tampering for privilege escalation → verify 403
- [ ] Add **P0 Security Tests** section to story
- [ ] Document threat model for AgentConfig endpoints

**Deliverable**:
- 4+ security test scenarios added to story
- Threat model document
- P0 security test section

#### Task 0c.5: Risk-Based Coverage Targets (P1 - HIGH)
- [ ] Replace ">80% coverage" with risk-based targets:
  - [ ] Critical paths (config CRUD, audio generation): 95%
  - [ ] Happy path sliders: 70%
  - [ ] Error handling: 90%
  - [ ] Tenant isolation: 100%
- [ ] Document rationale for each target
- [ ] Update story Phase 5 testing requirements

**Deliverable**:
- Risk-based coverage targets
- Coverage rationale document
- Updated Phase 5 requirements

---

## 📋 Story Updates Required

Once Phase 0 tasks are complete, update the story document:

### Story Content Updates

- [ ] Update **Acceptance Criteria**:
  - [ ] AC1: Change "immediately" to "within 3 seconds"
  - [ ] AC5: Add explicit interim state behavior
  - [ ] AC9: Add circuit breaker integration (new)
  - [ ] AC10: Add caching behavior (new)

- [ ] Update **Tasks / Subtasks**:
  - [ ] Phase 2: Rewrite to use TTSOrchestrator instead of direct SDK calls
  - [ ] Phase 5: Add contract testing, chaos tests, expanded security tests
  - [ ] Phase 6: Add factory functions to E2E tests

- [ ] Update **Dev Notes**:
  - [ ] Remove AudioTestService direct SDK implementation references
  - [ ] Add TTSOrchestrator integration pattern
  - [ ] Add state management strategy details
  - [ ] Add caching strategy details

- [ ] Update **Status**:
  - [ ] Change from `needs-refinement` to `ready-for-dev`
  - [ ] Update sprint-status.yaml accordingly

---

## 🎯 Phase 0 Completion Checklist

Before marking the story as `ready-for-dev`, verify:

### Product Validation ✅
- [ ] User interviews completed with documented findings
- [ ] Competitive analysis completed
- [ ] Success metrics defined and baselined
- [ ] Go/no-go decision made (should we build this?)

### Architecture Validation ✅
- [ ] Provider abstraction layer designed (uses TTSOrchestrator)
- [ ] State management strategy defined (localStorage documented)
- [ ] Circuit breaker integration specified (AC9 added)
- [ ] Performance expectations set (AC1 updated, AC10 added)

### Testing Validation ✅
- [ ] Factory functions created
- [ ] Contract testing strategy designed
- [ ] Chaos test scenarios specified
- [ ] Security test scenarios expanded
- [ ] Risk-based coverage targets defined

### Documentation Validation ✅
- [ ] Story document updated with all Phase 0 findings
- [ ] Adversarial review findings section updated (mark resolved items)
- [ ] Sprint status updated to `ready-for-dev`
- [ ] Research artifacts published:
  - [ ] User interview summary
  - [ ] Competitive analysis
  - [ ] Metrics baseline

---

## 📊 Timeline Estimate

| Phase | Duration | Dependencies | Owner |
|-------|----------|--------------|-------|
| **0a: Product Validation** | 3-5 days | None | PM + Researcher |
| **0b: Architecture Refinement** | 2-3 days | None (can parallel with 0a) | Architect + Backend |
| **0c: Testing Enhancement** | 2-3 days | None (can parallel with 0a, 0b) | Test Architect + QA |
| **Story Updates** | 1 day | 0a, 0b, 0c complete | Tech Writer |
| **Total** | **8-12 days** | Phases can run in parallel | Cross-functional |

**Critical Path**: 8-12 days (assuming parallel execution of phases 0a, 0b, 0c)

---

## 🚦 Decision Gates

### Gate 1: After User Interviews (Day 3-5)
**Question**: Do users actually need this feature?
- ✅ **YES** → Proceed to Phase 0b, 0c
- ❌ **NO** → Defer story, re-scope, or cancel

### Gate 2: After Architecture Review (Day 5-8)
**Question**: Can we build this without duplicating Story 2.3's code?
- ✅ **YES** → Proceed to story updates
- ❌ **NO** → Refine architecture (add 1-2 days)

### Gate 3: After Testing Strategy (Day 8-11)
**Question**: Is our testing approach comprehensive enough?
- ✅ **YES** → Proceed to story updates
- ❌ **NO** → Add missing test scenarios (add 1-2 days)

### Gate 4: Final Approval (Day 12)
**Question**: Are all 14 concerns addressed?
- ✅ **YES** → Mark story as `ready-for-dev`, begin implementation
- ❌ **NO** → Identify remaining gaps, address before proceeding

---

## 📝 Next Steps

1. **Immediate Actions** (This Week):
   - [ ] Schedule user interviews (aim for 5-10 participants)
   - [ ] Start competitive research (can begin immediately)
   - [ ] Architect: Review Story 2.3's TTSOrchestrator code

2. **Week 2 Actions**:
   - [ ] Complete user interviews and document findings
   - [ ] Complete architecture refinement
   - [ ] Design testing strategy enhancements

3. **Week 3 Actions**:
   - [ ] Make go/no-go decision based on research
   - [ ] Update story document with all findings
   - [ ] Transition story to `ready-for-dev` (if approved)

---

## 🔗 Related Artifacts

- Story Document: `_bmad-output/implementation-artifacts/2-6-pre-flight-calibration-dashboard.md`
- Sprint Status: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Research Artifacts (to be created):
  - `_bmad-output/research/voice-calibration-user-interviews.md`
  - `_bmad-output/research/voice-calibration-competitive-analysis.md`
  - `_bmad-output/research/voice-calibration-metrics-baseline.md`

---

**Last Updated**: 2026-04-04
**Status**: Awaiting Phase 0 initiation
**Next Review**: After user interviews complete (Day 3-5)
