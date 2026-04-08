"""Story 3.4 Expanded: Resolution Priority and Type-Based Fallbacks.

Tests the full resolution cascade with ORM objects, type-based fallbacks,
custom_fallbacks dict, system variables, and lead field edge cases.
"""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock

from conftest_3_4 import (
    make_lead,
    make_lead_with_custom_fields,
    make_agent,
    make_lead_dict,
    TEST_ORG,
)
from services.variable_injection import VariableInjectionService


@pytest.mark.asyncio
class TestResolutionWithORMObject:
    async def test_resolve_lead_name_from_orm_object(self, injection_service):
        lead = make_lead(name="Sarah Connor")
        result = await injection_service.render_template("Hello {{lead_name}}", lead)
        assert "Sarah Connor" in result.rendered_text

    async def test_resolve_lead_email_from_orm_object(self, injection_service):
        lead = make_lead(email="sarah@skynet.com")
        result = await injection_service.render_template("Email: {{lead_email}}", lead)
        assert "sarah@skynet.com" in result.rendered_text

    async def test_resolve_lead_phone_from_orm_object(self, injection_service):
        lead = make_lead(phone="555-0199")
        result = await injection_service.render_template("Call {{lead_phone}}", lead)
        assert "555-0199" in result.rendered_text

    async def test_resolve_lead_status_from_orm_object(self, injection_service):
        lead = make_lead(status="contacted")
        result = await injection_service.render_template(
            "Status: {{lead_status}}", lead
        )
        assert "contacted" in result.rendered_text

    async def test_resolve_custom_field_from_orm_object(self, injection_service):
        lead = make_lead_with_custom_fields({"company_name": "Cyberdyne"})
        lead.custom_fields = {"company_name": "Cyberdyne"}
        result = await injection_service.render_template("From {{company_name}}", lead)
        assert "Cyberdyne" in result.rendered_text


@pytest.mark.asyncio
class TestLeadFieldEdgeCases:
    async def test_lead_name_is_none_uses_fallback(self, injection_service):
        lead = make_lead_dict(name=None, phone=None)
        result = await injection_service.render_template("Hi {{lead_name}}", lead)
        assert (
            "there" in result.rendered_text.lower()
            or "Not Available" in result.rendered_text
        )

    async def test_lead_name_is_empty_uses_fallback(self, injection_service):
        lead = make_lead_dict(name="")
        result = await injection_service.render_template("Hi {{lead_name}}", lead)
        assert "{{lead_name}}" not in result.rendered_text

    async def test_phone_none_uses_fallback(self, injection_service):
        lead = make_lead_dict(phone=None)
        result = await injection_service.render_template("Call {{lead_phone}}", lead)
        assert "{{lead_phone}}" not in result.rendered_text

    async def test_custom_fields_null_resolves_to_fallback(self, injection_service):
        lead = make_lead_dict(custom_fields=None)
        result = await injection_service.render_template(
            "Company: {{company_name}}", lead
        )
        assert "{{company_name}}" not in result.rendered_text


@pytest.mark.asyncio
class TestCustomFieldComplexValues:
    async def test_dict_value_converted_to_string(self, injection_service):
        lead = make_lead_dict(
            custom_fields={"company": {"name": "Acme", "location": "NYC"}}
        )
        result = await injection_service.render_template("Info: {{company}}", lead)
        assert "{{company}}" not in result.rendered_text
        assert "Acme" in result.rendered_text

    async def test_list_value_converted_to_string(self, injection_service):
        lead = make_lead_dict(custom_fields={"tags": ["enterprise", "vip"]})
        result = await injection_service.render_template("Tags: {{tags}}", lead)
        assert "enterprise" in result.rendered_text

    async def test_custom_field_case_insensitive_key(self, injection_service):
        lead = make_lead_dict(custom_fields={"Company_Name": "Acme Corp"})
        result = await injection_service.render_template(
            "Hi from {{company_name}}", lead
        )
        assert "Acme Corp" in result.rendered_text


