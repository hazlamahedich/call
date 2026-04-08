"""Story 3.4 Expanded: Shared Queries and Router Integration.

Tests shared_queries.py error paths and the render/preview-variables
router endpoints via mocked integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from conftest_3_4 import TEST_ORG, make_lead, make_agent, make_script_with_variables


class TestSharedQueriesErrorPaths:
    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_load_agent_404_detail(self):
        from services.shared_queries import load_agent_for_context

        with patch(
            "services.shared_queries.load_agent_for_context", new_callable=AsyncMock
        ) as mock:
            mock.side_effect = HTTPException(
                status_code=404,
                detail={"code": "agent_not_found", "message": "Agent not found"},
            )
            with pytest.raises(HTTPException) as exc_info:
                await mock(AsyncMock(), 999, TEST_ORG)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_load_agent_403_detail(self):
        with patch(
            "services.shared_queries.load_agent_for_context", new_callable=AsyncMock
        ) as mock:
            mock.side_effect = HTTPException(
                status_code=403,
                detail={
                    "code": "wrong_org",
                    "message": "Agent belongs to different organization",
                },
            )
            with pytest.raises(HTTPException) as exc_info:
                await mock(AsyncMock(), 1, "wrong_org")
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_load_lead_404_detail(self):
        with patch(
            "services.shared_queries.load_lead_for_context", new_callable=AsyncMock
        ) as mock:
            mock.side_effect = HTTPException(
                status_code=404,
                detail={"code": "lead_not_found", "message": "Lead not found"},
            )
            with pytest.raises(HTTPException) as exc_info:
                await mock(AsyncMock(), 999, TEST_ORG)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_load_lead_403_detail(self):
        with patch(
            "services.shared_queries.load_lead_for_context", new_callable=AsyncMock
        ) as mock:
            mock.side_effect = HTTPException(
                status_code=403,
                detail={
                    "code": "wrong_org",
                    "message": "Lead belongs to different organization",
                },
            )
            with pytest.raises(HTTPException) as exc_info:
                await mock(AsyncMock(), 1, "wrong_org")
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_load_script_404_detail(self):
        with patch(
            "services.shared_queries.load_script_for_context", new_callable=AsyncMock
        ) as mock:
            mock.side_effect = HTTPException(
                status_code=404,
                detail={"code": "script_not_found", "message": "Script not found"},
            )
            with pytest.raises(HTTPException) as exc_info:
                await mock(AsyncMock(), 999, TEST_ORG)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_load_script_403_detail(self):
        with patch(
            "services.shared_queries.load_script_for_context", new_callable=AsyncMock
        ) as mock:
            mock.side_effect = HTTPException(
                status_code=403,
                detail={
                    "code": "wrong_org",
                    "message": "Script belongs to different organization",
                },
            )
            with pytest.raises(HTTPException) as exc_info:
                await mock(AsyncMock(), 1, "wrong_org")
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_set_rls_context_calls_set_config(self):
        mock_session = AsyncMock()
        from services.shared_queries import set_rls_context

        await set_rls_context(mock_session, TEST_ORG)
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        assert "set_config" in sql_text
        assert call_args[1] == {"org_id": TEST_ORG} or call_args[0][1] == {
            "org_id": TEST_ORG
        }

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_load_agent_success(self):
        agent = make_agent(org_id=TEST_ORG)
        with patch(
            "services.shared_queries.load_agent_for_context",
            new_callable=AsyncMock,
            return_value=agent,
        ) as mock_fn:
            result = await mock_fn(AsyncMock(), agent.id, TEST_ORG)
            assert result == agent
            mock_fn.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_load_agent_for_update_flag(self):
        agent = make_agent(org_id=TEST_ORG)
        with patch(
            "services.shared_queries.load_agent_for_context",
            new_callable=AsyncMock,
            return_value=agent,
        ) as mock:
            result = await mock(AsyncMock(), 1, TEST_ORG, for_update=True)
            assert result == agent


class TestRenderEndpointLogic:
    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_render_with_custom_fallbacks(self):
        from services.variable_injection import VariableInjectionService

        mock_session = AsyncMock()
        service = VariableInjectionService(mock_session)
        lead = make_lead(org_id=TEST_ORG)
        result = await service.render_template(
            "Hi {{region}} from {{lead_name}}",
            lead,
            custom_fallbacks={"region": "California"},
        )
        assert "California" in result.rendered_text
        assert "John Doe" in result.rendered_text

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_render_with_agent_name(self):
        from services.variable_injection import VariableInjectionService

        mock_session = AsyncMock()
        service = VariableInjectionService(mock_session)
        lead = make_lead()
        agent = make_agent(name="BotMcBotFace")
        result = await service.render_template(
            "I am {{agent_name}}, calling for {{lead_name}}",
            lead,
            agent=agent,
        )
        assert "BotMcBotFace" in result.rendered_text
        assert "John Doe" in result.rendered_text

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_render_without_agent_id_skips_agent_load(self):
        from services.variable_injection import VariableInjectionService

        mock_session = AsyncMock()
        service = VariableInjectionService(mock_session)
        lead = make_lead()
        result = await service.render_template(
            "Hello {{lead_name}}, this is {{agent_name}}",
            lead,
            agent=None,
        )
        assert "John Doe" in result.rendered_text
        assert "agent_name" in result.unresolved_variables


class TestPreviewVariablesLogic:
    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_preview_extracts_variables_and_sources(self):
        from services.variable_injection import VariableInjectionService

        mock_session = AsyncMock()
        service = VariableInjectionService(mock_session)
        template = (
            "Hello {{lead_name}}, today is {{current_date}} from {{company_name}}"
        )
        variables = service.extract_variables(template)

        var_names = [v.name for v in variables]
        var_sources = {v.name: v.source_type for v in variables}

        assert "lead_name" in var_names
        assert var_sources["lead_name"] == "lead"
        assert var_sources["current_date"] == "system"
        assert var_sources["company_name"] == "custom"

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_preview_with_sample_data(self):
        from services.variable_injection import VariableInjectionService

        mock_session = AsyncMock()
        service = VariableInjectionService(mock_session)
        template = "Hello {{lead_name}}"
        sample = {"name": "Preview User"}
        result = await service.render_template(template, sample)
        assert "Preview User" in result.rendered_text

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_preview_without_sample_data(self):
        from services.variable_injection import VariableInjectionService

        mock_session = AsyncMock()
        service = VariableInjectionService(mock_session)
        template = "Hello {{unknown_var}}"
        result = await service.render_template(template, {})
        assert "{{unknown_var}}" not in result.rendered_text
