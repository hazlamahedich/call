"""
Story 2.1: Vapi Telephony Bridge & Webhook Integration
Unit Tests for handle_call_started (business logic)

Test ID Format: [2.1-UNIT-XXX]
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from tests.support.factories import CallFactory


class TestHandleCallStarted:
    """[2.1-UNIT-110..113] handle_call_started business logic tests"""

    @pytest.mark.asyncio
    async def test_2_1_unit_110_P0_given_upsert_when_started_then_returns_call(
        self,
    ):
        from services.vapi import handle_call_started

        session = AsyncMock()
        row_mapping = CallFactory.build_in_progress(
            org_id="org_abc",
            vapi_call_id="vapi_123",
        )
        row_mapping["created_at"] = datetime.now(timezone.utc)
        row_mapping["updated_at"] = datetime.now(timezone.utc)

        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: row_mapping[key]
        mock_row._mapping = row_mapping

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row

        with patch("services.vapi.set_tenant_context", new_callable=AsyncMock):
            session.execute = AsyncMock(return_value=mock_result)
            result = await handle_call_started(
                session,
                "vapi_123",
                "org_abc",
                phone_number="+1234567890",
            )

        assert result.status == "in_progress"

    @pytest.mark.asyncio
    async def test_2_1_unit_111_P0_given_non_numeric_metadata_when_started_then_ignores_bad_values(
        self,
    ):
        from services.vapi import handle_call_started

        session = AsyncMock()
        row_mapping = CallFactory.build_in_progress(
            org_id="org_abc",
            vapi_call_id="vapi_new",
            phone_number="",
        )
        row_mapping["created_at"] = datetime.now(timezone.utc)
        row_mapping["updated_at"] = datetime.now(timezone.utc)

        mock_row = MagicMock()
        mock_row._mapping = row_mapping

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row

        with patch("services.vapi.set_tenant_context", new_callable=AsyncMock):
            session.execute = AsyncMock(return_value=mock_result)
            result = await handle_call_started(
                session,
                "vapi_new",
                "org_abc",
                metadata={"lead_id": "not_a_number", "agent_id": "abc"},
            )

        assert result.status == "in_progress"
        assert result.vapi_call_id == "vapi_new"
