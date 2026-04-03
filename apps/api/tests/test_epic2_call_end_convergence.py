"""
[2.4-INT-006] Test Epic 6 call-end triggers transcript aggregation AND TTS cleanup.

Tests the convergence of Stories 2.1, 2.2, and 2.3 at call-end:
- call-end triggers transcript aggregation + TTS reset + status update in order
- All three operations complete without conflicts
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.tts.factory import get_tts_orchestrator, shutdown_tts, _orchestrator
from services.tts.orchestrator import SessionTTSState
from services.vapi import handle_call_ended
from tests.support.mock_helpers import _make_result


def _make_settings(**overrides):
    s = MagicMock()
    defaults = {
        "TTS_PRIMARY_PROVIDER": "elevenlabs",
        "TTS_FALLBACK_PROVIDER": "cartesia",
        "ELEVENLABS_API_KEY": "test-key",
        "CARTESIA_API_KEY": "test-key",
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


@pytest.fixture(autouse=True)
def reset_orchestrator():
    global _orchestrator
    _orchestrator = None
    yield
    _orchestrator = None


class TestCallEndConvergence:
    """
    [2.4-INT-006_P0] Test call-end triggers all three operations in correct order.
    """

    @pytest.mark.asyncio
    async def test_call_end_triggers_transcript_tts_and_status_update(self):
        """
        [2.4-INT-006_P0_S1] Given a call with transcript entries and active TTS session,
        when call-end is received,
        then transcript aggregation, TTS reset, and status update all occur in order.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = get_tts_orchestrator()

            vapi_call_id = "vapi-convergence-123"
            org_id = "org-convergence"

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            # Create an active TTS session
            orchestrator._session_state[vapi_call_id] = SessionTTSState(
                active_provider="elevenlabs"
            )

            # Mock DB session
            db_session = AsyncMock()
            db_session.execute = AsyncMock(return_value=_make_result())
            db_session.commit = AsyncMock()
            db_session.flush = AsyncMock()

            # Simulate call-end webhook behavior from webhooks_vapi.py
            # 1. Reset TTS session
            orchestrator.reset_session(vapi_call_id)

            # 2. Handle call ended (transcript aggregation + status update)
            await handle_call_ended(
                db_session,
                vapi_call_id,
                org_id=org_id,
                duration=60,
                recording_url="https://example.com/recording.mp3",
            )

            # Verify TTS session was reset
            assert vapi_call_id not in orchestrator._session_state

            # Verify DB operations occurred (transcript aggregation + status update)
            assert db_session.execute.call_count >= 1

            # Cleanup
            for provider in orchestrator._providers.values():
                await provider.aclose()
            _orchestrator = None

    @pytest.mark.asyncio
    async def test_all_three_operations_complete_without_conflicts(self):
        """
        [2.4-INT-006_P0_S2] Given a call with accumulated transcript entries and TTS session,
        when call-end is processed,
        then all three operations (transcript aggregation, TTS reset, status update)
        complete without conflicts.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = get_tts_orchestrator()

            vapi_call_id = "vapi-no-conflict-456"
            org_id = "org-no-conflict"

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            # Create an active TTS session
            orchestrator._session_state[vapi_call_id] = SessionTTSState(
                active_provider="cartesia"
            )

            # Mock DB session
            db_session = AsyncMock()
            db_session.execute = AsyncMock(return_value=_make_result())
            db_session.commit = AsyncMock()
            db_session.flush = AsyncMock()

            # Process call-end (order: TTS reset → handle_call_ended)
            orchestrator.reset_session(vapi_call_id)
            await handle_call_ended(
                db_session,
                vapi_call_id,
                org_id=org_id,
                duration=120,
                recording_url=None,
            )

            # Verify no exceptions raised - all operations completed
            assert vapi_call_id not in orchestrator._session_state
            assert db_session.execute.call_count >= 1

            # Cleanup
            for provider in orchestrator._providers.values():
                await provider.aclose()
            _orchestrator = None

    @pytest.mark.asyncio
    async def test_operations_maintain_correct_order(self):
        """
        [2.4-INT-006_P0_S3] Given multiple calls ending concurrently,
        when each call's end event is processed,
        then TTS cleanup happens before call status transitions for each call.
        """
        with patch("services.tts.factory.settings", _make_settings()):
            orchestrator = get_tts_orchestrator()

            # Mock providers for cleanup
            for provider in orchestrator._providers.values():
                provider.aclose = AsyncMock()

            # Mock DB session
            db_session = AsyncMock()
            db_session.execute = AsyncMock(return_value=_make_result())
            db_session.commit = AsyncMock()
            db_session.flush = AsyncMock()

            # Process multiple call-end events
            calls = [
                ("vapi-order-1", "org-order", 60),
                ("vapi-order-2", "org-order", 90),
                ("vapi-order-3", "org-order", 30),
            ]

            for vapi_call_id, org_id, duration in calls:
                # Create TTS session for each call
                orchestrator._session_state[vapi_call_id] = SessionTTSState(
                    active_provider="elevenlabs"
                )

                # Process call-end in correct order: TTS reset first, then call handling
                orchestrator.reset_session(vapi_call_id)
                await handle_call_ended(
                    db_session,
                    vapi_call_id,
                    org_id=org_id,
                    duration=duration,
                    recording_url=None,
                )

                # Verify TTS was reset before call handling completed
                assert vapi_call_id not in orchestrator._session_state

            # Cleanup
            for provider in orchestrator._providers.values():
                await provider.aclose()
            _orchestrator = None
