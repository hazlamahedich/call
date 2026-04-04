# Architecture Decision Record: TTS Orchestrator Integration for Story 2.6

**Date**: 2026-04-04
**Status**: Proposed
**Author**: System Architect (Winston)
**Decision**: AudioTestService MUST use TTSOrchestrator, not direct provider SDKs

---

## Context

Story 2.6 (Pre-Flight Calibration Dashboard) requires generating test audio clips for user voice configuration. The original story design proposed creating `AudioTestService` with direct ElevenLabs and Cartesia SDK integrations.

**Adversarial Review Finding (Winston)**:
> "Tight Coupling to TTS Providers: The AudioTestService directly integrates ElevenLabs and Cartesia SDKs. What happens when we add a third provider? This violates the Open-Closed Principle."

Story 2.3 already implemented a robust TTS abstraction layer with:
- `TTSProviderBase` abstract base class
- `TTSOrchestrator` for provider management
- Circuit breaker pattern for automatic failover
- Session state management
- Provider health monitoring

## Decision

**AudioTestService will integrate with TTSOrchestrator instead of calling provider SDKs directly.**

### Architecture Pattern

```python
# ❌ WRONG: Direct provider coupling (original design)
class AudioTestService:
    async def generate_test_audio(self, text: str, voice_config: AgentConfig):
        if voice_config.provider == "elevenlabs":
            client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
            return await client.generate(...)
        elif voice_config.provider == "cartesia":
            client = Cartesia(api_key=settings.CARTESIA_API_KEY)
            return await client.generate(...)
        # Violates Open-Closed Principle: must modify this for each new provider

# ✅ CORRECT: Use TTSOrchestrator (approved design)
class AudioTestService:
    def __init__(self):
        self.orchestrator = get_tts_orchestrator()

    async def generate_test_audio(self, text: str, voice_config: AgentConfig) -> bytes:
        # Use orchestrator which handles provider abstraction, circuit breaker, etc.
        response = await self.orchestrator.synthesize_for_test(
            text=text,
            voice_id=voice_config.voice_id,
            provider=voice_config.provider,
            speech_speed=voice_config.speech_speed,
            stability=voice_config.stability,
        )
        return response.audio_bytes
```

### Required: Add `synthesize_for_test()` Method

The existing `synthesize_for_call()` method requires:
- `session: AsyncSession` (database session)
- `call_id: int` (database call record)
- `vapi_call_id: str` (Vapi call identifier)

For audio tests, we don't have a real call yet. We need a new method:

```python
# Add to TTSOrchestrator in apps/api/services/tts/orchestrator.py

async def synthesize_for_test(
    self,
    text: str,
    voice_id: str,
    provider: str | None = None,
    speech_speed: float = 1.0,
    stability: float = 0.8,
    temperature: float = 0.7,
) -> TTSResponse:
    """Generate test audio without requiring a call session.

    This method is used by Story 2.6's Pre-Flight Calibration Dashboard
    to generate test audio clips for user voice configuration.

    Key differences from synthesize_for_call():
    - No database session required
    - No call_id or vapi_call_id required
    - Does not record to tts_requests table
    - Does not emit voice_events
    - Still participates in circuit breaker state
    - Still respects provider health checks

    Args:
        text: The text to synthesize (typically 10-second test script)
        voice_id: Voice identifier for the provider
        provider: Provider name (elevenlabs, cartesia). If None, uses primary.
        speech_speed: Speech speed multiplier (0.5 - 2.0)
        stability: Stability setting (0.0 - 1.0)
        temperature: Temperature setting for expressiveness (0.0 - 1.0)

    Returns:
        TTSResponse with audio_bytes, latency_ms, provider, content_type

    Raises:
        TTSAllProvidersFailedError: If all providers are unavailable
    """
    # Select provider (respecting circuit breaker)
    if provider and provider not in self._providers:
        provider = None

    if provider is None:
        provider = self._settings.TTS_PRIMARY_PROVIDER
        # Check circuit breaker
        if self._circuit_breaker.is_open(provider):
            # Try fallback provider
            for alt in self._providers:
                if alt != provider and not self._circuit_breaker.is_open(alt):
                    provider = alt
                    break

    tts_provider = self._providers.get(provider)
    if tts_provider is None:
        raise TTSAllProvidersFailedError(
            f"Requested provider '{provider}' not available and no fallback configured"
        )

    # Synthesize (provider handles speech_speed, stability, temperature mapping)
    response = await tts_provider.synthesize(text, voice_id)

    # Update circuit breaker on failure/slow response
    if response.error or response.latency_ms > self._settings.TTS_LATENCY_THRESHOLD_MS:
        if not response.error:
            self._circuit_breaker.record_fallback(provider)
    else:
        self._circuit_breaker.record_success(provider)

    return response
```

