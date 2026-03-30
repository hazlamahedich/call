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
    async def test_1_7_unit_061_returns_none_when_no_org_id(self):
        request = MagicMock()
        request.state.org_id = None
        session = AsyncMock()

        result = await check_call_cap(request, session)
        assert result is None

    @pytest.mark.asyncio
    async def test_1_7_unit_062_returns_none_on_db_error(self):
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
    async def test_1_7_unit_063_raises_403_when_exceeded(self):
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
    async def test_1_7_unit_064_returns_none_when_ok(self):
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
    async def test_1_7_unit_065_returns_none_when_warning(self):
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
    async def test_1_7_unit_066_returns_none_when_critical(self):
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
