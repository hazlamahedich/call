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
