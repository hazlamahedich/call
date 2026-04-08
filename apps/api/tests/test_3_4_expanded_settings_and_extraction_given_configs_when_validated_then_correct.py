"""Story 3.4 Expanded: Settings Validation and Extraction Edge Cases.

Tests settings validators, extract_variables edge cases, and
_used_fallback accuracy.
"""

import pytest
from pydantic import ValidationError

from conftest_3_4 import make_lead_dict, make_lead_with_custom_fields, make_agent
from services.variable_injection import (
    VariableInjectionService,
    VariableInfo,
    classify_source,
)


class TestSettingsValidation:
    @pytest.mark.p2
    def test_default_values(self):
        from config.settings import settings

        assert settings.VARIABLE_DEFAULT_FALLBACK == "Not Available"
        assert settings.VARIABLE_INJECTION_ENABLED is True
        assert settings.VARIABLE_RESOLUTION_TIMEOUT_MS == 100
        assert settings.MAX_VARIABLE_VALUE_LENGTH == 500

    @pytest.mark.p2
    def test_resolution_timeout_zero_rejected(self):
        from config.settings import Settings

        with pytest.raises(Exception):
            Settings(VARIABLE_RESOLUTION_TIMEOUT_MS=0)

    @pytest.mark.p2
    def test_resolution_timeout_negative_rejected(self):
        from config.settings import Settings

        with pytest.raises(Exception):
            Settings(VARIABLE_RESOLUTION_TIMEOUT_MS=-1)

    @pytest.mark.p2
    def test_resolution_timeout_valid_accepted(self):
        from config.settings import Settings

        s = Settings(VARIABLE_RESOLUTION_TIMEOUT_MS=50)
        assert s.VARIABLE_RESOLUTION_TIMEOUT_MS == 50


class TestClassifySource:
    @pytest.mark.p2
    def test_lead_name_classified_as_lead(self):
        assert classify_source("lead_name") == "lead"

    @pytest.mark.p2
    def test_lead_email_classified_as_lead(self):
        assert classify_source("lead_email") == "lead"

    @pytest.mark.p2
    def test_current_date_classified_as_system(self):
        assert classify_source("current_date") == "system"

    @pytest.mark.p2
    def test_current_time_classified_as_system(self):
        assert classify_source("current_time") == "system"

    @pytest.mark.p2
    def test_agent_name_classified_as_system(self):
        assert classify_source("agent_name") == "system"

    @pytest.mark.p2
    def test_unknown_classified_as_custom(self):
        assert classify_source("company_name") == "custom"

    @pytest.mark.p2
    def test_case_insensitive_classification(self):
        assert classify_source("LEAD_NAME") == "lead"
        assert classify_source("CURRENT_DATE") == "system"


class TestExtractVariablesEdgeCases:
    @pytest.mark.p2
    def test_empty_fallback_not_matched(self):
        service = VariableInjectionService(AsyncMock())
        variables = service.extract_variables("Hello {{var:}}")
        assert len(variables) == 0

    @pytest.mark.p2
    def test_space_fallback_treated_as_none(self):
        service = VariableInjectionService(AsyncMock())
        variables = service.extract_variables("Hello {{var: }}")
        assert len(variables) == 1
        assert variables[0].fallback is None

    @pytest.mark.p2
    def test_whitespace_fallback_treated_as_none(self):
        service = VariableInjectionService(AsyncMock())
        variables = service.extract_variables("Hello {{var:   }}")
        assert len(variables) == 1
        assert variables[0].fallback is None

    @pytest.mark.p2
    def test_whitespace_in_braces_not_matched(self):
        service = VariableInjectionService(AsyncMock())
        variables = service.extract_variables("Hello {{ lead_name }}")
        assert len(variables) == 0

    @pytest.mark.p2
    def test_dollar_braces_not_matched(self):
        service = VariableInjectionService(AsyncMock())
        variables = service.extract_variables("Price: ${{price}}")
        assert len(variables) == 0

    @pytest.mark.p2
    def test_empty_braces_not_matched(self):
        service = VariableInjectionService(AsyncMock())
        variables = service.extract_variables("Hello {{}}")
        assert len(variables) == 0

    @pytest.mark.p2
    def test_raw_match_construction(self):
        service = VariableInjectionService(AsyncMock())
        variables = service.extract_variables("{{lead_name:there}}")
        assert variables[0].raw_match == "{{lead_name:there}}"

    @pytest.mark.p2
    def test_raw_match_without_fallback(self):
        service = VariableInjectionService(AsyncMock())
        variables = service.extract_variables("{{lead_name}}")
        assert variables[0].raw_match == "{{lead_name}}"

    @pytest.mark.p2
    def test_case_dedup_first_wins(self):
        service = VariableInjectionService(AsyncMock())
        variables = service.extract_variables("{{lead_name}} and {{LEAD_NAME}}")
        assert len(variables) == 1
        assert variables[0].name == "lead_name"

    @pytest.mark.p2
    def test_multiple_variables_extracted(self):
        service = VariableInjectionService(AsyncMock())
        variables = service.extract_variables(
            "{{lead_name}} {{company_name}} {{current_date}}"
        )
        assert len(variables) == 3

    @pytest.mark.p2
    def test_variable_with_hyphen_not_matched(self):
        service = VariableInjectionService(AsyncMock())
        variables = service.extract_variables("{{company-name}}")
        assert len(variables) == 0

    @pytest.mark.p2
    def test_variable_starting_with_number_not_matched(self):
        service = VariableInjectionService(AsyncMock())
        variables = service.extract_variables("{{1var}}")
        assert len(variables) == 0


