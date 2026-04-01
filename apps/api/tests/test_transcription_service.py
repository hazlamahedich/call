"""
Story 2.2: Real-time Audio Stream & Transcription Pipeline
Unit Tests for Transcription Service

Test ID Format: [2.2-UNIT-XXX]
"""

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.transcription import (
    _compute_latency,
    _map_role,
    _detect_interruption,
    handle_transcript_event,
    handle_speech_start,
    handle_speech_end,
    _resolve_call_id,
    _get_speech_state,
    _validate_transcript_obj,
    _row_to_transcript_entry,
    _row_to_voice_event,
)


def _make_row(**fields):
    row = MagicMock()
    row._mapping = fields
    return row


def _make_result(row=None, fetchall=None):
    result = MagicMock()
    result.first.return_value = row
    if fetchall is not None:
        result.fetchall.return_value = fetchall
    return result


class TestMapRole:
    """[2.2-UNIT-001..004] Role mapping tests"""

    def test_2_2_unit_001_given_assistant_role_when_map_then_returns_assistant_ai(
        self,
    ):
        assert _map_role("assistant") == "assistant-ai"

    def test_2_2_unit_002_given_user_role_when_map_then_returns_lead(self):
        assert _map_role("user") == "lead"

    def test_2_2_unit_003_given_human_role_when_map_then_returns_assistant_human(self):
        assert _map_role("human") == "assistant-human"

    def test_2_2_unit_004_given_unknown_role_when_map_then_returns_lead(self):
        assert _map_role("unknown") == "lead"


class TestComputeLatency:
    """[2.2-UNIT-005..008] Latency computation tests"""

    def test_2_2_unit_005_given_none_timestamp_when_compute_then_returns_none(self):
        result = _compute_latency(datetime.now(timezone.utc), None)
        assert result is None

    def test_2_2_unit_006_given_valid_timestamp_when_compute_then_returns_ms(self):
        now = datetime.now(timezone.utc)
        ts = now.timestamp() - 0.1
        result = _compute_latency(now, ts)
        assert result is not None
        assert 90 <= result <= 120

    def test_2_2_unit_007_given_future_timestamp_when_compute_then_returns_negative(
        self,
    ):
        now = datetime.now(timezone.utc)
        ts = now.timestamp() + 1.0
        result = _compute_latency(now, ts)
        assert result is not None
        assert result < 0

    def test_2_2_unit_008_given_invalid_timestamp_when_compute_then_returns_none(self):
        result = _compute_latency(datetime.now(timezone.utc), float("inf"))
        assert result is None


