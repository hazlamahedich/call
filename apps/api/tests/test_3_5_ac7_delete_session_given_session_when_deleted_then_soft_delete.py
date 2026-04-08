"""Story 3.5 AC7: Delete Session.

Tests for ownership verification and soft-delete of session + turns.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest_3_5 import *
from services.script_lab import ScriptLabService


@pytest.mark.asyncio
class TestAC7DeleteSession:
    @pytest.mark.p0
    async def test_3_5_100_given_active_session_when_deleted_then_soft_delete_applied(
        self, mock_session, lab_service
    ):
        ownership_result = MagicMock()
        ownership_result.fetchone.return_value = (TEST_ORG,)
        mock_session.execute = AsyncMock(return_value=ownership_result)
        mock_session.flush = AsyncMock()

        await lab_service.delete_session(org_id=TEST_ORG, session_id=1)

        assert mock_session.execute.call_count == 3
        mock_session.flush.assert_awaited_once()

    @pytest.mark.p0
    async def test_3_5_101_given_nonexistent_session_when_deleted_then_404(
        self, mock_session, lab_service
    ):
        ownership_result = MagicMock()
        ownership_result.fetchone.return_value = None
        mock_session.execute = AsyncMock(return_value=ownership_result)

        with pytest.raises(HTTPException) as exc_info:
            await lab_service.delete_session(org_id=TEST_ORG, session_id=999)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"]["code"] == "session_not_found"

    @pytest.mark.p0
    async def test_3_5_102_given_cross_tenant_session_when_deleted_then_403(
        self, mock_session, lab_service
    ):
        ownership_result = MagicMock()
        ownership_result.fetchone.return_value = (TEST_ORG_B,)
        mock_session.execute = AsyncMock(return_value=ownership_result)

        with pytest.raises(HTTPException) as exc_info:
            await lab_service.delete_session(org_id=TEST_ORG, session_id=1)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"]["code"] == "NAMESPACE_VIOLATION"

    @pytest.mark.p1
    async def test_3_5_103_given_session_when_deleted_then_turns_also_soft_deleted(
        self, mock_session, lab_service
    ):
        ownership_result = MagicMock()
        ownership_result.fetchone.return_value = (TEST_ORG,)
        mock_session.execute = AsyncMock(return_value=ownership_result)
        mock_session.flush = AsyncMock()

        await lab_service.delete_session(org_id=TEST_ORG, session_id=42)

        executed_statements = [
            call.args[0].text if hasattr(call.args[0], "text") else str(call.args[0])
            for call in mock_session.execute.call_args_list
        ]

        session_delete_found = any(
            "soft_delete = true" in s and "script_lab_sessions" in s
            for s in executed_statements
        )
        turns_delete_found = any(
            "soft_delete = true" in s and "script_lab_turns" in s
            for s in executed_statements
        )

        assert session_delete_found
        assert turns_delete_found
