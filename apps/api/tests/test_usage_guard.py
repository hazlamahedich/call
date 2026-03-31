"""
Story 1.7: Resource Guardrails - Usage Monitoring & Hard Caps
Unit Tests for Usage Guard Middleware

Test ID Format: [1.7-UNIT-XXX]
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from middleware.usage_guard import check_call_cap


class TestCheckCallCap:
    """[1.7-UNIT-061..066] Usage guard middleware unit tests"""

    @pytest.mark.asyncio
    async def test_1_7_unit_061_P1_given_no_org_id_when_check_call_cap_then_returns_none(
        self,
    ):
        request = MagicMock()
        request.state.org_id = None
        session = AsyncMock()

        result = await check_call_cap(request, session)
        assert result is None

    @pytest.mark.asyncio
    async def test_1_7_unit_062_P1_given_db_error_when_check_call_cap_then_returns_none(
        self,
    ):
        request = MagicMock()
        request.state.org_id = "org_123"
        session = AsyncMock()

        with (
            patch(
                "middleware.usage_guard.set_tenant_context",
                new_callable=AsyncMock,
            ),
            patch(
                "middleware.usage_guard.check_usage_cap",
                new_callable=AsyncMock,
                side_effect=Exception("DB connection lost"),
            ),
        ):
            result = await check_call_cap(request, session)
            assert result is None

    @pytest.mark.asyncio
    async def test_1_7_unit_063_P0_given_exceeded_cap_when_check_call_cap_then_raises_403(
        self,
    ):
        request = MagicMock()
        request.state.org_id = "org_123"
        session = AsyncMock()

        with (
            patch(
                "middleware.usage_guard.set_tenant_context",
                new_callable=AsyncMock,
            ),
            patch(
                "middleware.usage_guard.check_usage_cap",
                new_callable=AsyncMock,
                return_value="exceeded",
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await check_call_cap(request, session)

            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["code"] == "USAGE_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_1_7_unit_064_P0_given_ok_status_when_check_call_cap_then_returns_none(
        self,
    ):
        request = MagicMock()
        request.state.org_id = "org_123"
        session = AsyncMock()

        with (
            patch(
                "middleware.usage_guard.set_tenant_context",
                new_callable=AsyncMock,
            ),
            patch(
                "middleware.usage_guard.check_usage_cap",
                new_callable=AsyncMock,
                return_value="ok",
            ),
        ):
            result = await check_call_cap(request, session)
            assert result is None

    @pytest.mark.asyncio
    async def test_1_7_unit_065_P1_given_warning_status_when_check_call_cap_then_returns_none(
        self,
    ):
        request = MagicMock()
        request.state.org_id = "org_123"
        session = AsyncMock()

        with (
            patch(
                "middleware.usage_guard.set_tenant_context",
                new_callable=AsyncMock,
            ),
            patch(
                "middleware.usage_guard.check_usage_cap",
                new_callable=AsyncMock,
                return_value="warning",
            ),
        ):
            result = await check_call_cap(request, session)
            assert result is None

    @pytest.mark.asyncio
    async def test_1_7_unit_066_P1_given_critical_status_when_check_call_cap_then_returns_none(
        self,
    ):
        request = MagicMock()
        request.state.org_id = "org_123"
        session = AsyncMock()

        with (
            patch(
                "middleware.usage_guard.set_tenant_context",
                new_callable=AsyncMock,
            ),
            patch(
                "middleware.usage_guard.check_usage_cap",
                new_callable=AsyncMock,
                return_value="critical",
            ),
        ):
            result = await check_call_cap(request, session)
            assert result is None