class TestHandleTranscriptEvent:
    """[2.2-UNIT-009..014] Transcript event handling tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_009_given_valid_transcript_when_handle_then_persists_entry(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=1,
            org_id="org_1",
            call_id=10,
            vapi_call_id="vci_1",
            role="lead",
            text="hello",
            start_time=0.0,
            end_time=1.5,
            confidence=0.95,
            words_json=None,
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
            entry = await handle_transcript_event(
                mock_session,
                "vci_1",
                "org_1",
                {"transcript": {"role": "user", "text": "hello", "words": []}},
            )

        assert entry is not None
        assert entry.role == "lead"
        assert entry.text == "hello"

    @pytest.mark.asyncio
    async def test_2_2_unit_010_given_assistant_role_when_handle_then_maps_to_assistant_ai(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=2,
            org_id="org_1",
            call_id=10,
            vapi_call_id="vci_2",
            role="assistant-ai",
            text="hi there",
            start_time=0.0,
            end_time=2.0,
            confidence=None,
            words_json=None,
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
            entry = await handle_transcript_event(
                mock_session,
                "vci_2",
                "org_1",
                {"transcript": {"role": "assistant", "text": "hi there"}},
            )

        assert entry.role == "assistant-ai"

    @pytest.mark.asyncio
    async def test_2_2_unit_011_given_words_with_timing_when_handle_then_extracts_start_end(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=5,
            org_id="org_1",
            call_id=10,
            vapi_call_id="vci_5",
            role="lead",
            text="hello world",
            start_time=0.3,
            end_time=1.8,
            confidence=0.965,
            words_json=None,
            received_at=now,
            vapi_event_timestamp=None,
            created_at=now,
            updated_at=now,
            soft_delete=False,
        )
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=row)

        words = [
            {"word": "hello", "start": 0.3, "end": 0.8, "confidence": 0.98},
            {"word": "world", "start": 1.0, "end": 1.8, "confidence": 0.95},
        ]

        with patch(
            "services.transcription._resolve_call_id",
            new_callable=AsyncMock,
            return_value=10,
        ):
            entry = await handle_transcript_event(
                mock_session,
                "vci_5",
                "org_1",
                {
                    "transcript": {
                        "role": "user",
                        "text": "hello world",
                        "words": words,
                    }
                },
            )

        assert entry is not None
        assert entry.start_time == 0.3
        assert entry.end_time == 1.8
        assert entry.confidence is not None
        assert abs(entry.confidence - 0.965) < 0.01

    @pytest.mark.asyncio
    async def test_2_2_unit_012_given_no_call_found_when_handle_then_raises_value_error(
        self,
    ):
        mock_session = AsyncMock()

        with patch(
            "services.transcription._resolve_call_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(ValueError, match="No call found for vapi_call_id"):
                await handle_transcript_event(
                    mock_session,
                    "vci_3",
                    "org_1",
                    {"transcript": {"role": "user", "text": "orphan text"}},
                )

    @pytest.mark.asyncio
    async def test_2_2_unit_013_given_timestamp_in_data_when_handle_then_computes_latency(
        self,
    ):
        now = datetime.now(timezone.utc)
        row = _make_row(
            id=4,
            org_id="org_1",
            call_id=10,
            vapi_call_id="vci_4",
            role="lead",
            text="timed text",
            start_time=0.0,
            end_time=1.0,
            confidence=None,
            words_json=None,
            received_at=now,
            vapi_event_timestamp=time.time() - 0.05,
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
            entry = await handle_transcript_event(
                mock_session,
                "vci_4",
                "org_1",
                {
                    "transcript": {"role": "user", "text": "timed text"},
                    "timestamp": time.time() - 0.05,
                },
            )

        assert entry is not None


class TestHandleSpeechStart:
    """[2.2-UNIT-015..018] Speech start handling tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_015_given_speech_start_when_handle_then_creates_event(self):
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
    async def test_2_2_unit_016_given_assistant_speaker_when_handle_then_maps_to_ai(
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
    async def test_2_2_unit_019_given_speech_end_when_handle_then_creates_event(self):
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
    async def test_2_2_unit_020_given_no_call_id_when_handle_then_still_persists(self):
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


class TestDetectInterruption:
    """[2.2-UNIT-021..023] Interruption detection tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_021_given_lead_speaking_while_ai_active_when_detect_then_returns_true(
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
    async def test_2_2_unit_022_given_ai_speaking_when_detect_then_returns_false(self):
        mock_session = AsyncMock()

        result = await _detect_interruption(mock_session, "vci_int2", "org_1", "ai")
        assert result is False

    @pytest.mark.asyncio
    async def test_2_2_unit_023_given_no_active_speech_when_detect_then_returns_false(
        self,
    ):
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=None)

        result = await _detect_interruption(mock_session, "vci_int3", "org_1", "lead")
        assert result is False


class TestValidateTranscriptObj:
    """[2.2-UNIT-024..028] Transcript object validation tests"""

    def test_2_2_unit_024_given_valid_dict_when_validate_then_returns_fields(self):
        data = {"transcript": {"role": "user", "text": "hi", "words": []}}
        result = _validate_transcript_obj(data)
        assert result["role"] == "user"
        assert result["text"] == "hi"
        assert result["words"] == []

    def test_2_2_unit_025_given_non_dict_transcript_when_validate_then_returns_defaults(
        self,
    ):
        data = {"transcript": "not-a-dict"}
        result = _validate_transcript_obj(data)
        assert result["role"] == "user"
        assert result["text"] == ""
        assert result["words"] == []

    def test_2_2_unit_026_given_non_list_words_when_validate_then_returns_empty_list(
        self,
    ):
        data = {"transcript": {"role": "user", "text": "hi", "words": "not-a-list"}}
        result = _validate_transcript_obj(data)
        assert result["words"] == []

    def test_2_2_unit_027_given_missing_transcript_key_when_validate_then_uses_root(
        self,
    ):
        data = {"role": "assistant", "text": "hello"}
        result = _validate_transcript_obj(data)
        assert result["role"] == "assistant"
        assert result["text"] == "hello"

    def test_2_2_unit_028_given_empty_dict_when_validate_then_returns_defaults(self):
        result = _validate_transcript_obj({})
        assert result["role"] == "user"
        assert result["text"] == ""
        assert result["words"] == []


class TestResolveCallId:
    """[2.2-UNIT-029..030] Call ID resolution tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_029_given_matching_call_when_resolve_then_returns_id(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = (42,)
        mock_session.execute.return_value = mock_result

        result = await _resolve_call_id(mock_session, "vci_match", "org_1")
        assert result == 42

    @pytest.mark.asyncio
    async def test_2_2_unit_030_given_no_matching_call_when_resolve_then_returns_none(
        self,
    ):
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=None)

        result = await _resolve_call_id(mock_session, "vci_ghost", "org_1")
        assert result is None


class TestGetSpeechState:
    """[2.2-UNIT-031..033] Speech state retrieval tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_031_given_speech_start_event_when_get_state_then_returns_dict(
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
    async def test_2_2_unit_032_given_no_speech_events_when_get_state_then_returns_none(
        self,
    ):
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=None)

        result = await _get_speech_state(mock_session, "vci_empty", "org_1")
        assert result is None

    @pytest.mark.asyncio
    async def test_2_2_unit_033_given_lead_speech_state_when_get_state_then_returns_lead(
        self,
    ):
        now = datetime.now(timezone.utc)
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=("lead", now))

        result = await _get_speech_state(mock_session, "vci_lead", "org_1")
        assert result is not None
        assert result["speaker"] == "lead"


class TestHandleSpeechStartInterruption:
    """[2.2-UNIT-034..036] Speech start with interruption detection"""

    @pytest.mark.asyncio
    async def test_2_2_unit_034_given_interruption_detected_when_speech_start_then_creates_interruption_event(
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
    async def test_2_2_unit_035_given_no_call_id_when_speech_start_then_still_creates_event(
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
    async def test_2_2_unit_036_given_interruption_metadata_when_speech_start_then_metadata_has_structure(
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
    """[2.2-UNIT-037..039] RuntimeError when INSERT RETURNING yields None"""

    @pytest.mark.asyncio
    async def test_2_2_unit_037_given_insert_returns_none_when_transcript_then_raises_runtime_error(
        self,
    ):
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=None)

        with patch(
            "services.transcription._resolve_call_id",
            new_callable=AsyncMock,
            return_value=10,
        ):
            with pytest.raises(RuntimeError, match="INSERT RETURNING"):
                await handle_transcript_event(
                    mock_session,
                    "vci_err",
                    "org_1",
                    {"transcript": {"role": "user", "text": "fail"}},
                )

    @pytest.mark.asyncio
    async def test_2_2_unit_038_given_insert_returns_none_when_speech_start_then_raises_runtime_error(
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

    @pytest.mark.asyncio
    async def test_2_2_unit_041_given_no_call_id_when_handle_then_no_broadcast(self):
        mock_session = AsyncMock()
        mock_session.execute.return_value = _make_result(row=None)

        with patch(
            "services.transcription._resolve_call_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(ValueError, match="No call found"):
                await handle_transcript_event(
                    mock_session,
                    "vci_no_call",
                    "org_1",
                    {"transcript": {"role": "user", "text": "no bcast"}},
                )


class TestMapRoleExtended:
    """[2.2-UNIT-042] Extended role mapping"""

    def test_2_2_unit_042_given_ai_role_when_map_then_returns_assistant_ai(self):
        assert _map_role("ai") == "assistant-ai"


class TestRowToModels:
    """[2.2-UNIT-043..046] Row-to-model conversion without _mapping"""

    def test_2_2_unit_043_given_row_without_mapping_when_to_transcript_entry_then_uses_dict(
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

    def test_2_2_unit_044_given_row_with_mapping_when_to_transcript_entry_then_uses_mapping(
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

    def test_2_2_unit_045_given_row_without_mapping_when_to_voice_event_then_uses_dict(
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

    def test_2_2_unit_046_given_row_with_mapping_when_to_voice_event_then_uses_mapping(
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


class TestHandleSpeechSpeakerEdgeCases:
    """[2.2-UNIT-047..048] Non-string speaker edge cases"""

    @pytest.mark.asyncio
    async def test_2_2_unit_047_given_non_string_speaker_when_speech_start_then_defaults_to_lead(
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
    async def test_2_2_unit_048_given_non_string_speaker_when_speech_end_then_defaults_to_lead(
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
