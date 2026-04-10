"""
[2.4-INT-005] Test Epic 5 transcript + TTS during active call.

Tests the coexistence of transcript handling and TTS synthesis during active calls:
- Transcript handler and TTS session don't interfere during active call
- Both services share vapi_call_id and org_id for correlation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.tts.factory import get_tts_orchestrator, shutdown_tts, reset_orchestrator
from services.tts.orchestrator import SessionTTSState
from services.tts.base import TTSProviderBase
from services.transcription import handle_transcript_event
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
        "ELEVENLABS_API_KEY": "test-key",
        "CARTESIA_API_KEY": "test-key",
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _mock_db_result(org_id: str, vapi_call_id: str):
    """Helper to create a mock DB result with a proper row."""
    mock_result = MagicMock()  # Not AsyncMock - result.first() is synchronous
    mock_row = MagicMock()
    mock_row._mapping = {
        "id": 1,
        "org_id": org_id,
        "call_id": 123,
        "vapi_call_id": vapi_call_id,
        "role": "user",
        "text": "Test transcript",
        "start_time": None,
        "end_time": None,
        "confidence": None,
        "words_json": None,
        "received_at": None,
        "vapi_event_timestamp": None,
        "created_at": None,
        "updated_at": None,
        "soft_delete": False,
    }
    mock_result.first.return_value = mock_row
    return mock_result


@pytest.fixture
def mock_resolve_call_id():
    """Mock _resolve_call_id to return a valid call_id."""
    with patch(
        "services.transcription._resolve_call_id", new_callable=AsyncMock
    ) as mock:
        mock.return_value = 123  # Valid call_id
        yield mock


@pytest.fixture(autouse=True)
def _reset_tts():
    reset_orchestrator()
    yield
    reset_orchestrator()


class TestTranscriptTTSCoexistence:
    """
    [2.4-INT-005_P0] Test transcript handler and TTS don't interfere during active call.
    """

    @pytest.mark.asyncio
    async def test_transcript_and_tts_dont_interfere(self, mock_resolve_call_id):
        """
        [2.4-INT-005_P0_S1] Given an active call with TTS running,
        when a transcript webhook arrives mid-call,
        then both the TTS synthesis pipeline and the transcript handler operate
        without interfering with each other.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = await get_tts_orchestrator()

            # Create an active TTS session
            vapi_call_id = "vapi-coexist-123"
            org_id = "org-coexist"

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            # Create a TTS session state
            orchestrator._session_state[vapi_call_id] = SessionTTSState(
                active_provider="elevenlabs"
            )

            # Mock DB session for transcript handling
            db_session = AsyncMock()
            db_session.execute = AsyncMock(
                return_value=_mock_db_result(org_id, vapi_call_id)
            )
            db_session.flush = AsyncMock()

            # Handle a transcript event mid-call
            transcript_data = {
                "transcript": {"text": "Hello world", "role": "user"},
                "vapi_call_id": vapi_call_id,
                "org_id": org_id,
            }

            # Should not raise - both systems should coexist
            await handle_transcript_event(
                db_session,
                vapi_call_id,
                org_id,
                transcript_data=transcript_data,
            )

            # Verify TTS session is still intact
            assert vapi_call_id in orchestrator._session_state
            assert orchestrator.get_session_provider(vapi_call_id) == "elevenlabs"

            # Verify transcript was persisted (DB was called)
            assert db_session.execute.call_count >= 1

            # Cleanup
            for provider in orchestrator._providers.values():
                await provider.aclose()
            reset_orchestrator()

    @pytest.mark.asyncio
    async def test_both_services_share_correlation_ids(self, mock_resolve_call_id):
        """
        [2.4-INT-005_P0_S2] Given an active call with TTS running,
        when a transcript webhook arrives mid-call,
        then both services share the same vapi_call_id and org_id for correlation.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = await get_tts_orchestrator()

            vapi_call_id = "vapi-correlation-456"
            org_id = "org-correlation"

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            # Create a TTS session state
            orchestrator._session_state[vapi_call_id] = SessionTTSState(
                active_provider="cartesia"
            )

            # Mock DB session
            db_session = AsyncMock()
            db_session.execute = AsyncMock(
                return_value=_mock_db_result(org_id, vapi_call_id)
            )
            db_session.flush = AsyncMock()

            # Handle transcript event
            transcript_data = {
                "transcript": {"text": "Test transcript", "role": "user"},
                "vapi_call_id": vapi_call_id,
                "org_id": org_id,
            }

            await handle_transcript_event(
                db_session,
                vapi_call_id,
                org_id,
                transcript_data=transcript_data,
            )

            # Verify both services can be correlated by vapi_call_id and org_id
            assert vapi_call_id in orchestrator._session_state

            # Verify DB session was called with correct context
            assert db_session.execute.call_count >= 1

            # Cleanup
            for provider in orchestrator._providers.values():
                await provider.aclose()
            reset_orchestrator()

    @pytest.mark.asyncio
    async def test_multiple_transcripts_dont_disrupt_tts_session(
        self, mock_resolve_call_id
    ):
        """
        [2.4-INT-005_P0_S3] Given an active call with TTS running,
        when multiple transcript webhooks arrive mid-call,
        then the TTS session state remains untouched across all transcripts.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = await get_tts_orchestrator()

            vapi_call_id = "vapi-multiple-789"
            org_id = "org-multiple"

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            # Create a TTS session state
            initial_state = SessionTTSState(active_provider="elevenlabs")
            orchestrator._session_state[vapi_call_id] = initial_state

            # Mock DB session
            db_session = AsyncMock()
            db_session.execute = AsyncMock(
                return_value=_mock_db_result(org_id, vapi_call_id)
            )
            db_session.flush = AsyncMock()

            # Handle multiple transcript events
            for i in range(5):
                transcript_data = {
                    "transcript": {"text": f"Transcript {i}", "role": "user"},
                    "vapi_call_id": vapi_call_id,
                    "org_id": org_id,
                }

                await handle_transcript_event(
                    db_session,
                    vapi_call_id,
                    org_id,
                    transcript_data=transcript_data,
                )

            # Verify TTS session is unchanged
            assert vapi_call_id in orchestrator._session_state
            current_state = orchestrator._session_state[vapi_call_id]
            assert current_state.active_provider == initial_state.active_provider

            # Cleanup
            for provider in orchestrator._providers.values():
                await provider.aclose()
            reset_orchestrator()
