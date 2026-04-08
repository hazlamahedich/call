"""Story 3.5 AC6: Session Expiry.

Tests that expired sessions raise 410, max-turns sessions raise 422,
and background cleanup marks sessions as expired.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest_3_5 import (
    TEST_ORG,
    mock_session,
    lab_service,
    make_active_row,
    make_expired_row,
)
from services.script_lab import ScriptLabService


@pytest.mark.asyncio
class TestAC6SessionExpiry:
    @pytest.mark.p0
    async def test_3_5_021_given_session_past_ttl_when_sending_chat_then_raises_410(
        self, mock_session, lab_service
    ):
        expired_row = make_expired_row()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = expired_row
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await lab_service._check_session_expiry(expired_row)

        assert exc_info.value.status_code == 410
        assert exc_info.value.detail["error"]["code"] == "session_expired"

    @pytest.mark.p0
    async def test_3_5_022_given_session_about_to_expire_when_ttl_checked_then_410(
        self, mock_session, lab_service
    ):
        barely_expired = make_expired_row(
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
        )
        mock_result = MagicMock()
        mock_result.fetchone.return_value = barely_expired
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await lab_service._check_session_expiry(barely_expired)

        assert exc_info.value.status_code == 410
        assert exc_info.value.detail["error"]["code"] == "session_expired"

    @pytest.mark.p0
    async def test_3_5_022b_given_session_at_max_turns_when_sending_chat_then_422(
        self, mock_session, lab_service
    ):
        max_turns_row = make_active_row(turn_count=50)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = max_turns_row
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()

        with patch("services.script_lab.settings") as mock_settings:
            mock_settings.SCRIPT_LAB_MAX_TURNS = 50
            with patch("services.script_lab.set_rls_context", new_callable=AsyncMock):
                with pytest.raises(HTTPException) as exc_info:
                    await lab_service.send_chat_message(
                        org_id=TEST_ORG,
                        session_id=1,
                        message="Hello",
                    )

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["error"]["code"] == "max_turns_reached"

    @pytest.mark.p0
    async def test_3_5_023_given_background_cleanup_when_sessions_expire_then_status_set(
        self, mock_session, lab_service
    ):
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        count = await lab_service.cleanup_expired_sessions()

        assert count == 3
        mock_session.commit.assert_awaited_once()

    @pytest.mark.p1
    async def test_3_5_023b_given_no_expired_sessions_when_cleanup_then_zero_returned(
        self, mock_session, lab_service
    ):
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await lab_service.cleanup_expired_sessions()

        assert count == 0
        mock_session.commit.assert_not_awaited()

    @pytest.mark.p1
    async def test_3_5_021b_given_session_already_expired_status_when_chat_then_410(
        self, mock_session, lab_service
    ):
        expired_status_row = make_active_row(status="expired")
        mock_result = MagicMock()
        mock_result.fetchone.return_value = expired_status_row
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.script_lab.set_rls_context", new_callable=AsyncMock):
            with pytest.raises(HTTPException) as exc_info:
                await lab_service.send_chat_message(
                    org_id=TEST_ORG,
                    session_id=1,
                    message="Hello",
                )

        assert exc_info.value.status_code == 410
        assert exc_info.value.detail["error"]["code"] == "session_expired"
