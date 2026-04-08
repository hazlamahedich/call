"""Story 3.4 Expanded: Schema Validation Tests.

Tests all Pydantic schemas with camelCase aliasing,
field validators, and boundary conditions.
"""

import pytest
from pydantic import ValidationError

from schemas.variable_injection import (
    ScriptRenderRequest,
    ScriptRenderResponse,
    VariablePreviewRequest,
    VariablePreviewResponse,
    CustomFieldsUpdateRequest,
    ResolvedVariable,
)


class TestScriptRenderRequest:
    def test_camel_case_aliases(self):
        req = ScriptRenderRequest(**{"scriptId": 1, "leadId": 2})
        assert req.script_id == 1
        assert req.lead_id == 2

    def test_snake_case_also_works(self):
        req = ScriptRenderRequest(script_id=1, lead_id=2)
        assert req.script_id == 1

    def test_optional_agent_id(self):
        req = ScriptRenderRequest(script_id=1, lead_id=2)
        assert req.agent_id is None

    def test_optional_custom_fallbacks(self):
        req = ScriptRenderRequest(script_id=1, lead_id=2)
        assert req.custom_fallbacks is None

    def test_with_all_fields(self):
        req = ScriptRenderRequest(
            script_id=1,
            lead_id=2,
            agent_id=3,
            custom_fallbacks={"key": "value"},
        )
        assert req.agent_id == 3
        assert req.custom_fallbacks == {"key": "value"}

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            ScriptRenderRequest(script_id=1)


class TestScriptRenderResponse:
    def test_camel_case_serialization(self):
        resp = ScriptRenderResponse(
            rendered_text="Hello John",
            resolved_variables={"lead_name": "John"},
            unresolved_variables=[],
            was_rendered=True,
        )
        data = resp.model_dump(by_alias=True)
        assert "renderedText" in data
        assert "resolvedVariables" in data
        assert "unresolvedVariables" in data
        assert "wasRendered" in data


class TestVariablePreviewRequest:
    def test_valid_template(self):
        req = VariablePreviewRequest(template="Hello {{name}}")
        assert req.template == "Hello {{name}}"

    def test_empty_template_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            VariablePreviewRequest(template="")
        assert (
            "at least 1 character" in str(exc_info.value).lower()
            or "min_length" in str(exc_info.value).lower()
        )

    def test_too_long_template_rejected(self):
        with pytest.raises(ValidationError):
            VariablePreviewRequest(template="A" * 50001)

    def test_max_length_template_accepted(self):
        req = VariablePreviewRequest(template="A" * 50000)
        assert len(req.template) == 50000

    def test_sample_data_optional(self):
        req = VariablePreviewRequest(template="Hi {{name}}")
        assert req.sample_data is None

    def test_sample_data_provided(self):
        req = VariablePreviewRequest(
            template="Hi {{name}}", sample_data={"name": "Test"}
        )
        assert req.sample_data == {"name": "Test"}


class TestCustomFieldsUpdateRequest:
    def test_valid_fields(self):
        req = CustomFieldsUpdateRequest(custom_fields={"company": "Acme"})
        assert req.custom_fields == {"company": "Acme"}

    def test_empty_dict_rejected(self):
        with pytest.raises(ValidationError):
            CustomFieldsUpdateRequest(custom_fields={})

    def test_value_exceeding_500_chars_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldsUpdateRequest(custom_fields={"key": "A" * 501})
        assert "500" in str(exc_info.value)

    def test_value_at_500_chars_accepted(self):
        req = CustomFieldsUpdateRequest(custom_fields={"key": "A" * 500})
        assert len(req.custom_fields["key"]) == 500

    def test_max_50_keys(self):
        fields = {f"key_{i}": f"val_{i}" for i in range(50)}
        req = CustomFieldsUpdateRequest(custom_fields=fields)
        assert len(req.custom_fields) == 50

    def test_over_50_keys_rejected(self):
        fields = {f"key_{i}": f"val_{i}" for i in range(51)}
        with pytest.raises(ValidationError):
            CustomFieldsUpdateRequest(custom_fields=fields)

    def test_empty_string_value_accepted(self):
        req = CustomFieldsUpdateRequest(custom_fields={"key": ""})
        assert req.custom_fields["key"] == ""

    def test_camel_case_alias(self):
        req = CustomFieldsUpdateRequest(**{"customFields": {"k": "v"}})
        assert req.custom_fields == {"k": "v"}


class TestResolvedVariable:
    def test_camel_case_serialization(self):
        var = ResolvedVariable(
            name="lead_name", value="John", source="lead", used_fallback=False
        )
        data = var.model_dump(by_alias=True)
        assert "usedFallback" in data
        assert "used_fallback" not in data
