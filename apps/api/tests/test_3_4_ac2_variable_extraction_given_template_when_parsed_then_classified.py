"""Story 3.4 AC2: Variable Extraction.

Tests that {{variable}} placeholders are correctly parsed
and classified by source type (lead, system, custom).
"""

import pytest

from conftest_3_4 import (
    make_lead,
    make_lead_with_custom_fields,
    make_agent,
    TEST_ORG,
)
from services.variable_injection import (
    VariableInjectionService,
    VariableInfo,
    RenderResult,
    classify_source,
)
from unittest.mock import AsyncMock


class TestAC2VariableExtraction:
    @pytest.mark.p0
    def test_3_4_006_given_3_variables_when_extracted_then_3_entries(
        self, injection_service
    ):
        template = (
            "Hi {{lead_name}}, calling about {{company_name}} on {{current_date}}"
        )
        variables = injection_service.extract_variables(template)
        assert len(variables) == 3
        names = {v.name for v in variables}
        assert names == {"lead_name", "company_name", "current_date"}

    @pytest.mark.p0
    def test_3_4_007_given_lead_name_when_classified_then_lead(self):
        assert classify_source("lead_name") == "lead"

    @pytest.mark.p0
    def test_3_4_008_given_current_date_when_classified_then_system(self):
        assert classify_source("current_date") == "system"

    @pytest.mark.p0
    def test_3_4_009_given_purchase_history_when_classified_then_custom(self):
        assert classify_source("purchase_history") == "custom"

    @pytest.mark.p0
    def test_3_4_010_given_var_fallback_when_parsed_then_has_fallback(
        self, injection_service
    ):
        template = "{{region:your area}}"
        variables = injection_service.extract_variables(template)
        assert len(variables) == 1
        assert variables[0].fallback == "your area"

    @pytest.mark.p0
    def test_3_4_011_given_dollar_syntax_when_parsed_then_not_extracted(
        self, injection_service
    ):
        template = "Hello $lead_name and ${company}"
        variables = injection_service.extract_variables(template)
        assert len(variables) == 0
