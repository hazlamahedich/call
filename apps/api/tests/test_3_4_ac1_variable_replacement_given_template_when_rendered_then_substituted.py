"""Story 3.4 AC1: Variable Replacement.

Tests that {{variable}} placeholders are correctly substituted
with resolved values from lead, custom fields, and fallbacks.
"""

import pytest

from conftest_3_4 import (
    make_lead,
    make_lead_with_custom_fields,
    make_lead_dict,
    make_agent,
    assert_variable_resolved,
    create_render_result,
    TEST_ORG,
)
from services.variable_injection import VariableInjectionService, RenderResult
from unittest.mock import AsyncMock


@pytest.mark.asyncio
class TestAC1VariableReplacement:
    @pytest.mark.p0
    async def test_3_4_001_given_template_with_lead_name_when_rendered_then_substituted(
        self, injection_service
    ):
        lead = make_lead_dict(name="John")
        result = await injection_service.render_template("Hello {{lead_name}}", lead)
        assert result.rendered_text == "Hello John"
        assert result.was_rendered is True
        assert_variable_resolved(result, "lead_name", "John")

    @pytest.mark.p0
    async def test_3_4_002_given_custom_field_when_rendered_then_substituted(
        self, injection_service
    ):
        lead = make_lead_dict(custom_fields={"company_name": "Acme"})
        result = await injection_service.render_template("{{company_name}}", lead)
        assert result.rendered_text == "Acme"
        assert_variable_resolved(result, "company_name", "Acme")

    @pytest.mark.p0
    async def test_3_4_003_given_missing_variable_when_rendered_then_fallback(
        self, injection_service
    ):
        lead = make_lead_dict()
        result = await injection_service.render_template("{{unknown_field}}", lead)
        assert result.was_rendered is True
        assert "unknown_field" in result.unresolved_variables
        assert result.rendered_text != "{{unknown_field}}"

    @pytest.mark.p0
    async def test_3_4_004_given_inline_fallback_when_no_data_then_uses_inline(
        self, injection_service
    ):
        lead = make_lead_dict()
        result = await injection_service.render_template("{{region:your area}}", lead)
        assert result.rendered_text == "your area"

    @pytest.mark.p0
    async def test_3_4_005_given_mixed_variables_when_rendered_then_partial_resolution(
        self, injection_service
    ):
        lead = make_lead_dict(name="Alice")
        template = "Hi {{lead_name}}, welcome to {{company_name}}!"
        result = await injection_service.render_template(template, lead)
        assert "Alice" in result.rendered_text
        assert "company_name" in result.unresolved_variables
        assert "lead_name" in result.resolved_variables
        assert "{{lead_name}}" not in result.rendered_text
