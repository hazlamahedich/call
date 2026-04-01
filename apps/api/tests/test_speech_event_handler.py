"""
Story 2.2: Real-time Audio Stream & Transcription Pipeline
Speech Event Handler Unit Tests

Test ID Format: [2.2-UNIT-XXX]
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.transcription import (
    handle_speech_start,
    handle_speech_end,
)
from tests.support.mock_helpers import _make_row, _make_result


class TestHandleSpeechStart:
    """[2.2-UNIT-015..016] Speech start handling tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_015_P0_given_speech_start_when_handle_then_creates_event(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=1,
            org_id="org_1",
            call_id=10,
            vapi_call_id="vci_s",
            event_type="speech_start",
            speaker="lead",
            event_metadata=None,
            received_at=now,
            vapi_event_timestamp=None,
            created_at=now,
            updated_at=now,
            soft_delete=False,
        )
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=row)

        with (
            patch(
                "services.transcription._resolve_call_id",
                new_callable=AsyncMock,
                return_value=10,
            ),
            patch(
                "services.transcription._detect_interruption",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            event = await handle_speech_start(
                mock_session,
                "vci_s",
                "org_1",
                {"speaker": "lead"},
            )

        assert event.event_type == "speech_start"
        assert event.speaker == "lead"

    @pytest.mark.asyncio
    async def test_2_2_unit_016_P0_given_assistant_speaker_when_handle_then_maps_to_ai(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=2,
            org_id="org_1",
            call_id=10,
            vapi_call_id="vci_s2",
            event_type="speech_start",
            speaker="ai",
            event_metadata=None,
            received_at=now,
            vapi_event_timestamp=None,
            created_at=now,
            updated_at=now,
            soft_delete=False,
        )
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=row)

        with (
            patch(
                "services.transcription._resolve_call_id",
                new_callable=AsyncMock,
                return_value=10,
            ),
            patch(
                "services.transcription._detect_interruption",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            event = await handle_speech_start(
                mock_session,
                "vci_s2",
                "org_1",
                {"speaker": "assistant"},
            )

        assert event.speaker == "ai"


class TestHandleSpeechEnd:
    """[2.2-UNIT-019..020] Speech end handling tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_019_P1_given_speech_end_when_handle_then_creates_event(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=1,
            org_id="org_1",
            call_id=10,
            vapi_call_id="vci_e",
            event_type="speech_end",
            speaker="lead",
            event_metadata=None,
            received_at=now,
            vapi_event_timestamp=None,
            created_at=now,
            updated_at=now,
            soft_delete=False,
        )
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=row)

        with patch(
            "services.transcription._resolve_call_id",
            new_callable=AsyncMock,
            return_value=10,
        ):
            event = await handle_speech_end(
                mock_session,
                "vci_e",
                "org_1",
                {"speaker": "lead"},
            )

        assert event.event_type == "speech_end"

    @pytest.mark.asyncio
    async def test_2_2_unit_020_P1_given_no_call_id_when_handle_then_still_persists(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=2,
            org_id="org_1",
            call_id=None,
            vapi_call_id="vci_e2",
            event_type="speech_end",
            speaker="lead",
            event_metadata=None,
            received_at=now,
            vapi_event_timestamp=None,
            created_at=now,
            updated_at=now,
            soft_delete=False,
        )
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=row)

        with patch(
            "services.transcription._resolve_call_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            event = await handle_speech_end(
                mock_session,
                "vci_e2",
                "org_1",
                {"speaker": "lead"},
            )

        assert event is not None


class TestHandleSpeechStartInterruption:
    """[2.2-UNIT-034..036] Speech start with interruption detection"""

    @pytest.mark.asyncio
    async def test_2_2_unit_034_P0_given_interruption_detected_when_speech_start_then_creates_interruption_event(
        self,
    ):
        now = datetime.now(timezone.utc)
        speech_start_row = _make_row(
            id=1,
            org_id="org_1",
            call_id=10,
            vapi_call_id="vci_int_branch",
            event_type="speech_start",
            speaker="lead",
            event_metadata=None,
            received_at=now,
            vapi_event_timestamp=None,
            created_at=now,
            updated_at=now,
            soft_delete=False,
        )
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=speech_start_row)

        with (
            patch(
                "services.transcription._resolve_call_id",
                new_callable=AsyncMock,
                return_value=10,
            ),
            patch(
                "services.transcription._detect_interruption",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "services.transcription._broadcast_speech_state",
                new_callable=AsyncMock,
            ),
        ):
            event = await handle_speech_start(
                mock_session,
                "vci_int_branch",
                "org_1",
                {"speaker": "lead"},
            )

        assert event is not None
        assert mock_session.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_2_2_unit_035_P1_given_no_call_id_when_speech_start_then_still_creates_event(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=2,
            org_id="org_1",
            call_id=None,
            vapi_call_id="vci_no_call",
            event_type="speech_start",
            speaker="lead",
            event_metadata=None,
            received_at=now,
            vapi_event_timestamp=None,
            created_at=now,
            updated_at=now,
            soft_delete=False,
        )
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=row)

        with (
            patch(
                "services.transcription._resolve_call_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "services.transcription._detect_interruption",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "services.transcription._broadcast_speech_state",
                new_callable=AsyncMock,
            ),
        ):
            event = await handle_speech_start(
                mock_session,
                "vci_no_call",
                "org_1",
                {"speaker": "lead"},
            )

        assert event is not None

    @pytest.mark.asyncio
    async def test_2_2_unit_036_P0_given_interruption_metadata_when_speech_start_then_metadata_has_structure(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=3,
            org_id="org_1",
            call_id=10,
            vapi_call_id="vci_meta",
            event_type="speech_start",
            speaker="lead",
            event_metadata=None,
            received_at=now,
            vapi_event_timestamp=None,
            created_at=now,
            updated_at=now,
            soft_delete=False,
        )
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=row)

        with (
            patch(
                "services.transcription._resolve_call_id",
                new_callable=AsyncMock,
                return_value=10,
            ),
            patch(
                "services.transcription._detect_interruption",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "services.transcription._broadcast_speech_state",
                new_callable=AsyncMock,
            ),
        ):
            await handle_speech_start(
                mock_session,
                "vci_meta",
                "org_1",
                {"speaker": "lead"},
            )

        calls = mock_session.execute.call_args_list
        assert len(calls) >= 2
        interruption_call = calls[1]
        assert "interrupted_speaker" in str(interruption_call)


class TestRuntimeErrorBranches:
    """[2.2-UNIT-038] RuntimeError when INSERT RETURNING yields None (speech)"""

    @pytest.mark.asyncio
    async def test_2_2_unit_038_P1_given_insert_returns_none_when_speech_start_then_raises_runtime_error(
        self,
    ):
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=None)

        with (
            patch(
                "services.transcription._resolve_call_id",
                new_callable=AsyncMock,
                return_value=10,
            ),
            patch(
                "services.transcription._detect_interruption",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            with pytest.raises(RuntimeError, match="INSERT RETURNING"):
                await handle_speech_start(
                    mock_session,
                    "vci_err",
                    "org_1",
                    {"speaker": "lead"},
                )


class TestHandleSpeechSpeakerEdgeCases:
    """[2.2-UNIT-047..048] Non-string speaker edge cases"""

    @pytest.mark.asyncio
    async def test_2_2_unit_047_P1_given_non_string_speaker_when_speech_start_then_defaults_to_lead(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=1,
            org_id="org_1",
            call_id=10,
            vapi_call_id="vci_ns",
            event_type="speech_start",
            speaker="lead",
            event_metadata=None,
            received_at=now,
            vapi_event_timestamp=None,
            created_at=now,
            updated_at=now,
            soft_delete=False,
        )
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=row)

        with (
            patch(
                "services.transcription._resolve_call_id",
                new_callable=AsyncMock,
                return_value=10,
            ),
            patch(
                "services.transcription._detect_interruption",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "services.transcription._broadcast_speech_state",
                new_callable=AsyncMock,
            ),
        ):
            event = await handle_speech_start(
                mock_session,
                "vci_ns",
                "org_1",
                {"speaker": 123},
            )

        assert event.speaker == "lead"

    @pytest.mark.asyncio
    async def test_2_2_unit_048_P1_given_non_string_speaker_when_speech_end_then_defaults_to_lead(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=1,
            org_id="org_1",
            call_id=10,
            vapi_call_id="vci_nse",
            event_type="speech_end",
            speaker="lead",
            event_metadata=None,
            received_at=now,
            vapi_event_timestamp=None,
            created_at=now,
            updated_at=now,
            soft_delete=False,
        )
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=row)

        with (
            patch(
                "services.transcription._resolve_call_id",
                new_callable=AsyncMock,
                return_value=10,
            ),
            patch(
                "services.transcription._broadcast_speech_state",
                new_callable=AsyncMock,
            ),
        ):
            event = await handle_speech_end(
                mock_session,
                "vci_nse",
                "org_1",
                {"speaker": None},
            )

        assert event.speaker == "lead"
