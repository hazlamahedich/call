"""
Story 2.1: Vapi Telephony Bridge & Webhook Integration
Unit Tests for trigger_outbound_call (business logic)

Test ID Format: [2.1-UNIT-XXX]
"""

import pytest
from unittest.mock import AsyncMock, patch

from tests.support.factories import CallFactory


class TestTriggerOutboundCall:
    """[2.1-UNIT-100..106] trigger_outbound_call business logic tests"""

    @pytest.mark.asyncio
    async def test_2_1_unit_100_P0_given_no_assistant_id_when_trigger_then_raises_not_configured(
        self,
    ):
        from services.vapi import trigger_outbound_call

        session = AsyncMock()
        with pytest.raises(ValueError, match="VAPI_NOT_CONFIGURED"):
            await trigger_outbound_call(
                session,
                org_id="org_123",
                phone_number="+1234567890",
                assistant_id=None,
            )

    @pytest.mark.asyncio
    async def test_2_1_unit_101_P0_given_valid_input_when_trigger_then_creates_call_and_returns(
        self,
    ):
        from services.vapi import trigger_outbound_call
        from models.call import Call

        session = AsyncMock()
        created_call = Call.model_validate(
            {
                "vapiCallId": "placeholder-uuid",
                "phoneNumber": "+1234567890",
                "status": "pending",
            }
        )
        created_call.id = 1

        with (
            patch("services.vapi.set_tenant_context", new_callable=AsyncMock),
            patch("services.vapi._call_service") as mock_svc,
            patch(
                "services.vapi.initiate_call",
                new_callable=AsyncMock,
                return_value={"id": "call_vapi_123"},
            ) as mock_initiate,
            patch("services.vapi.record_usage", new_callable=AsyncMock),
        ):
            mock_svc.create = AsyncMock(return_value=created_call)
            session.execute = AsyncMock()
            session.flush = AsyncMock()

            result = await trigger_outbound_call(
                session,
                org_id="org_abc",
                phone_number="+1234567890",
                assistant_id="asst_456",
                lead_id=10,
                agent_id=20,
            )

        assert result.vapi_call_id == "call_vapi_123"
        mock_initiate.assert_called_once()

    @pytest.mark.asyncio
    async def test_2_1_unit_102_P0_given_api_failure_when_trigger_then_marks_call_failed(
        self,
    ):
        from services.vapi import trigger_outbound_call
        from models.call import Call

        session = AsyncMock()
        created_call = Call.model_validate(
            {
                "vapiCallId": "placeholder-uuid",
                "phoneNumber": "+1234567890",
                "status": "pending",
            }
        )
        created_call.id = 2

        with (
            patch("services.vapi.set_tenant_context", new_callable=AsyncMock),
            patch("services.vapi._call_service") as mock_svc,
            patch(
                "services.vapi.initiate_call",
                new_callable=AsyncMock,
                side_effect=RuntimeError("API unreachable"),
            ),
        ):
            mock_svc.create = AsyncMock(return_value=created_call)
            session.execute = AsyncMock()
            session.flush = AsyncMock()

            with pytest.raises(RuntimeError, match="API unreachable"):
                await trigger_outbound_call(
                    session,
                    org_id="org_abc",
                    phone_number="+1234567890",
                    assistant_id="asst_456",
                )

        assert created_call.status == "failed"