@pytest.mark.asyncio
class TestSystemVariables:
    async def test_current_date_returns_today(self, injection_service):
        lead = make_lead_dict()
        result = await injection_service.render_template("Date: {{current_date}}", lead)
        expected = date.today().isoformat()
        assert expected in result.rendered_text

    async def test_current_time_returns_formatted(self, injection_service):
        lead = make_lead_dict()
        result = await injection_service.render_template("Time: {{current_time}}", lead)
        assert "{{current_time}}" not in result.rendered_text
        assert len(result.rendered_text) > 6

    async def test_current_datetime_returns_iso(self, injection_service):
        lead = make_lead_dict()
        result = await injection_service.render_template(
            "When: {{current_datetime}}", lead
        )
        assert "{{current_datetime}}" not in result.rendered_text

    async def test_agent_name_without_agent_uses_fallback(self, injection_service):
        lead = make_lead_dict()
        result = await injection_service.render_template(
            "Hi {{agent_name}}", lead, agent=None
        )
        assert "{{agent_name}}" not in result.rendered_text


@pytest.mark.asyncio
class TestTypeBasedFallbacks:
    async def test_name_type_fallback_is_there(self, injection_service):
        lead = make_lead_dict(custom_fields={})
        result = await injection_service.render_template("Hi {{first_name}}", lead)
        assert result.resolved_variables.get("first_name") == "there"

    async def test_company_type_fallback_is_your_company(self, injection_service):
        lead = make_lead_dict(custom_fields={})
        result = await injection_service.render_template("About {{company_size}}", lead)
        assert result.resolved_variables.get("company_size") == "your company"

    async def test_date_type_fallback_is_recently(self, injection_service):
        lead = make_lead_dict(custom_fields={})
        result = await injection_service.render_template(
            "Updated {{interaction_date}}", lead
        )
        assert result.resolved_variables.get("interaction_date") == "recently"

    async def test_email_type_fallback(self, injection_service):
        lead = make_lead_dict(custom_fields={})
        result = await injection_service.render_template(
            "Email {{contact_email}}", lead
        )
        assert result.resolved_variables.get("contact_email") == "Not Available"

    async def test_phone_type_fallback(self, injection_service):
        lead = make_lead_dict(custom_fields={})
        result = await injection_service.render_template("Call {{mobile_number}}", lead)
        assert result.resolved_variables.get("mobile_number") == "Not Available"

    async def test_generic_fallback_is_not_available(self, injection_service):
        lead = make_lead_dict(custom_fields={})
        result = await injection_service.render_template(
            "Value: {{totally_unknown}}", lead
        )
        assert result.resolved_variables.get("totally_unknown") == "Not Available"


@pytest.mark.asyncio
class TestCustomFallbacksDict:
    async def test_custom_fallbacks_override_type_default(self, injection_service):
        lead = make_lead_dict(custom_fields={})
        result = await injection_service.render_template(
            "Region: {{region}}",
            lead,
            custom_fallbacks={"region": "the East Coast"},
        )
        assert result.resolved_variables.get("region") == "the East Coast"

    async def test_custom_fallbacks_used_when_no_data(self, injection_service):
        lead = make_lead_dict(custom_fields={})
        result = await injection_service.render_template(
            "Source: {{source_channel}}",
            lead,
            custom_fallbacks={"source_channel": "organic"},
        )
        assert result.resolved_variables.get("source_channel") == "organic"

    async def test_lead_data_takes_priority_over_custom_fallbacks(
        self, injection_service
    ):
        lead = make_lead_dict(name="Alice")
        result = await injection_service.render_template(
            "Hi {{lead_name}}",
            lead,
            custom_fallbacks={"lead_name": "Bob"},
        )
        assert "Alice" in result.rendered_text
        assert "Bob" not in result.rendered_text


@pytest.mark.asyncio
class TestRenderTemplateEdgeCases:
    async def test_no_variables_returns_was_rendered_false(self, injection_service):
        lead = make_lead_dict()
        result = await injection_service.render_template(
            "Hello world, no variables here.", lead
        )
        assert result.was_rendered is False
        assert result.rendered_text == "Hello world, no variables here."
        assert result.resolved_variables == {}

    async def test_duplicate_variables_different_case_deduplicated(
        self, injection_service
    ):
        lead = make_lead_dict(name="Bob")
        result = await injection_service.render_template(
            "{{lead_name}} and {{LEAD_NAME}}", lead
        )
        assert result.rendered_text == "Bob and Bob"
        assert "lead_name" in result.resolved_variables

    async def test_custom_fallbacks_passed_through(self, injection_service):
        lead = make_lead_dict(custom_fields={})
        result = await injection_service.render_template(
            "Hi {{first_name}}",
            lead,
            custom_fallbacks={"first_name": "Friend"},
        )
        assert "Friend" in result.rendered_text
