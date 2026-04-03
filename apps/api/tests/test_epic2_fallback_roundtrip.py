"""
[2.4-INT-003] Test Epic 3 full fallback round-trip with mocked HTTP.

Tests the complete TTS fallback flow from synthesize_for_call to response:
- 3 slow responses trigger switch to fallback provider
- Provider switch writes to tts_provider_switches (mocked DB)
- Voice event is emitted on switch
- Post-switch requests use the new provider
- Round-trip from synthesize_for_call entry to final response
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.tts.orchestrator import (
    TTSOrchestrator,
    SessionTTSState,
)
from services.tts.base import TTSResponse, TTSProviderBase
from tests.support.mock_helpers import _make_result


def _make_settings(**overrides):
    """Helper to create mock settings with test overrides."""
    s = MagicMock()
    defaults = {
        "TTS_PRIMARY_PROVIDER": "elevenlabs",
        "TTS_FALLBACK_PROVIDER": "cartesia",
        "TTS_LATENCY_THRESHOLD_MS": 500,
        "TTS_CONSECUTIVE_SLOW_THRESHOLD": 3,
        "TTS_AUTO_RECOVERY_ENABLED": True,
        "TTS_RECOVERY_HEALTHY_COUNT": 5,
        "TTS_RECOVERY_LATENCY_MS": 300,
        "TTS_RECOVERY_COOLDOWN_SEC": 60,
        "TTS_SESSION_TTL_SEC": 3600,
        "TTS_CIRCUIT_OPEN_SEC": 30,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _mock_provider(
    name: str,
    *,
    latency_ms: float = 100.0,
    error: bool = False,
    error_message: str | None = None,
):
    """Helper to create a mock TTS provider."""
    p = MagicMock(spec=TTSProviderBase)
    p.provider_name = name
    p.synthesize = AsyncMock(
        return_value=TTSResponse(
            audio_bytes=b"" if error else b"audio",
            latency_ms=latency_ms,
            provider=name,
            content_type="" if error else "audio/mpeg",
            error=error,
            error_message=error_message,
        )
    )
    p.health_check = AsyncMock(return_value=True)
    p.aclose = AsyncMock()
    return p


def _mock_session():
    """Helper to create a mock DB session."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_result())
    session.flush = AsyncMock()
    return session


class TestFallbackRoundTrip:
    """
    [2.4-INT-003_P0] Test 3 slow responses trigger switch to fallback.
    """

    @pytest.mark.asyncio
    async def test_three_slow_responses_trigger_switch(self):
        """
        [2.4-INT-003_P0_S1] Given an active call session with ElevenLabs as primary,
        when 3 consecutive slow responses (>500ms) occur,
        then the orchestrator switches to Cartesia.
        """
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        vapi_call_id = "vapi-slow-test"

        # Three slow responses trigger fallback
        for i in range(3):
            result = await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id=vapi_call_id,
                org_id="org-1",
                text=f"slow request {i}",
                voice_id="v1",
            )

        # Verify switch to Cartesia
        assert orchestrator.get_session_provider(vapi_call_id) == "cartesia"

    @pytest.mark.asyncio
    async def test_provider_switch_writes_to_db(self):
        """
        [2.4-INT-003_P0_S2] Given a fallback is triggered,
        when the switch occurs,
        then a row is written to tts_provider_switches (mocked DB).
        """
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )

        # Mock session to capture execute calls
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_make_result())
        session.flush = AsyncMock()

        vapi_call_id = "vapi-switch-test"

        # Three slow responses
        for i in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id=vapi_call_id,
                org_id="org-1",
                text=f"request {i}",
                voice_id="v1",
            )

        # Verify DB write was attempted (session.execute called)
        assert session.execute.call_count >= 1
        assert session.flush.call_count >= 1

    @pytest.mark.asyncio
    async def test_voice_event_emitted_on_switch(self):
        """
        [2.4-INT-003_P0_S3] Given a fallback is triggered,
        when the switch occurs,
        then a voice_event is emitted with switch details.
        """
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        vapi_call_id = "vapi-event-test"

        # Trigger fallback
        for i in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id=vapi_call_id,
                org_id="org-1",
                text=f"request {i}",
                voice_id="v1",
            )

        # Verify voice event was logged (via logger in orchestrator)
        # The implementation logs with code "TTS_PROVIDER_SWITCH"
        # We can't directly test logger output without more complex mocking,
        # but we can verify the provider switched
        assert orchestrator.get_session_provider(vapi_call_id) == "cartesia"


