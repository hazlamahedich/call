"""
Story 1.7: Resource Guardrails - Usage Monitoring & Hard Caps
Unit Tests for Usage Service Functions

Test ID Format: [1.7-UNIT-XXX]
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.usage import (
    get_monthly_cap,
    get_tenant_cap_override,
    get_org_plan,
    get_usage_summary,
    check_usage_cap,
)


class TestGetMonthlyCap:
    """[1.7-UNIT-073..076] get_monthly_cap service"""

    @pytest.mark.asyncio
    async def test_1_7_unit_073_P1_given_default_plan_when_get_monthly_cap_then_returns_free_cap(
        self,
    ):
        mock_session = AsyncMock()
        with patch(
            "services.usage.get_tenant_cap_override",
            new_callable=AsyncMock,
            return_value=None,
        ):
            cap = await get_monthly_cap(mock_session, "org_1")
        assert cap == 1000

    @pytest.mark.asyncio
    async def test_1_7_unit_074_P1_given_pro_plan_when_get_monthly_cap_then_returns_pro_cap(
        self,
    ):
        mock_session = AsyncMock()
        with patch(
            "services.usage.get_tenant_cap_override",
            new_callable=AsyncMock,
            return_value=None,
        ):
            cap = await get_monthly_cap(mock_session, "org_1", plan="pro")
        assert cap == 25000

    @pytest.mark.asyncio
    async def test_1_7_unit_075_P2_given_enterprise_plan_when_get_monthly_cap_then_returns_enterprise_cap(
        self,
    ):
        mock_session = AsyncMock()
        with patch(
            "services.usage.get_tenant_cap_override",
            new_callable=AsyncMock,
            return_value=None,
        ):
            cap = await get_monthly_cap(mock_session, "org_1", plan="enterprise")
        assert cap == 100000

    @pytest.mark.asyncio
    async def test_1_7_unit_076_P1_given_unknown_plan_when_get_monthly_cap_then_returns_default_cap(
        self,
    ):
        mock_session = AsyncMock()
        with patch(
            "services.usage.get_tenant_cap_override",
            new_callable=AsyncMock,
            return_value=None,
        ):
            cap = await get_monthly_cap(mock_session, "org_1", plan="nonexistent")
        assert cap == 1000

    @pytest.mark.asyncio
    async def test_1_7_unit_076b_P0_given_tenant_override_when_get_monthly_cap_then_returns_override(
        self,
    ):
        mock_session = AsyncMock()
        with patch(
            "services.usage.get_tenant_cap_override",
            new_callable=AsyncMock,
            return_value=50000,
        ):
            cap = await get_monthly_cap(mock_session, "org_1", plan="free")
        assert cap == 50000


class TestGetOrgPlan:
    """[1.7-UNIT-077..079] get_org_plan service"""

    @pytest.mark.asyncio
    async def test_1_7_unit_077_P1_given_plan_in_db_when_get_org_plan_then_returns_plan(
        self,
    ):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = "pro"
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.usage.set_tenant_context", new_callable=AsyncMock):
            plan = await get_org_plan(mock_session, "org_1")
        assert plan == "pro"

    @pytest.mark.asyncio
    async def test_1_7_unit_078_P1_given_no_plan_row_when_get_org_plan_then_returns_free(
        self,
    ):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.usage.set_tenant_context", new_callable=AsyncMock):
            plan = await get_org_plan(mock_session, "org_1")
        assert plan == "free"

    @pytest.mark.asyncio
    async def test_1_7_unit_079_P1_given_unknown_plan_when_get_org_plan_then_returns_free(
        self,
    ):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = "starter"
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.usage.set_tenant_context", new_callable=AsyncMock):
            plan = await get_org_plan(mock_session, "org_1")
        assert plan == "free"


class TestGetUsageSummary:
    """[1.7-UNIT-080..082] get_usage_summary service"""

    @pytest.mark.asyncio
    async def test_1_7_unit_080_P0_given_pro_plan_usage_when_get_summary_then_returns_correct_values(
        self,
    ):
        mock_session = AsyncMock()

        with (
            patch("services.usage.set_tenant_context", new_callable=AsyncMock),
            patch(
                "services.usage.get_org_plan",
                new_callable=AsyncMock,
                return_value="pro",
            ),
            patch(
                "services.usage.get_monthly_usage",
                new_callable=AsyncMock,
                return_value=500,
            ),
            patch(
                "services.usage.get_monthly_cap",
                new_callable=AsyncMock,
                return_value=25000,
            ),
        ):
            summary = await get_usage_summary(mock_session, "org_1")

        assert summary["used"] == 500
        assert summary["cap"] == 25000
        assert summary["percentage"] == 2.0
        assert summary["plan"] == "pro"
        assert summary["threshold"] == "ok"

    @pytest.mark.asyncio
    async def test_1_7_unit_081_P1_given_zero_cap_when_get_summary_then_handles_gracefully(
        self,
    ):
        mock_session = AsyncMock()

        with (
            patch("services.usage.set_tenant_context", new_callable=AsyncMock),
            patch(
                "services.usage.get_org_plan",
                new_callable=AsyncMock,
                return_value="free",
            ),
            patch(
                "services.usage.get_monthly_usage",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "services.usage.get_monthly_cap",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            summary = await get_usage_summary(mock_session, "org_1")

        assert summary["percentage"] == 0.0
        assert summary["threshold"] == "exceeded"

    @pytest.mark.asyncio
    async def test_1_7_unit_082_P1_given_333_of_1000_when_get_summary_then_rounds_percentage(
        self,
    ):
        mock_session = AsyncMock()

        with (
            patch("services.usage.set_tenant_context", new_callable=AsyncMock),
            patch(
                "services.usage.get_org_plan",
                new_callable=AsyncMock,
                return_value="free",
            ),
            patch(
                "services.usage.get_monthly_usage",
                new_callable=AsyncMock,
                return_value=333,
            ),
            patch(
                "services.usage.get_monthly_cap",
                new_callable=AsyncMock,
                return_value=1000,
            ),
        ):
            summary = await get_usage_summary(mock_session, "org_1")

        assert summary["percentage"] == 33.3


class TestCheckUsageCapService:
    """[1.7-UNIT-086..088] check_usage_cap service"""

    @pytest.mark.asyncio
    async def test_1_7_unit_086_P0_given_usage_over_cap_when_check_cap_then_returns_exceeded(
        self,
    ):
        mock_session = AsyncMock()

        with (
            patch("services.usage.set_tenant_context", new_callable=AsyncMock),
            patch(
                "services.usage.get_org_plan",
                new_callable=AsyncMock,
                return_value="free",
            ),
            patch(
                "services.usage.get_monthly_usage",
                new_callable=AsyncMock,
                return_value=1001,
            ),
            patch(
                "services.usage.get_monthly_cap",
                new_callable=AsyncMock,
                return_value=1000,
            ),
        ):
            result = await check_usage_cap(mock_session, "org_1")
        assert result == "exceeded"

    @pytest.mark.asyncio
    async def test_1_7_unit_087_P0_given_provided_plan_when_check_cap_then_uses_provided_plan(
        self,
    ):
        mock_session = AsyncMock()

        with (
            patch("services.usage.set_tenant_context", new_callable=AsyncMock),
            patch(
                "services.usage.get_monthly_usage",
                new_callable=AsyncMock,
                return_value=500,
            ),
            patch(
                "services.usage.get_monthly_cap",
                new_callable=AsyncMock,
                return_value=25000,
            ),
        ):
            result = await check_usage_cap(mock_session, "org_1", plan="pro")
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_1_7_unit_088_P2_given_no_plan_provided_when_check_cap_then_fetches_plan(
        self,
    ):
        mock_session = AsyncMock()

        with (
            patch("services.usage.set_tenant_context", new_callable=AsyncMock),
            patch(
                "services.usage.get_org_plan",
                new_callable=AsyncMock,
                return_value="free",
            ),
            patch(
                "services.usage.get_monthly_usage",
                new_callable=AsyncMock,
                return_value=800,
            ),
            patch(
                "services.usage.get_monthly_cap",
                new_callable=AsyncMock,
                return_value=1000,
            ),
        ):
            result = await check_usage_cap(mock_session, "org_1")
        assert result == "warning"
