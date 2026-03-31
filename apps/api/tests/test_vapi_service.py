"""
Story 2.1: Vapi Telephony Bridge & Webhook Integration
Unit Tests for Vapi Service (business logic)

Test ID Format: [2.1-UNIT-XXX]
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


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
            patch(
                "services.vapi._call_service",
            ) as mock_svc,
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


class TestHandleCallStarted:
    """[2.1-UNIT-110..113] handle_call_started business logic tests"""

    @pytest.mark.asyncio
    async def test_2_1_unit_110_P0_given_upsert_when_started_then_returns_call(
        self,
    ):
        from services.vapi import handle_call_started

        session = AsyncMock()

        row_mapping = {
            "id": 1,
            "org_id": "org_abc",
            "vapi_call_id": "vapi_123",
            "lead_id": None,
            "agent_id": None,
            "campaign_id": None,
            "status": "in_progress",
            "duration": None,
            "recording_url": None,
            "phone_number": "+1234567890",
            "transcript": None,
            "ended_at": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "soft_delete": False,
        }
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: row_mapping[key]
        mock_row._mapping = row_mapping

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row

        with (
            patch("services.vapi.set_tenant_context", new_callable=AsyncMock),
        ):
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

        row_mapping = {
            "id": 5,
            "org_id": "org_abc",
            "vapi_call_id": "vapi_new",
            "lead_id": None,
            "agent_id": None,
            "campaign_id": None,
            "status": "in_progress",
            "duration": None,
            "recording_url": None,
            "phone_number": "",
            "transcript": None,
            "ended_at": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "soft_delete": False,
        }
        mock_row = MagicMock()
        mock_row._mapping = row_mapping

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row

        with (
            patch("services.vapi.set_tenant_context", new_callable=AsyncMock),
        ):
            session.execute = AsyncMock(return_value=mock_result)
            result = await handle_call_started(
                session,
                "vapi_new",
                "org_abc",
                metadata={"lead_id": "not_a_number", "agent_id": "abc"},
            )

        assert result.status == "in_progress"
        assert result.vapi_call_id == "vapi_new"


class TestHandleCallEnded:
    """[2.1-UNIT-120..122] handle_call_ended business logic tests"""

    @pytest.mark.asyncio
    async def test_2_1_unit_120_P0_given_existing_call_when_ended_then_updates_status_and_duration(
        self,
    ):
        from services.vapi import handle_call_ended

        session = AsyncMock()
        row_mapping = {
            "id": 1,
            "org_id": "org_abc",
            "vapi_call_id": "vapi_123",
            "lead_id": None,
            "agent_id": None,
            "campaign_id": None,
            "status": "completed",
            "duration": 120,
            "recording_url": "https://recording.url",
            "phone_number": "+1234567890",
            "transcript": None,
            "ended_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "soft_delete": False,
        }
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


class TestHandleCallFailed:
    """[2.1-UNIT-130..132] handle_call_failed business logic tests"""

    @pytest.mark.asyncio
    async def test_2_1_unit_130_P0_given_existing_call_when_failed_then_updates_status(
        self,
    ):
        from services.vapi import handle_call_failed

        session = AsyncMock()
        row_mapping = {
            "id": 1,
            "org_id": "org_abc",
            "vapi_call_id": "vapi_123",
            "lead_id": None,
            "agent_id": None,
            "campaign_id": None,
            "status": "failed",
            "duration": None,
            "recording_url": None,
            "phone_number": "+1234567890",
            "transcript": "[error] Carrier rejected",
            "ended_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "soft_delete": False,
        }
        mock_row = MagicMock()
        mock_row._mapping = row_mapping

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row

        with patch("services.vapi.set_tenant_context", new_callable=AsyncMock):
            session.execute = AsyncMock(return_value=mock_result)
            result = await handle_call_failed(
                session,
                "vapi_123",
                org_id="org_abc",
                error_message="Carrier rejected",
            )

        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_2_1_unit_131_P1_given_no_call_found_when_failed_then_raises_value_error(
        self,
    ):
        from services.vapi import handle_call_failed

        session = AsyncMock()
        mock_empty = MagicMock()
        mock_empty.first.return_value = None
        session.execute = AsyncMock(return_value=mock_empty)

        with (
            patch("services.vapi.set_tenant_context", new_callable=AsyncMock),
            pytest.raises(ValueError, match="Call not found"),
        ):
            await handle_call_failed(
                session,
                "nonexistent_vapi_id",
                org_id="org_abc",
            )