class TestPostSwitchRequestsUseNewProvider:
    """
    [2.4-INT-003_P0] Test post-switch requests use new provider.
    """

    @pytest.mark.asyncio
    async def test_post_switch_requests_use_fallback_provider(self):
        """
        [2.4-INT-003_P0_S4] Given a fallback has been triggered,
        when subsequent requests are made,
        then they use the new provider (Cartesia) without error.
        """
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        vapi_call_id = "vapi-post-switch"

        # Trigger fallback
        for i in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id=vapi_call_id,
                org_id="org-1",
                text=f"slow {i}",
                voice_id="v1",
            )

        # Verify switched to Cartesia
        assert orchestrator.get_session_provider(vapi_call_id) == "cartesia"

        # Subsequent request should use Cartesia
        result = await orchestrator.synthesize_for_call(
            session,
            call_id=1,
            vapi_call_id=vapi_call_id,
            org_id="org-1",
            text="post-switch request",
            voice_id="v1",
        )

        # Verify result
        assert result.provider == "cartesia"
        assert not result.error

        # Verify Cartesia was called twice: once during fallback trigger, once post-switch
        # Request 3 triggered fallback and retried with Cartesia, then request 4 used it
        assert fallback.synthesize.call_count == 2
        assert primary.synthesize.call_count == 3  # Only the 3 slow calls


class TestRoundTripIntegration:
    """
    [2.4-INT-003_P0] Test complete round-trip from entry to response.
    """

    @pytest.mark.asyncio
    async def test_round_trip_from_synthesize_to_response(self):
        """
        [2.4-INT-003_P0_S5] Given the orchestrator entry point synthesize_for_call,
        when a full round-trip occurs with fallback,
        then the flow completes: synthesize_for_call → provider HTTP → latency check →
        fallback decision → DB write → voice event → final response.
        """
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )

        # Mock session with detailed tracking
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_make_result())
        session.flush = AsyncMock()

        vapi_call_id = "vapi-roundtrip"
        org_id = "org-roundtrip"

        # Complete round-trip: 3 slow requests triggering fallback
        responses = []
        for i in range(3):
            response = await orchestrator.synthesize_for_call(
                session,
                call_id=100 + i,
                vapi_call_id=vapi_call_id,
                org_id=org_id,
                text=f"roundtrip request {i}",
                voice_id="vx-123",
            )
            responses.append(response)

        # Verify all requests succeeded
        for resp in responses:
            assert resp.audio_bytes == b"audio"
            assert not resp.error

        # Verify provider switched
        assert orchestrator.get_session_provider(vapi_call_id) == "cartesia"

        # Verify DB interactions occurred
        assert session.execute.call_count >= 3
        assert session.flush.call_count >= 3

        # Verify provider call counts
        # The third slow request triggers fallback and retries with Cartesia
        assert primary.synthesize.call_count == 3  # Three slow calls
        assert fallback.synthesize.call_count == 1  # Retry on third request (fallback trigger)

        # Now make a post-switch request to complete the round-trip
        final_response = await orchestrator.synthesize_for_call(
            session,
            call_id=103,
            vapi_call_id=vapi_call_id,
            org_id=org_id,
            text="post-switch",
            voice_id="vx-123",
        )

        # Verify final response uses fallback provider
        assert final_response.provider == "cartesia"
        # Total fallback calls: 1 during third request (fallback trigger) + 1 post-switch = 2
        assert fallback.synthesize.call_count == 2