### Benefits

1. **Open/Closed Principle**: Adding new providers requires zero changes to AudioTestService
2. **Circuit Breaker Integration**: Audio tests respect circuit state (approved AC9)
3. **Code Reuse**: Leverages existing provider abstractions and error handling
4. **Consistent Monitoring**: Test audio generation uses same logging and telemetry patterns
5. **Single Source of Truth**: TTS configuration lives in one place (TTSOrchestrator)

### Implementation Impact

**Changes Required**:
1. Add `synthesize_for_test()` method to `TTSOrchestrator` (~50 lines)
2. Create lightweight `AudioTestService` wrapper (~20 lines)
3. Update Story 2.6 Phase 2 tasks to remove direct provider SDK implementation

**No Changes Required**:
- Provider implementations (ElevenLabsProvider, CartesiaProvider)
- Circuit breaker logic
- Health monitoring
- Session cleanup

### Updated Story 2.6 Tasks

**Phase 2: Backend — TTS Integration for Audio Tests (REVISED)**

- [ ] Add `synthesize_for_test()` method to `TTSOrchestrator` (ACs 1, 7, 8)
  - [ ] Method signature: `async synthesize_for_test(text, voice_id, provider, speech_speed, stability, temperature)`
  - [ ] Provider selection with circuit breaker respect
  - [ ] Call `provider.synthesize()` with parameters
  - [ ] Update circuit breaker state based on response
  - [ ] Return `TTSResponse` with audio_bytes
  - [ ] Raise `TTSAllProvidersFailedError` on provider failure

- [ ] Create lightweight `AudioTestService` in `apps/api/services/audio_test.py` (ACs 1, 7, 8)
  - [ ] `__init__()`: Get TTSOrchestrator via factory
  - [ ] `async generate_test_audio(text: str, voice_config: AgentConfig) -> bytes`
  - [ ] Call `orchestrator.synthesize_for_test()` with config
  - [ ] Return audio bytes from TTSResponse
  - [ ] Raise `AudioTestError` on failure (wraps TTSAllProvidersFailedError)

- [ ] Add audio test settings to `apps/api/config/settings.py` (AC: 1)
  - [ ] `DEFAULT_TEST_TEXT` (e.g., "Hello, this is a test of the AI voice configuration...")
  - [ ] `AUDIO_TEST_TIMEOUT_MS` (default 10000)
  - [ ] Provider API keys already configured for TTSOrchestrator

- [ ] Add error handling and logging (AC: 8)
  - [ ] Create `AudioTestError` exception in `apps/api/exceptions.py`
  - [ ] Log structured errors with `extra={"code": "AUDIO_TEST_ERROR"}`
  - [ ] Include provider, voice_id, and error details in logs

### Updated Acceptance Criteria

**AC9: Circuit Breaker Integration (NEW)**
```
Given the TTS circuit breaker is tripped for a provider,
When the user triggers an audio test with that provider,
Then the test fails fast with a clear message:
      "Audio service temporarily unavailable. Please try again in a few minutes."
And the UI remains functional for other adjustments.
And the test uses the fallback provider if available.
```

## Alternatives Considered

### Alternative 1: Direct Provider SDK Calls (Original Design)
**Rejected** - Violates Open/Closed Principle, creates two separate TTS code paths

### Alternative 2: Create New Provider Abstraction Layer for Tests
**Rejected** - Duplicates existing TTSOrchestrator functionality, increases maintenance burden

### Alternative 3: Mock Call Session for Tests
**Rejected** - Creates fake database records, violates data integrity, confusing for monitoring

## Consequences

**Positive**:
- Eliminates code duplication
- Consistent behavior between production calls and test audio
- Automatic circuit breaker protection
- Easier to add new providers in future

**Negative**:
- Requires modifying TTSOrchestrator (minimal impact)
- Test audio doesn't record to tts_requests table (by design, tests are ephemeral)

**Risks**:
- Low: Adding new method to existing class is well-understood pattern
- Low: No changes to provider implementations

## Related Decisions

- Story 2.3 ADR: TTS Provider Abstraction and Fallback
- Story 2.3 ADR: Circuit Breaker Pattern for TTS Providers
- Architecture: Single Responsibility Principle for Service Classes

## References

- Story 2.3 Implementation: `_bmad-output/implementation-artifacts/2-3-low-latency-tts-provider-fallback-logic.md`
- TTSOrchestrator Code: `apps/api/services/tts/orchestrator.py`
- TTSProviderBase Code: `apps/api/services/tts/base.py`
- Adversarial Review: `2-6-adversarial-review-action-plan.md` Task 0b.1
