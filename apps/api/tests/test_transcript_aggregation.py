"""
Story 2.2: Real-time Audio Stream & Transcription Pipeline
Call Transcript Aggregation Tests

Test ID Format: [2.2-UNIT-XXX]
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_call_row(**overrides):
    defaults = {
        "id": 42,
        "org_id": "org_1",
        "vapi_call_id": "vci_agg",
        "lead_id": None,
        "agent_id": None,
        "campaign_id": None,
        "status": "completed",
        "duration": 120,
        "recording_url": None,
        "phone_number": "+1234567890",
        "transcript": None,
        "ended_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "soft_delete": False,
    }
    defaults.update(overrides)

    row = MagicMock()
    row._mapping = defaults
    return row


def _make_result(row=None, fetchall=None):
    result = MagicMock()
    result.first.return_value = row
    if fetchall is not None:
        result.fetchall.return_value = fetchall
    return result


def _any_result():
    return MagicMock()


class TestTranscriptAggregation:
    """[2.2-UNIT-500..502] Call-end transcript aggregation tests"""

    @pytest.mark.asyncio
    async def test_2_2_unit_500_given_entries_exist_when_call_ends_then_transcript_aggregated(
        self,
    ):
        mock_session = AsyncMock()

        call_row = _make_call_row(id=42, vapi_call_id="vci_agg")
        update_result = _make_result(row=call_row)

        entries = [("assistant-ai", "Hello there"), ("lead", "I am interested")]
        entries_result = _make_result(fetchall=entries)

        transcript_update_result = _make_result()

        mock_session.execute.side_effect = [
            _any_result(),
            update_result,
            entries_result,
            transcript_update_result,
        ]

        from services.vapi import handle_call_ended

        call = await handle_call_ended(
            mock_session,
            "vci_agg",
            org_id="org_1",
            duration=120,
            recording_url=None,
        )

        assert call.transcript is not None
        assert "[AI]: Hello there" in call.transcript
        assert "[Lead]: I am interested" in call.transcript

    @pytest.mark.asyncio
    async def test_2_2_unit_501_given_no_entries_when_call_ends_then_transcript_stays_null(
        self,
    ):
        mock_session = AsyncMock()

        call_row = _make_call_row(id=43, vapi_call_id="vci_empty", transcript=None)
        update_result = _make_result(row=call_row)

        entries_result = _make_result(fetchall=[])

        mock_session.execute.side_effect = [
            _any_result(),
            update_result,
            entries_result,
        ]

        from services.vapi import handle_call_ended

        call = await handle_call_ended(
            mock_session,
            "vci_empty",
            org_id="org_1",
            duration=60,
            recording_url=None,
        )

        assert call.transcript is None

    @pytest.mark.asyncio
    async def test_2_2_unit_502_given_aggregation_error_when_call_ends_then_graceful(
        self,
    ):
        mock_session = AsyncMock()

        call_row = _make_call_row(id=44, vapi_call_id="vci_err", transcript=None)
        update_result = _make_result(row=call_row)

        mock_session.execute.side_effect = [
            _any_result(),
            update_result,
            Exception("DB error"),
        ]

        from services.vapi import handle_call_ended

        call = await handle_call_ended(
            mock_session,
            "vci_err",
            org_id="org_1",
            duration=30,
            recording_url=None,
        )

        assert call is not None
