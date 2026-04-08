"""Story 3.4 AC7: Fallback Configuration.

Tests that type-based fallbacks and inline fallbacks work correctly
when variables cannot be resolved from data.
"""

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
class TestAC7FallbackConfig:
    async def test_3_4_026_given_name_type_when_missing_then_there(
        self, injection_service
    ):
        lead = make_lead_dict(name=None)
        result = await injection_service.render_template("{{lead_name}}", lead)
        assert result.rendered_text == "there"

    async def test_3_4_027_given_company_type_when_missing_then_your_company(
        self, injection_service
    ):
        lead = make_lead_dict()
        result = await injection_service.render_template("{{employer}}", lead)
        assert result.rendered_text == "your company"

    async def test_3_4_028_given_inline_fallback_when_missing_then_overrides_type(
        self, injection_service
    ):
        lead = make_lead_dict()
        result = await injection_service.render_template(
            "{{company_name:Acme Inc}}", lead
        )
        assert result.rendered_text == "Acme Inc"

    async def test_3_4_029_given_custom_fallbacks_dict_when_resolved_then_dict_value(
        self, injection_service
    ):
        lead = make_lead_dict()
        custom_fallbacks = {"region": "North America"}
        result = await injection_service.render_template(
            "{{region}}", lead, custom_fallbacks=custom_fallbacks
        )
        assert result.rendered_text == "North America"
