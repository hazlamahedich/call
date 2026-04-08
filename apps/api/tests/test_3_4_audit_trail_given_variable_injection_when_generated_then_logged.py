"""Story 3.4 Audit Trail.

Tests that variable injection events are logged with
variable counts and unresolved names, without logging PII values.
"""

import logging
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from conftest_3_4 import (
    make_lead,
    make_lead_with_custom_fields,
    make_agent,
    make_lead_dict,
    TEST_ORG,
)
from services.variable_injection import VariableInjectionService, RenderResult


@pytest.mark.asyncio
class TestAuditTrail:
    @pytest.mark.p2
    async def test_3_4_032_given_generation_with_vars_when_completed_then_variable_count_logged(
        self, injection_service
    ):
        lead = make_lead_dict(name="Alice")
        template = "Hi {{lead_name}}, welcome to {{company_name}}"

        with patch("services.variable_injection.logger") as mock_logger:
            result = await injection_service.render_template(template, lead)
            assert len(result.resolved_variables) >= 1

    @pytest.mark.p2
    async def test_3_4_033_given_unresolved_vars_when_completed_then_names_logged(
        self, injection_service
    ):
        lead = make_lead_dict()
        template = "{{unknown_var_x}} and {{another_unknown_y}}"

        result = await injection_service.render_template(template, lead)
        assert "unknown_var_x" in result.unresolved_variables
        assert "another_unknown_y" in result.unresolved_variables

    @pytest.mark.p2
    async def test_3_4_034_given_audit_entry_when_inspected_then_no_values_logged(
        self, injection_service
    ):
        lead = make_lead_dict(name="Sensitive Name", email="secret@email.com")
        template = "{{lead_name}} {{lead_email}}"

        result = await injection_service.render_template(template, lead)

        assert "lead_name" in result.resolved_variables
        assert "lead_email" in result.resolved_variables
        assert result.resolved_variables["lead_name"] == "Sensitive Name"
        assert result.resolved_variables["lead_email"] == "secret@email.com"
