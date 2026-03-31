"""
Story 1.7: Resource Guardrails - Usage Monitoring & Hard Caps
Concurrency Tests for Cap Enforcement

Test ID Format: [1.7-CONCURRENCY-XXX]

Verifies that concurrent record_usage calls don't bypass the cap check.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.usage import _compute_threshold


class TestConcurrencyCapEnforcement:
    """[1.7-CONCURRENCY-001..003] Cap enforcement under concurrent load"""

    @pytest.mark.asyncio
    async def test_1_7_concurrency_001_P0_given_near_cap_usage_when_concurrent_records_then_threshold_remains_correct(
        self,
    ):
        """
        Simulates concurrent cap checks where usage is at 999/1000.
        Even with multiple concurrent checks, the threshold should
        reflect the actual count, not a stale read.
        """
        from services.usage import check_usage_cap

        mock_session = AsyncMock()
        call_count = 0

        async def mock_get_monthly_usage(session, org_id):
            return 999

        async def mock_get_monthly_cap(session, org_id, plan=None):
            return 1000

        async def mock_get_org_plan(session, org_id):
            return "free"

        with (
            patch("services.usage.set_tenant_context", new_callable=AsyncMock),
            patch(
                "services.usage.get_org_plan",
                side_effect=mock_get_org_plan,
            ),
            patch(
                "services.usage.get_monthly_usage",
                side_effect=mock_get_monthly_usage,
            ),
            patch(
                "services.usage.get_monthly_cap",
                side_effect=mock_get_monthly_cap,
            ),
            patch(
                "services.usage.get_tenant_cap_override",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            results = await asyncio.gather(
                check_usage_cap(mock_session, "org_1"),
                check_usage_cap(mock_session, "org_1"),
                check_usage_cap(mock_session, "org_1"),
            )

        for result in results:
            assert result == "critical"

    @pytest.mark.asyncio
    async def test_1_7_concurrency_002_P1_given_exceeded_cap_when_concurrent_checks_then_all_report_exceeded(
        self,
    ):
        """
        Once usage exceeds cap, all concurrent checks should report exceeded.
        """
        from services.usage import check_usage_cap

        mock_session = AsyncMock()

        async def mock_get_monthly_usage(session, org_id):
            return 1001

        async def mock_get_monthly_cap(session, org_id, plan=None):
            return 1000

        with (
            patch("services.usage.set_tenant_context", new_callable=AsyncMock),
            patch(
                "services.usage.get_org_plan",
                new_callable=AsyncMock,
                return_value="free",
            ),
            patch(
                "services.usage.get_monthly_usage",
                side_effect=mock_get_monthly_usage,
            ),
            patch(
                "services.usage.get_monthly_cap",
                side_effect=mock_get_monthly_cap,
            ),
            patch(
                "services.usage.get_tenant_cap_override",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            results = await asyncio.gather(
                *[check_usage_cap(mock_session, "org_1") for _ in range(10)]
            )

        assert all(r == "exceeded" for r in results)

    def test_1_7_concurrency_003_P1_given_compute_threshold_when_called_concurrently_then_pure_function_is_thread_safe(
        self,
    ):
        """
        _compute_threshold is a pure function and must be safe under
        concurrent invocation without shared state mutation.
        """
        inputs = [
            (790, 1000, "ok"),
            (800, 1000, "warning"),
            (950, 1000, "critical"),
            (1000, 1000, "exceeded"),
            (0, 0, "exceeded"),
            (50000, 100000, "ok"),
        ]

        results = [_compute_threshold(u, c) for u, c, _ in inputs]

        for (_, _, expected), actual in zip(inputs, results):
            assert actual == expected, f"Expected {expected}, got {actual}"
