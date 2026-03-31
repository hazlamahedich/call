"""
Story 1.7: Resource Guardrails - Usage Monitoring & Hard Caps
Unit Tests for record_usage Service Function

Test ID Format: [1.7-UNIT-XXX]
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestRecordUsage:
    """[1.7-UNIT-083..085] record_usage service"""

    @pytest.mark.asyncio
    async def test_1_7_unit_083_P1_given_valid_input_when_record_usage_then_creates_log_and_returns(
        self,
    ):
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
    async def test_1_7_unit_084_P1_given_metadata_when_record_usage_then_passes_metadata(
        self,
    ):
        from models.usage_log import UsageLog

        mock_session = AsyncMock()
        captured_log = None
        mock_log = UsageLog.model_validate(
            {
                "resourceType": "call",
                "resourceId": "call_002",
                "action": "call_completed",
                "metadataJson": {"duration": 120},
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
        assert captured_log.metadata_json == {"duration": 120}

    @pytest.mark.asyncio
    async def test_1_7_unit_085_P1_given_no_metadata_when_record_usage_then_defaults_to_empty_json(
        self,
    ):
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
        assert passed_log.metadata_json == {}


from services.usage import record_usage
