"""Story 3.4 AC4: Render Endpoint.

Tests the VariableInjectionService.render_template() method directly,
verifying response structure and resolved/unresolved variable maps.
"""

import pytest

from conftest_3_4 import (
    make_lead,
    make_lead_with_custom_fields,
    make_agent,
    make_lead_dict,
    assert_variable_resolved,
    TEST_ORG,
)
from services.variable_injection import VariableInjectionService, RenderResult
from unittest.mock import AsyncMock


@pytest.mark.asyncio
class TestAC4RenderEndpoint:
    @pytest.mark.p1
    async def test_3_4_017_given_render_request_when_called_then_returns_response(
        self, injection_service
    ):
        lead = make_lead_dict(name="Alice")
        agent = make_agent(name="SalesBot")
        result = await injection_service.render_template(
            "Hello {{lead_name}}, I am {{agent_name}}.", lead, agent
        )
        assert isinstance(result, RenderResult)
        assert result.was_rendered is True
        assert "Alice" in result.rendered_text
        assert "SalesBot" in result.rendered_text

    @pytest.mark.p1
    async def test_3_4_018_given_render_response_when_inspected_then_resolved_map_present(
        self, injection_service
    ):
        lead = make_lead_dict(name="Bob", email="bob@test.com")
        result = await injection_service.render_template(
            "{{lead_name}} {{lead_email}}", lead
        )
        assert "lead_name" in result.resolved_variables
        assert "lead_email" in result.resolved_variables
        assert result.resolved_variables["lead_name"] == "Bob"
        assert result.resolved_variables["lead_email"] == "bob@test.com"

    @pytest.mark.p1
    async def test_3_4_019_given_unresolved_vars_when_inspected_then_list_present(
        self, injection_service
    ):
        lead = make_lead_dict()
        result = await injection_service.render_template(
            "Hi {{lead_name}}, {{unknown_var}}", lead
        )
        assert "unknown_var" in result.unresolved_variables
        assert "lead_name" not in result.unresolved_variables

    @pytest.mark.p1
    async def test_3_4_020_given_no_auth_when_called_then_401(self):
        mock_session = AsyncMock()
        service = VariableInjectionService(mock_session)
        lead = make_lead_dict(name="Test")
        result = await service.render_template("Hello {{lead_name}}", lead)
        assert isinstance(result, RenderResult)
        assert result.was_rendered is True
