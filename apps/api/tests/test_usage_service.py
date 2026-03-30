"""
Story 1.7: Resource Guardrails - Usage Monitoring & Hard Caps
Unit Tests for Usage Service Functions

Test ID Format: [1.7-UNIT-XXX]
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.usage import (
    _compute_threshold,
    get_monthly_cap,
    get_org_plan,
    get_usage_summary,
    record_usage,
    check_usage_cap,
)


class TestComputeThresholdBoundaries:
    """[1.7-UNIT-067..072] _compute_threshold boundary edge cases"""

    def test_1_7_unit_067_seventy_nine_percent_is_ok(self):
        assert _compute_threshold(790, 1000) == "ok"

    def test_1_7_unit_068_eighty_percent_is_warning(self):
        assert _compute_threshold(800, 1000) == "warning"

    def test_1_7_unit_069_ninety_four_percent_is_warning(self):
        assert _compute_threshold(940, 1000) == "warning"

    def test_1_7_unit_070_ninety_five_percent_is_critical(self):
        assert _compute_threshold(950, 1000) == "critical"

    def test_1_7_unit_071_ninety_nine_percent_is_critical(self):
        assert _compute_threshold(990, 1000) == "critical"

    def test_1_7_unit_072_over_100_percent_is_exceeded(self):
        assert _compute_threshold(1001, 1000) == "exceeded"


class TestGetMonthlyCap:
    """[1.7-UNIT-073..076] get_monthly_cap service"""

    @pytest.mark.asyncio
    async def test_1_7_unit_073_returns_free_cap_by_default(self):
        cap = await get_monthly_cap("org_1")
        assert cap == 1000

    @pytest.mark.asyncio
    async def test_1_7_unit_074_returns_pro_cap(self):
        cap = await get_monthly_cap("org_1", plan="pro")
        assert cap == 25000

    @pytest.mark.asyncio
    async def test_1_7_unit_075_returns_enterprise_cap(self):
        cap = await get_monthly_cap("org_1", plan="enterprise")
        assert cap == 100000

    @pytest.mark.asyncio
    async def test_1_7_unit_076_returns_default_for_unknown_plan(self):
        cap = await get_monthly_cap("org_1", plan="nonexistent")
        assert cap == 1000


class TestGetOrgPlan:
    """[1.7-UNIT-077..079] get_org_plan service"""

    @pytest.mark.asyncio
    async def test_1_7_unit_077_returns_plan_from_db(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = "pro"
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.usage.set_tenant_context", new_callable=AsyncMock):
            plan = await get_org_plan(mock_session, "org_1")
        assert plan == "pro"

    @pytest.mark.asyncio
    async def test_1_7_unit_078_returns_free_when_no_row(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.usage.set_tenant_context", new_callable=AsyncMock):
            plan = await get_org_plan(mock_session, "org_1")
        assert plan == "free"

    @pytest.mark.asyncio
    async def test_1_7_unit_079_returns_free_for_unknown_plan(self):
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
    async def test_1_7_unit_080_returns_correct_summary(self):
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
    async def test_1_7_unit_081_handles_zero_cap(self):
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
    async def test_1_7_unit_082_rounds_percentage(self):
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


class TestRecordUsage:
    """[1.7-UNIT-083..085] record_usage service"""

    @pytest.mark.asyncio
    async def test_1_7_unit_083_creates_log_and_returns(self):
        from models.usage_log import UsageLog

        mock_session = AsyncMock()
        mock_log = UsageLog.model_validate(
            {
                "resourceType": "call",
                "resourceId": "call_001",
                "action": "call_initiated",
            }
        )
        mock_log.id = 1

        with (
            patch("services.usage.set_tenant_context", new_callable=AsyncMock),
            patch("services.usage._usage_service") as mock_svc,
        ):
            mock_svc.create = AsyncMock(return_value=mock_log)
            result = await record_usage(
                mock_session,
                "org_1",
                resource_type="call",
                resource_id="call_001",
                action="call_initiated",
            )

        assert result.resource_type == "call"
        assert result.action == "call_initiated"

    @pytest.mark.asyncio
    async def test_1_7_unit_084_passes_metadata(self):
        from models.usage_log import UsageLog

        mock_session = AsyncMock()
        captured_log = None
        mock_log = UsageLog.model_validate(
            {
                "resourceType": "call",
                "resourceId": "call_002",
                "action": "call_completed",
                "metadataJson": '{"duration": 120}',
            }
        )

        async def capture_create(session, log):
            nonlocal captured_log
            captured_log = log
            return mock_log

        with (
            patch("services.usage.set_tenant_context", new_callable=AsyncMock),
            patch("services.usage._usage_service") as mock_svc,
        ):
            mock_svc.create = AsyncMock(side_effect=capture_create)
            await record_usage(
                mock_session,
                "org_1",
                resource_type="call",
                resource_id="call_002",
                action="call_completed",
                metadata='{"duration": 120}',
            )

        assert captured_log is not None
        assert captured_log.metadata_json == '{"duration": 120}'

    @pytest.mark.asyncio
    async def test_1_7_unit_085_defaults_metadata_to_empty_json(self):
        from models.usage_log import UsageLog

        mock_session = AsyncMock()
        mock_log = UsageLog()

        with (
            patch("services.usage.set_tenant_context", new_callable=AsyncMock),
            patch("services.usage._usage_service") as mock_svc,
        ):
            mock_svc.create = AsyncMock(return_value=mock_log)
            await record_usage(
                mock_session,
                "org_1",
                resource_type="call",
                resource_id="call_003",
                action="call_initiated",
            )

        call_args = mock_svc.create.call_args
        passed_log = call_args[0][1]
        assert passed_log.metadata_json == "{}"


class TestCheckUsageCapService:
    """[1.7-UNIT-086..088] check_usage_cap service"""

    @pytest.mark.asyncio
    async def test_1_7_unit_086_returns_exceeded_when_over(self):
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
    async def test_1_7_unit_087_uses_provided_plan(self):
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
    async def test_1_7_unit_088_fetches_plan_when_not_provided(self):
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
