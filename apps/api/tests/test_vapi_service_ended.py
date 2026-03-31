"""
Story 2.1: Vapi Telephony Bridge & Webhook Integration
Unit Tests for handle_call_ended (business logic)

Test ID Format: [2.1-UNIT-XXX]
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from tests.support.factories import CallFactory


class TestHandleCallEnded:
    """[2.1-UNIT-120..122] handle_call_ended business logic tests"""

    @pytest.mark.asyncio
    async def test_2_1_unit_120_P0_given_existing_call_when_ended_then_updates_status_and_duration(
        self,
    ):
        from services.vapi import handle_call_ended

        session = AsyncMock()
        row_mapping = CallFactory.build_completed(
            org_id="org_abc",
            vapi_call_id="vapi_123",
        )
        row_mapping["ended_at"] = datetime.now(timezone.utc)
        row_mapping["created_at"] = datetime.now(timezone.utc)
        row_mapping["updated_at"] = datetime.now(timezone.utc)

        mock_row = MagicMock()
        mock_row._mapping = row_mapping

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row

        with patch("services.vapi.set_tenant_context", new_callable=AsyncMock):
            session.execute = AsyncMock(return_value=mock_result)
            result = await handle_call_ended(
                session,
                "vapi_123",
                org_id="org_abc",
                duration=120,
                recording_url="https://recording.url",
            )

        assert result.status == "completed"
        assert result.duration == 120

    @pytest.mark.asyncio
    async def test_2_1_unit_121_P1_given_no_call_found_when_ended_then_raises_value_error(
        self,
    ):
        from services.vapi import handle_call_ended

        session = AsyncMock()
        mock_empty = MagicMock()
        mock_empty.first.return_value = None
        session.execute = AsyncMock(return_value=mock_empty)

        with (
            patch("services.vapi.set_tenant_context", new_callable=AsyncMock),
            pytest.raises(ValueError, match="Call not found"),
        ):
            await handle_call_ended(
                session,
                "nonexistent_vapi_id",
                org_id="org_abc",
            )
