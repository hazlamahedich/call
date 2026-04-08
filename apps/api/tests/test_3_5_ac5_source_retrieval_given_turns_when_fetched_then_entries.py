"""Story 3.5 AC5: Source Retrieval (get_session_sources).

Tests for session ownership verification, turn pairing, source formatting,
display turn number calculation, and empty sessions.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest_3_5 import (
    TEST_ORG,
    TEST_ORG_B,
    mock_session,
    lab_service,
)
from services.script_lab import ScriptLabService


@pytest.mark.asyncio
class TestAC5SourceRetrieval:
    @pytest.mark.p0
    async def test_3_5_090_given_session_with_turns_when_sources_fetched_then_entries_returned(
        self, mock_session, lab_service
    ):
        ownership_result = MagicMock()
        ownership_result.fetchone.return_value = (TEST_ORG,)

        turns_result = MagicMock()
        turns_result.fetchall.return_value = [
            (1, "user", "Hello", None, None),
            (
                2,
                "assistant",
                "AI reply",
                [
                    {
                        "chunk_id": 42,
                        "document_name": "doc.pdf",
                        "page_number": 3,
                        "excerpt": "text",
                        "similarity_score": 0.9,
                    }
                ],
                0.9,
            ),
        ]

        call_count = 0

        async def mock_execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ownership_result
            return turns_result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        entries = await lab_service.get_session_sources(org_id=TEST_ORG, session_id=1)

        assert len(entries) == 1
        assert entries[0].turn_number == 1
        assert entries[0].user_message == "Hello"
        assert entries[0].ai_response == "AI reply"
        assert entries[0].grounding_confidence == 0.9
        assert len(entries[0].sources) == 1
        assert entries[0].sources[0].chunk_id == 42

    @pytest.mark.p0
    async def test_3_5_091_given_nonexistent_session_when_sources_fetched_then_404(
        self, mock_session, lab_service
    ):
        ownership_result = MagicMock()
        ownership_result.fetchone.return_value = None
        mock_session.execute = AsyncMock(return_value=ownership_result)

        with pytest.raises(HTTPException) as exc_info:
            await lab_service.get_session_sources(org_id=TEST_ORG, session_id=999)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"]["code"] == "session_not_found"

    @pytest.mark.p0
    async def test_3_5_092_given_cross_tenant_session_when_sources_fetched_then_403(
        self, mock_session, lab_service
    ):
        ownership_result = MagicMock()
        ownership_result.fetchone.return_value = (TEST_ORG_B,)
        mock_session.execute = AsyncMock(return_value=ownership_result)

        with pytest.raises(HTTPException) as exc_info:
            await lab_service.get_session_sources(org_id=TEST_ORG, session_id=1)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"]["code"] == "NAMESPACE_VIOLATION"

    @pytest.mark.p1
    async def test_3_5_093_given_multiple_turn_pairs_when_sources_fetched_then_display_turns_sequential(
        self, mock_session, lab_service
    ):
        ownership_result = MagicMock()
        ownership_result.fetchone.return_value = (TEST_ORG,)

        turns_result = MagicMock()
        turns_result.fetchall.return_value = [
            (1, "user", "Q1", None, None),
            (
                2,
                "assistant",
                "A1",
                [
                    {
                        "chunk_id": 1,
                        "document_name": "d.pdf",
                        "page_number": None,
                        "excerpt": "e",
                        "similarity_score": 0.8,
                    }
                ],
                0.8,
            ),
            (3, "user", "Q2", None, None),
            (
                4,
                "assistant",
                "A2",
                [
                    {
                        "chunk_id": 2,
                        "document_name": "d2.pdf",
                        "page_number": 1,
                        "excerpt": "f",
                        "similarity_score": 0.7,
                    }
                ],
                0.7,
            ),
        ]

        call_count = 0

        async def mock_execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ownership_result
            return turns_result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        entries = await lab_service.get_session_sources(org_id=TEST_ORG, session_id=1)

        assert len(entries) == 2
        assert entries[0].turn_number == 1
        assert entries[0].user_message == "Q1"
        assert entries[1].turn_number == 2
        assert entries[1].user_message == "Q2"

    @pytest.mark.p1
    async def test_3_5_094_given_session_with_no_assistant_turns_when_sources_fetched_then_empty(
        self, mock_session, lab_service
    ):
        ownership_result = MagicMock()
        ownership_result.fetchone.return_value = (TEST_ORG,)

        turns_result = MagicMock()
        turns_result.fetchall.return_value = [
            (1, "user", "Hello", None, None),
        ]

        call_count = 0

        async def mock_execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ownership_result
            return turns_result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        entries = await lab_service.get_session_sources(org_id=TEST_ORG, session_id=1)

        assert entries == []

    @pytest.mark.p1
    async def test_3_5_095_given_assistant_turn_without_matching_user_when_sources_fetched_then_empty_user_msg(
        self, mock_session, lab_service
    ):
        ownership_result = MagicMock()
        ownership_result.fetchone.return_value = (TEST_ORG,)

        turns_result = MagicMock()
        turns_result.fetchall.return_value = [
            (
                2,
                "assistant",
                "Orphan reply",
                [
                    {
                        "chunk_id": 1,
                        "document_name": "d.pdf",
                        "page_number": None,
                        "excerpt": "e",
                        "similarity_score": 0.5,
                    }
                ],
                0.5,
            ),
        ]

        call_count = 0

        async def mock_execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ownership_result
            return turns_result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        entries = await lab_service.get_session_sources(org_id=TEST_ORG, session_id=1)

        assert len(entries) == 1
        assert entries[0].user_message == ""
        assert entries[0].ai_response == "Orphan reply"

    @pytest.mark.p2
    async def test_3_5_096_given_null_grounding_confidence_when_sources_fetched_then_default_zero(
        self, mock_session, lab_service
    ):
        ownership_result = MagicMock()
        ownership_result.fetchone.return_value = (TEST_ORG,)

        turns_result = MagicMock()
        turns_result.fetchall.return_value = [
            (1, "user", "Hi", None, None),
            (
                2,
                "assistant",
                "Reply",
                [
                    {
                        "chunk_id": 1,
                        "document_name": "d.pdf",
                        "page_number": None,
                        "excerpt": "e",
                        "similarity_score": 0.5,
                    }
                ],
                None,
            ),
        ]

        call_count = 0

        async def mock_execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ownership_result
            return turns_result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        entries = await lab_service.get_session_sources(org_id=TEST_ORG, session_id=1)

        assert entries[0].grounding_confidence == 0.0
