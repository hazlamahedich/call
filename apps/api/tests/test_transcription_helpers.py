"""
Story 2.2: Real-time Audio Stream & Transcription Pipeline
Helper Function Unit Tests (interruption detection, validation, resolution, state, row-to-model)

Test ID Format: [2.2-UNIT-XXX]
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.transcription import (
    _detect_interruption,
    _get_speech_state,
    _resolve_call_id,
    _validate_transcript_obj,
    _row_to_transcript_entry,
    _row_to_voice_event,
)
from tests.support.mock_helpers import _make_row, _make_result


class TestDetectInterruption:
    """[2.2-UNIT-021..023] Interruption detection tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_021_P0_given_lead_speaking_while_ai_active_when_detect_then_returns_true(
        self,
    ):
        now = datetime.now(timezone.utc)
        mock_session = AsyncMock()
        mock_session.execute.side_effect = [
            _make_result(row=("ai", now)),
            _make_result(row=None),
        ]

        result = await _detect_interruption(mock_session, "vci_int", "org_1", "lead")
        assert result is True

    @pytest.mark.asyncio
    async def test_2_2_unit_022_P1_given_ai_speaking_when_detect_then_returns_false(
        self,
    ):
        mock_session = AsyncMock()

        result = await _detect_interruption(mock_session, "vci_int2", "org_1", "ai")
        assert result is False

    @pytest.mark.asyncio
    async def test_2_2_unit_023_P1_given_no_active_speech_when_detect_then_returns_false(
        self,
    ):
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=None)

        result = await _detect_interruption(mock_session, "vci_int3", "org_1", "lead")
        assert result is False


class TestValidateTranscriptObj:
    """[2.2-UNIT-024..028] Transcript object validation tests"""

    def test_2_2_unit_024_P1_given_valid_dict_when_validate_then_returns_fields(self):
        data = {"transcript": {"role": "user", "text": "hi", "words": []}}
        result = _validate_transcript_obj(data)
        assert result["role"] == "user"
        assert result["text"] == "hi"
        assert result["words"] == []

    def test_2_2_unit_025_P1_given_non_dict_transcript_when_validate_then_returns_defaults(
        self,
    ):
        data = {"transcript": "not-a-dict"}
        result = _validate_transcript_obj(data)
        assert result["role"] == "user"
        assert result["text"] == ""
        assert result["words"] == []

    def test_2_2_unit_026_P1_given_non_list_words_when_validate_then_returns_empty_list(
        self,
    ):
        data = {"transcript": {"role": "user", "text": "hi", "words": "not-a-list"}}
        result = _validate_transcript_obj(data)
        assert result["words"] == []

    def test_2_2_unit_027_P1_given_missing_transcript_key_when_validate_then_uses_root(
        self,
    ):
        data = {"role": "assistant", "text": "hello"}
        result = _validate_transcript_obj(data)
        assert result["role"] == "assistant"
        assert result["text"] == "hello"

    def test_2_2_unit_028_P1_given_empty_dict_when_validate_then_returns_defaults(self):
        result = _validate_transcript_obj({})
        assert result["role"] == "user"
        assert result["text"] == ""
        assert result["words"] == []


class TestResolveCallId:
    """[2.2-UNIT-029..030] Call ID resolution tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_029_P1_given_matching_call_when_resolve_then_returns_id(
        self,
    ):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = (42,)
        mock_session.execute.return_value = mock_result

        result = await _resolve_call_id(mock_session, "vci_match", "org_1")
        assert result == 42

    @pytest.mark.asyncio
    async def test_2_2_unit_030_P1_given_no_matching_call_when_resolve_then_returns_none(
        self,
    ):
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=None)

        result = await _resolve_call_id(mock_session, "vci_ghost", "org_1")
        assert result is None


class TestGetSpeechState:
    """[2.2-UNIT-031..033] Speech state retrieval tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_031_P1_given_speech_start_event_when_get_state_then_returns_dict(
        self,
    ):
        now = datetime.now(timezone.utc)
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=("ai", now))

        result = await _get_speech_state(mock_session, "vci_ss", "org_1")
        assert result is not None
        assert result["speaker"] == "ai"
        assert result["speech_started_at"] == now

    @pytest.mark.asyncio
    async def test_2_2_unit_032_P1_given_no_speech_events_when_get_state_then_returns_none(
        self,
    ):
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=None)

        result = await _get_speech_state(mock_session, "vci_empty", "org_1")
        assert result is None

    @pytest.mark.asyncio
    async def test_2_2_unit_033_P1_given_lead_speech_state_when_get_state_then_returns_lead(
        self,
    ):
        now = datetime.now(timezone.utc)
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=("lead", now))

        result = await _get_speech_state(mock_session, "vci_lead", "org_1")
        assert result is not None
        assert result["speaker"] == "lead"


class TestRowToModels:
    """[2.2-UNIT-043..046] Row-to-model conversion without _mapping"""

    def test_2_2_unit_043_P2_given_row_without_mapping_when_to_transcript_entry_then_uses_dict(
        self,
    ):
        now = datetime.now(timezone.utc)
        plain_dict = {
            "id": 1,
            "org_id": "org_1",
            "call_id": 10,
            "vapi_call_id": "vci_1",
            "role": "lead",
            "text": "hello",
            "start_time": 0.0,
            "end_time": 1.5,
            "confidence": 0.95,
            "words_json": None,
            "received_at": now,
            "vapi_event_timestamp": None,
            "created_at": now,
            "updated_at": now,
            "soft_delete": False,
        }

        entry = _row_to_transcript_entry(plain_dict)
        assert entry.id == 1
        assert entry.role == "lead"
        assert entry.text == "hello"
        assert entry.call_id == 10

    def test_2_2_unit_044_P2_given_row_with_mapping_when_to_transcript_entry_then_uses_mapping(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=2,
            org_id="org_1",
            call_id=20,
            vapi_call_id="vci_2",
            role="assistant-ai",
            text="hi",
            start_time=0.0,
            end_time=1.0,
            confidence=None,
            words_json=None,
            received_at=now,
            vapi_event_timestamp=None,
            created_at=now,
            updated_at=now,
            soft_delete=False,
        )

        entry = _row_to_transcript_entry(row)
        assert entry.id == 2
        assert entry.role == "assistant-ai"

    def test_2_2_unit_045_P2_given_row_without_mapping_when_to_voice_event_then_uses_dict(
        self,
    ):
        now = datetime.now(timezone.utc)
        plain_dict = {
            "id": 1,
            "org_id": "org_1",
            "call_id": 10,
            "vapi_call_id": "vci_v1",
            "event_type": "speech_start",
            "speaker": "lead",
            "event_metadata": None,
            "received_at": now,
            "vapi_event_timestamp": None,
            "created_at": now,
            "updated_at": now,
            "soft_delete": False,
        }

        event = _row_to_voice_event(plain_dict)
        assert event.id == 1
        assert event.event_type == "speech_start"
        assert event.speaker == "lead"

    def test_2_2_unit_046_P2_given_row_with_mapping_when_to_voice_event_then_uses_mapping(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=2,
            org_id="org_1",
            call_id=10,
            vapi_call_id="vci_v2",
            event_type="interruption",
            speaker="lead",
            event_metadata='{"key": "val"}',
            received_at=now,
            vapi_event_timestamp=None,
            created_at=now,
            updated_at=now,
            soft_delete=False,
        )

        event = _row_to_voice_event(row)
        assert event.event_type == "interruption"
