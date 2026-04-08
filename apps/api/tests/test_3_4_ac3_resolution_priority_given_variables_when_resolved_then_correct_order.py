"""Story 3.4 AC3: Resolution Priority.

Tests that variable resolution follows the correct order:
lead standard -> custom fields -> system -> inline fallback -> custom fallbacks -> type -> global.
"""

from datetime import date

import pytest

from conftest_3_4 import (
    make_lead,
    make_lead_with_custom_fields,
    make_agent,
    make_lead_dict,
    TEST_ORG,
)
from services.variable_injection import VariableInjectionService, RenderResult
from unittest.mock import AsyncMock


@pytest.mark.asyncio
class TestAC3ResolutionPriority:
    @pytest.mark.p0
    async def test_3_4_012_given_standard_and_custom_same_key_when_resolved_then_standard_wins(
        self, injection_service
    ):
        lead = make_lead_dict(
            name="Standard Jane", custom_fields={"lead_name": "Custom Jane"}
        )
        result = await injection_service.render_template("{{lead_name}}", lead)
        assert result.rendered_text == "Standard Jane"

    @pytest.mark.p0
    async def test_3_4_013_given_custom_field_when_resolved_then_value_returned(
        self, injection_service
    ):
        lead = make_lead_dict(custom_fields={"industry": "Fintech"})
        result = await injection_service.render_template("{{industry}}", lead)
        assert result.rendered_text == "Fintech"

    @pytest.mark.p0
    async def test_3_4_014_given_current_date_when_resolved_then_todays_date(
        self, injection_service
    ):
        lead = make_lead_dict()
        result = await injection_service.render_template("{{current_date}}", lead)
        expected = date.today().isoformat()
        assert result.rendered_text == expected

    @pytest.mark.p0
    async def test_3_4_015_given_uppercase_var_when_resolved_then_case_insensitive(
        self, injection_service
    ):
        lead = make_lead_dict(name="Bob")
        result = await injection_service.render_template("{{LEAD_NAME}}", lead)
        assert result.rendered_text == "Bob"

    @pytest.mark.p0
    async def test_3_4_016_given_no_data_when_resolved_then_global_fallback(
        self, injection_service
    ):
        lead = make_lead_dict()
        result = await injection_service.render_template(
            "{{totally_unknown_var}}", lead
        )
        assert result.rendered_text == "Not Available"