from unittest.mock import AsyncMock


class TestUsedFallbackAccuracy:
    @pytest.mark.p2
    def test_resolve_returns_used_fallback_true_for_unknown(self):
        service = VariableInjectionService(AsyncMock())
        value, used_fallback = service._resolve("totally_unknown", None, {}, None, None)
        assert used_fallback is True

    @pytest.mark.p2
    def test_resolve_returns_used_fallback_false_for_resolved_lead_field(self):
        service = VariableInjectionService(AsyncMock())
        lead = make_lead_dict(name="Alice")
        value, used_fallback = service._resolve("lead_name", None, lead, None, None)
        assert used_fallback is False
        assert "Alice" in value

    @pytest.mark.p2
    def test_resolve_returns_used_fallback_false_for_system_callable(self):
        service = VariableInjectionService(AsyncMock())
        value, used_fallback = service._resolve("current_date", None, {}, None, None)
        assert used_fallback is False

    @pytest.mark.p2
    def test_resolve_returns_used_fallback_false_for_agent_with_name(self):
        service = VariableInjectionService(AsyncMock())
        agent = make_agent(name="Bot")
        value, used_fallback = service._resolve("agent_name", None, {}, agent, None)
        assert used_fallback is False
        assert "Bot" in value

    @pytest.mark.p2
    def test_resolve_returns_used_fallback_true_for_agent_without_name(self):
        service = VariableInjectionService(AsyncMock())
        agent = make_agent(name="")
        value, used_fallback = service._resolve("agent_name", None, {}, agent, None)
        assert used_fallback is True

    @pytest.mark.p2
    def test_resolve_returns_used_fallback_false_for_inline_fallback(self):
        service = VariableInjectionService(AsyncMock())
        value, used_fallback = service._resolve(
            "unknown", "default_val", {}, None, None
        )
        assert used_fallback is False
        assert value == "default_val"

    @pytest.mark.p2
    def test_resolve_returns_used_fallback_false_for_custom_fallbacks_dict(self):
        service = VariableInjectionService(AsyncMock())
        value, used_fallback = service._resolve(
            "region", None, {}, None, {"region": "East"}
        )
        assert used_fallback is False
        assert value == "East"

    @pytest.mark.p2
    def test_resolve_returns_used_fallback_false_for_custom_field(self):
        service = VariableInjectionService(AsyncMock())
        lead = make_lead_dict(custom_fields={"company_name": "Acme"})
        value, used_fallback = service._resolve("company_name", None, lead, None, None)
        assert used_fallback is False
        assert "Acme" in value

    @pytest.mark.p2
    def test_resolve_returns_used_fallback_true_for_null_custom_field(self):
        service = VariableInjectionService(AsyncMock())
        lead = make_lead_dict(custom_fields={"company_name": None})
        value, used_fallback = service._resolve("company_name", None, lead, None, None)
        assert used_fallback is True
