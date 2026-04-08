"""Story 3.4 Edge Cases.

Tests unusual inputs: empty braces, whitespace, null custom fields,
nested dicts, partial params, and large variable counts.
"""

import pytest

from conftest_3_4 import (
    make_lead,
    make_lead_with_custom_fields,
    make_lead_dict,
    make_agent,
    TEST_ORG,
)
from services.variable_injection import VariableInjectionService, RenderResult
from schemas.script_generation import ScriptGenerateRequest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
class TestEdgeCases:
    def test_3_4_edge001_given_empty_braces_when_parsed_then_no_vars(
        self, injection_service
    ):
        variables = injection_service.extract_variables("Hello {{}}")
        assert len(variables) == 0

    def test_3_4_edge002_given_whitespace_in_braces_when_parsed_then_no_vars(
        self, injection_service
    ):
        variables = injection_service.extract_variables("Hello {{ }}")
        assert len(variables) == 0

    async def test_3_4_edge003_given_empty_fallback_when_resolved_then_type_default(
        self, injection_service
    ):
        lead = make_lead_dict()
        result = await injection_service.render_template("{{employer}}", lead)
        assert result.rendered_text == "your company"

    def test_3_4_edge004_given_dollar_syntax_when_parsed_then_not_extracted(
        self, injection_service
    ):
        variables = injection_service.extract_variables("Hello $name and ${company}")
        assert len(variables) == 0

    async def test_3_4_edge005_given_null_custom_fields_when_resolved_then_fallback(
        self, injection_service
    ):
        lead = make_lead_dict(custom_fields=None)
        result = await injection_service.render_template("{{purchase_history}}", lead)
        assert result.was_rendered is True
        assert result.rendered_text == "Not Available"

    async def test_3_4_edge006_given_nested_dict_custom_field_when_resolved_then_string_repr(
        self, injection_service
    ):
        lead = make_lead_dict(custom_fields={"metadata": {"key": "value", "count": 42}})
        result = await injection_service.render_template("{{metadata}}", lead)
        assert result.was_rendered is True
        assert (
            "'key'" in result.rendered_text
            or "'value'" in result.rendered_text
            or "key" in result.rendered_text
        )

    def test_3_4_edge007_given_partial_params_when_validated_then_422(self):
        with pytest.raises(ValueError):
            ScriptGenerateRequest(query="test", lead_id=1)

    async def test_3_4_edge008_given_50_variables_when_rendered_then_all_resolved(
        self, injection_service
    ):
        custom_fields = {f"var_{i}": f"val_{i}" for i in range(50)}
        lead = make_lead_dict(custom_fields=custom_fields)
        parts = [f"{{{{var_{i}}}}}" for i in range(50)]
        template = " ".join(parts)

        result = await injection_service.render_template(template, lead)
        assert result.was_rendered is True
        for i in range(50):
            assert f"val_{i}" in result.rendered_text
