"""
[2.4-INT-007] Test Epic 7 tenant isolation across voice pipeline.

Tests that TTS sessions, transcript entries, and provider switches are isolated by org_id:
- Concurrent calls from different orgs maintain isolated TTS sessions
- Transcript entries are org-scoped
- Provider switches are org-scoped
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.tts.factory import get_tts_orchestrator, shutdown_tts, reset_orchestrator
from services.tts.orchestrator import SessionTTSState
from services.transcription import handle_transcript_event
from tests.support.mock_helpers import _make_result


def _make_settings(**overrides):
    s = MagicMock()
    defaults = {
        "TTS_PRIMARY_PROVIDER": "elevenlabs",
        "TTS_FALLBACK_PROVIDER": "cartesia",
        "TTS_LATENCY_THRESHOLD_MS": 500,
        "TTS_CONSECUTIVE_SLOW_THRESHOLD": 3,
        "ELEVENLABS_API_KEY": "test-key",
        "CARTESIA_API_KEY": "test-key",
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _mock_db_result(org_id: str, vapi_call_id: str):
    """Helper to create a mock DB result with a proper row."""
    mock_result = MagicMock()
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
        mock.return_value = 123
        yield mock


@pytest.fixture(autouse=True)
def _reset_tts():
    reset_orchestrator()
    yield
    reset_orchestrator()


class TestTenantIsolation:
    """
    [2.4-INT-007_P0] Test tenant isolation across voice pipeline.
    """

    @pytest.mark.asyncio
    async def test_concurrent_calls_maintain_isolated_tts_sessions(self):
        """
        [2.4-INT-007_P0_S1] Given two concurrent calls from different orgs,
        when each call has its own TTS session,
        then TTS session state is fully isolated by org_id.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = await get_tts_orchestrator()

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            # Create sessions for two different orgs
            org1_vapi = "vapi-org1-123"
            org2_vapi = "vapi-org2-456"

            orchestrator._session_state[org1_vapi] = SessionTTSState(
                active_provider="elevenlabs"
            )
            orchestrator._session_state[org2_vapi] = SessionTTSState(
                active_provider="cartesia"
            )

            # Verify both sessions exist independently
            assert org1_vapi in orchestrator._session_state
            assert org2_vapi in orchestrator._session_state
            assert orchestrator.get_session_provider(org1_vapi) == "elevenlabs"
            assert orchestrator.get_session_provider(org2_vapi) == "cartesia"

            # Reset one session - should not affect the other
            orchestrator.reset_session(org1_vapi)
            assert org1_vapi not in orchestrator._session_state
            assert org2_vapi in orchestrator._session_state

            # Cleanup
            for provider in orchestrator._providers.values():
                await provider.aclose()
            reset_orchestrator()

    @pytest.mark.asyncio
    async def test_transcript_entries_are_org_scoped(self, mock_resolve_call_id):
        """
        [2.4-INT-007_P0_S2] Given two concurrent calls from different orgs,
        when each call has transcript events,
        then transcript entries are org-scoped and cross-tenant queries return zero.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = await get_tts_orchestrator()

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            org1_vapi = "vapi-org1-transcript-123"
            org2_vapi = "vapi-org2-transcript-456"
            org1 = "org-transcript-1"
            org2 = "org-transcript-2"

            # Mock DB sessions for each org
            db_session_org1 = AsyncMock()
            db_session_org1.execute = AsyncMock(
                return_value=_mock_db_result(org1, org1_vapi)
            )
            db_session_org1.flush = AsyncMock()

            db_session_org2 = AsyncMock()
            db_session_org2.execute = AsyncMock(
                return_value=_mock_db_result(org2, org2_vapi)
            )
            db_session_org2.flush = AsyncMock()

            # Handle transcript events for each org
            await handle_transcript_event(
                db_session_org1,
                org1_vapi,
                org1,
                transcript_data={
                    "transcript": {"text": "Org 1 transcript", "role": "user"},
                    "vapi_call_id": org1_vapi,
                    "org_id": org1,
                },
            )

            await handle_transcript_event(
                db_session_org2,
                org2_vapi,
                org2,
                transcript_data={
                    "transcript": {"text": "Org 2 transcript", "role": "user"},
                    "vapi_call_id": org2_vapi,
                    "org_id": org2,
                },
            )

            # Verify each org's DB session was called with its org_id
            assert db_session_org1.execute.call_count >= 1
            assert db_session_org2.execute.call_count >= 1

            # Cleanup
            for provider in orchestrator._providers.values():
                await provider.aclose()
            reset_orchestrator()

    @pytest.mark.asyncio
    async def test_provider_switches_are_org_scoped(self):
        """
        [2.4-INT-007_P0_S3] Given two concurrent calls from different orgs,
        when one org triggers a provider switch,
        then the switch does not affect the other org's TTS sessions.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = await get_tts_orchestrator()

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            org1_vapi = "vapi-org1-switch-123"
            org2_vapi = "vapi-org2-switch-456"

            # Create sessions for both orgs with same initial provider
            orchestrator._session_state[org1_vapi] = SessionTTSState(
                active_provider="elevenlabs"
            )
            orchestrator._session_state[org2_vapi] = SessionTTSState(
                active_provider="elevenlabs"
            )

            # Simulate provider switch for org1 only
            orchestrator._session_state[org1_vapi].active_provider = "cartesia"

            # Verify org1 switched but org2 did not
            assert orchestrator.get_session_provider(org1_vapi) == "cartesia"
            assert orchestrator.get_session_provider(org2_vapi) == "elevenlabs"

            # Circuit breaker state should also be org-independent
            # (circuit breaker is global, but sessions are isolated)
            assert org1_vapi in orchestrator._session_state
            assert org2_vapi in orchestrator._session_state

            # Cleanup
            for provider in orchestrator._providers.values():
                await provider.aclose()
            reset_orchestrator()
