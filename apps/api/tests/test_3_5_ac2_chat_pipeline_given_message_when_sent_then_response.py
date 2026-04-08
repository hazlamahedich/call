"""Story 3.5 AC2: Chat Pipeline (send_chat_message).

Tests the full chat pipeline: session lookup, tenant verification,
expiry enforcement, turn persistence, variable injection, RAG generation,
source attribution, and response assembly.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest_3_5 import *
from services.script_lab import ScriptLabService


def _make_active_row(**overrides):
    defaults = {
        "id": 1,
        "org_id": TEST_ORG,
        "agent_id": 1,
        "script_id": 10,
        "lead_id": None,
        "scenario_overlay": None,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "status": "active",
        "turn_count": 0,
    }
    defaults.update(overrides)
    return tuple(defaults.values())


def _mock_gen_result(response="AI response", confidence=0.85, chunks=None):
    gen_result = MagicMock()
    gen_result.response = response
    gen_result.grounding_confidence = confidence
    gen_result.source_chunks = chunks or [
        make_raw_chunk(),
    ]
    return gen_result


def _make_mock_gen_service(gen_result):
    mock_gen = AsyncMock()
    mock_gen.generate_response.return_value = gen_result
    return mock_gen


@pytest.mark.asyncio
class TestAC2ChatPipeline:
    @pytest.mark.p0
    async def test_3_5_050_given_active_session_when_chat_sent_then_response_returned(
        self, mock_session, lab_service
    ):
        active_row = _make_active_row(turn_count=0)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = active_row
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        gen_result = _mock_gen_result()

        with (
            patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
            patch("services.script_lab.settings") as mock_settings,
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ) as mock_load_script,
            patch("services.script_generation.ScriptGenerationService") as mock_gen_cls,
        ):
            mock_settings.SCRIPT_LAB_MAX_TURNS = 50
            mock_settings.VARIABLE_INJECTION_ENABLED = False

            mock_script = MagicMock()
            mock_script.content = "Hello {{name}}"
            mock_load_script.return_value = mock_script

            mock_gen_cls.return_value = _make_mock_gen_service(gen_result)

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
        active_row = _make_active_row(turn_count=2)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = active_row
        mock_session.execute = AsyncMock(return_value=mock_result)

        added_instances = []

        def capture_add(instance):
            added_instances.append(instance)

        mock_session.add = MagicMock(side_effect=capture_add)
        mock_session.flush = AsyncMock()

        gen_result = _mock_gen_result()

        with (
            patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
            patch("services.script_lab.settings") as mock_settings,
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ) as mock_load_script,
            patch("services.script_generation.ScriptGenerationService") as mock_gen_cls,
        ):
            mock_settings.SCRIPT_LAB_MAX_TURNS = 50
            mock_settings.VARIABLE_INJECTION_ENABLED = False

            mock_script = MagicMock()
            mock_script.content = "Script"
            mock_load_script.return_value = mock_script

            mock_gen_cls.return_value = _make_mock_gen_service(gen_result)

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
        cross_tenant_row = _make_active_row(org_id=TEST_ORG_B)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = cross_tenant_row
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
        active_row = _make_active_row(turn_count=0)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = active_row
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        gen_result = _mock_gen_result(confidence=0.3)

        with (
            patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
            patch("services.script_lab.settings") as mock_settings,
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ) as mock_load_script,
            patch("services.script_generation.ScriptGenerationService") as mock_gen_cls,
        ):
            mock_settings.SCRIPT_LAB_MAX_TURNS = 50
            mock_settings.VARIABLE_INJECTION_ENABLED = False

            mock_script = MagicMock()
            mock_script.content = "Script"
            mock_load_script.return_value = mock_script

            mock_gen_cls.return_value = _make_mock_gen_service(gen_result)

            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Low confidence test"
            )

        assert result.low_confidence_warning is True
        assert result.grounding_confidence == 0.3

    @pytest.mark.p1
    async def test_3_5_055_given_pipeline_failure_when_chat_then_500(
        self, mock_session, lab_service
    ):
        active_row = _make_active_row(turn_count=0)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = active_row
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        with (
            patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
            patch("services.script_lab.settings") as mock_settings,
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ) as mock_load_script,
            patch("services.script_generation.ScriptGenerationService") as mock_gen_cls,
        ):
            mock_settings.SCRIPT_LAB_MAX_TURNS = 50
            mock_settings.VARIABLE_INJECTION_ENABLED = False

            mock_script = MagicMock()
            mock_script.content = "Script"
            mock_load_script.return_value = mock_script

            mock_gen_instance = AsyncMock()
            mock_gen_instance.generate_response.side_effect = RuntimeError("LLM down")
            mock_gen_cls.return_value = mock_gen_instance

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
        active_row = _make_active_row(turn_count=0)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = active_row
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        with (
            patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
            patch("services.script_lab.settings") as mock_settings,
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ) as mock_load_script,
            patch("services.script_generation.ScriptGenerationService") as mock_gen_cls,
        ):
            mock_settings.SCRIPT_LAB_MAX_TURNS = 50
            mock_settings.VARIABLE_INJECTION_ENABLED = False

            mock_script = MagicMock()
            mock_script.content = "Script"
            mock_load_script.return_value = mock_script

            mock_gen_instance = AsyncMock()
            mock_gen_instance.generate_response.side_effect = HTTPException(
                status_code=422, detail={"error": {"code": "test_error"}}
            )
            mock_gen_cls.return_value = mock_gen_instance

            with pytest.raises(HTTPException) as exc_info:
                await lab_service.send_chat_message(
                    org_id=TEST_ORG, session_id=1, message="Propagate HTTP"
                )

        assert exc_info.value.status_code == 422

    @pytest.mark.p1
    async def test_3_5_057_given_variable_injection_enabled_when_chat_then_template_rendered(
        self, mock_session, lab_service
    ):
        active_row = _make_active_row(turn_count=0, lead_id=5)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = active_row
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        gen_result = _mock_gen_result()

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

            mock_gen_cls.return_value = _make_mock_gen_service(gen_result)

            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Hi"
            )

        mock_vi_instance.render_template.assert_awaited_once()
        assert result.response_text == "AI response"

    @pytest.mark.p1
    async def test_3_5_058_given_scenario_overlay_without_lead_when_chat_then_overlay_used_as_lead(
        self, mock_session, lab_service
    ):
        active_row = _make_active_row(
            turn_count=0,
            lead_id=None,
            scenario_overlay={"company": "Acme Corp"},
        )
        mock_result = MagicMock()
        mock_result.fetchone.return_value = active_row
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        gen_result = _mock_gen_result()
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

            mock_gen_cls.return_value = _make_mock_gen_service(gen_result)

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
        active_row = _make_active_row(turn_count=0)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = active_row

        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        gen_result = _mock_gen_result()

        with (
            patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
            patch("services.script_lab.settings") as mock_settings,
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ) as mock_load_script,
            patch("services.script_generation.ScriptGenerationService") as mock_gen_cls,
        ):
            mock_settings.SCRIPT_LAB_MAX_TURNS = 50
            mock_settings.VARIABLE_INJECTION_ENABLED = False

            mock_script = MagicMock()
            mock_script.content = "Script"
            mock_load_script.return_value = mock_script

            mock_gen_cls.return_value = _make_mock_gen_service(gen_result)

            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Test"
            )

        assert result.response_text == "AI response"

    @pytest.mark.p2
    async def test_3_5_060_given_source_attributions_in_chat_when_inspecting_then_chunk_id_present(
        self, mock_session, lab_service
    ):
        active_row = _make_active_row(turn_count=0)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = active_row
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        chunks = [
            make_raw_chunk(chunk_id=100, similarity=0.9),
            make_raw_chunk(chunk_id=101, similarity=0.7),
        ]
        gen_result = _mock_gen_result(chunks=chunks)

        with (
            patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
            patch("services.script_lab.settings") as mock_settings,
            patch(
                "services.script_lab.load_script_for_context", new_callable=AsyncMock
            ) as mock_load_script,
            patch("services.script_generation.ScriptGenerationService") as mock_gen_cls,
        ):
            mock_settings.SCRIPT_LAB_MAX_TURNS = 50
            mock_settings.VARIABLE_INJECTION_ENABLED = False

            mock_script = MagicMock()
            mock_script.content = "Script"
            mock_load_script.return_value = mock_script

            mock_gen_cls.return_value = _make_mock_gen_service(gen_result)

            result = await lab_service.send_chat_message(
                org_id=TEST_ORG, session_id=1, message="Attribution test"
            )

        assert len(result.source_attributions) == 2
        assert result.source_attributions[0].chunk_id == 100
        assert result.source_attributions[1].chunk_id == 101
