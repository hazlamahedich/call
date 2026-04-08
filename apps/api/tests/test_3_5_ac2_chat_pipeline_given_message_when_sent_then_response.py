"""Story 3.5 AC2: Chat Pipeline (send_chat_message).

Tests the full chat pipeline: session lookup, tenant verification,
expiry enforcement, turn persistence, variable injection, RAG generation,
source attribution, and response assembly.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from conftest_3_5 import (
    TEST_ORG,
    TEST_ORG_B,
    mock_session,
    lab_service,
    make_active_row,
    make_raw_chunk,
    mock_gen_result,
    mock_gen_service,
    chat_pipeline_patches,
)
from services.script_lab import ScriptLabService


def _setup_session(mock_session, row, added_instances=None):
    mock_result = MagicMock()
    mock_result.fetchone.return_value = row
    mock_session.execute = AsyncMock(return_value=mock_result)
    if added_instances is not None:
        mock_session.add = MagicMock(side_effect=lambda i: added_instances.append(i))
    else:
        mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()


@pytest.mark.asyncio
class TestAC2ChatPipeline:
    @pytest.mark.p0
    async def test_3_5_050_given_active_session_when_chat_sent_then_response_returned(
        self, mock_session, lab_service
    ):
        _setup_session(mock_session, make_active_row(turn_count=0))

        async with chat_pipeline_patches(mock_gen_result()):
            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Hi there"
            )

        assert result.response_text == "AI response"
        assert result.turn_number == 1
        assert result.grounding_confidence == 0.85
        assert result.low_confidence_warning is False

    @pytest.mark.p0
    async def test_3_5_051_given_chat_when_inspecting_turns_then_user_and_assistant_persisted(
        self, mock_session, lab_service
    ):
        added_instances = []
        _setup_session(mock_session, make_active_row(turn_count=2), added_instances)

        async with chat_pipeline_patches(mock_gen_result()):
            await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Test message"
            )

        assert len(added_instances) == 2
        assert added_instances[0].role == "user"
        assert added_instances[0].content == "Test message"
        assert added_instances[1].role == "assistant"
        assert added_instances[1].content == "AI response"

    @pytest.mark.p0
    async def test_3_5_052_given_nonexistent_session_when_chat_then_404(
        self, mock_session, lab_service
    ):
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
            pytest.raises(HTTPException) as exc_info,
        ):
            await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=999, message="Hi"
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"]["code"] == "session_not_found"

    @pytest.mark.p0
    async def test_3_5_053_given_cross_tenant_session_when_chat_then_403(
        self, mock_session, lab_service
    ):
        mock_result = MagicMock()
        mock_result.fetchone.return_value = make_active_row(org_id=TEST_ORG_B)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
            pytest.raises(HTTPException) as exc_info,
        ):
            await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Hi"
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"]["code"] == "NAMESPACE_VIOLATION"

    @pytest.mark.p0
    async def test_3_5_054_given_low_confidence_response_when_chat_then_warning_true(
        self, mock_session, lab_service
    ):
        _setup_session(mock_session, make_active_row(turn_count=0))

        async with chat_pipeline_patches(mock_gen_result(confidence=0.3)):
            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Low confidence test"
            )

        assert result.low_confidence_warning is True
        assert result.grounding_confidence == 0.3

    @pytest.mark.p1
    async def test_3_5_055_given_pipeline_failure_when_chat_then_500(
        self, mock_session, lab_service
    ):
        _setup_session(mock_session, make_active_row(turn_count=0))
        failing_gen = AsyncMock()
        failing_gen.generate_response.side_effect = RuntimeError("LLM down")

        async with chat_pipeline_patches(gen_service_override=failing_gen):
            with pytest.raises(HTTPException) as exc_info:
                await lab_service.send_chat_message(
                    org_id=TEST_ORG, session_id=1, message="Trigger error"
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error"]["code"] == "generation_failed"

    @pytest.mark.p1
    async def test_3_5_056_given_http_exception_in_pipeline_when_chat_then_propagated(
        self, mock_session, lab_service
    ):
        _setup_session(mock_session, make_active_row(turn_count=0))
        failing_gen = AsyncMock()
        failing_gen.generate_response.side_effect = HTTPException(
            status_code=422, detail={"error": {"code": "test_error"}}
        )

        async with chat_pipeline_patches(gen_service_override=failing_gen):
            with pytest.raises(HTTPException) as exc_info:
                await lab_service.send_chat_message(
                    org_id=TEST_ORG, session_id=1, message="Propagate HTTP"
                )

        assert exc_info.value.status_code == 422

    @pytest.mark.p1
    async def test_3_5_057_given_variable_injection_enabled_when_chat_then_template_rendered(
        self, mock_session, lab_service
    ):
        _setup_session(mock_session, make_active_row(turn_count=0, lead_id=5))

        mock_render_result = MagicMock()
        mock_render_result.rendered_text = "Hello John Doe, welcome!"

        with (
            patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
            patch("services.script_lab.settings") as mock_settings,
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ) as mock_load_script,
            patch(
                "services.script_lab.load_lead_for_context", new_callable=AsyncMock
            ) as mock_load_lead,
            patch(
                "services.variable_injection.VariableInjectionService"
            ) as mock_vi_cls,
            patch("services.script_generation.ScriptGenerationService") as mock_gen_cls,
        ):
            mock_settings.SCRIPT_LAB_MAX_TURNS = 50
            mock_settings.VARIABLE_INJECTION_ENABLED = True
            mock_script = MagicMock()
            mock_script.content = "Hello {{name}}"
            mock_load_script.return_value = mock_script
            mock_lead = MagicMock()
            mock_load_lead.return_value = mock_lead
            mock_vi_instance = AsyncMock()
            mock_vi_instance.render_template.return_value = mock_render_result
            mock_vi_cls.return_value = mock_vi_instance
            mock_gen_cls.return_value = mock_gen_service(mock_gen_result())

            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Hi"
            )

        mock_vi_instance.render_template.assert_awaited_once()
        assert result.response_text == "AI response"

    @pytest.mark.p1
    async def test_3_5_058_given_scenario_overlay_without_lead_when_chat_then_overlay_used_as_lead(
        self, mock_session, lab_service
    ):
        _setup_session(
            mock_session,
            make_active_row(
                turn_count=0,
                lead_id=None,
                scenario_overlay={"company": "Acme Corp"},
            ),
        )

        mock_render_result = MagicMock()
        mock_render_result.rendered_text = "Rendered"

        with (
            patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
            patch("services.script_lab.settings") as mock_settings,
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ) as mock_load_script,
            patch(
                "services.variable_injection.VariableInjectionService"
            ) as mock_vi_cls,
            patch("services.script_generation.ScriptGenerationService") as mock_gen_cls,
        ):
            mock_settings.SCRIPT_LAB_MAX_TURNS = 50
            mock_settings.VARIABLE_INJECTION_ENABLED = True
            mock_script = MagicMock()
            mock_script.content = "Template"
            mock_load_script.return_value = mock_script
            mock_vi_instance = AsyncMock()
            mock_vi_instance.render_template.return_value = mock_render_result
            mock_vi_cls.return_value = mock_vi_instance
            mock_gen_cls.return_value = mock_gen_service(mock_gen_result())

            await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Overlay test"
            )

        call_args = mock_vi_instance.render_template.call_args
        lead_arg = call_args.kwargs["lead"]
        assert lead_arg == {"company": "Acme Corp"}

    @pytest.mark.p1
    async def test_3_5_059_given_assistant_turn_persist_failure_when_chat_then_response_still_returned(
        self, mock_session, lab_service
    ):
        active_row = make_active_row(turn_count=0)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = active_row
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()

        flush_call_count = 0

        async def mock_flush():
            nonlocal flush_call_count
            flush_call_count += 1
            if flush_call_count == 2:
                raise RuntimeError("DB connection lost")

        mock_session.flush = AsyncMock(side_effect=mock_flush)

        async with chat_pipeline_patches(mock_gen_result()):
            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Test"
            )

        assert result.response_text == "AI response"
        assert flush_call_count >= 2

    @pytest.mark.p2
    async def test_3_5_060_given_source_attributions_in_chat_when_inspecting_then_chunk_id_present(
        self, mock_session, lab_service
    ):
        _setup_session(mock_session, make_active_row(turn_count=0))

        chunks = [
            make_raw_chunk(chunk_id=100, similarity=0.9),
            make_raw_chunk(chunk_id=101, similarity=0.7),
        ]

        async with chat_pipeline_patches(mock_gen_result(chunks=chunks)):
            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Attribution test"
            )

        assert len(result.source_attributions) == 2
        assert result.source_attributions[0].chunk_id == 100
        assert result.source_attributions[1].chunk_id == 101
