"""
Story 2.2: Real-time Audio Stream & Transcription Pipeline
Transcript Event Handler Unit Tests

Test ID Format: [2.2-UNIT-XXX]
"""

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from services.transcription import handle_transcript_event
from tests.support.mock_helpers import _make_row, _make_result


class TestHandleTranscriptEvent:
    """[2.2-UNIT-009..013] Transcript event handling tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_009_P0_given_valid_transcript_when_handle_then_persists_entry(
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
    async def test_2_2_unit_010_P0_given_assistant_role_when_handle_then_maps_to_assistant_ai(
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
    async def test_2_2_unit_011_P0_given_words_with_timing_when_handle_then_extracts_start_end(
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
    async def test_2_2_unit_012_P0_given_no_call_found_when_handle_then_raises_value_error(
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
    async def test_2_2_unit_013_P1_given_timestamp_in_data_when_handle_then_computes_latency(
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


class TestRuntimeErrorBranches:
    """[2.2-UNIT-037..039] RuntimeError when INSERT RETURNING yields None"""

    @pytest.mark.asyncio
    async def test_2_2_unit_037_P1_given_insert_returns_none_when_transcript_then_raises_runtime_error(
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
    async def test_2_2_unit_041_P1_given_no_call_id_when_handle_then_no_broadcast(self):
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
