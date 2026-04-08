"""Story 3.4 AC8: Performance.

Tests that variable injection completes within acceptable time limits.
"""

import time

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
class TestAC8Performance:
    @pytest.mark.p1
    async def test_3_4_030_given_10_variables_when_rendered_then_under_10ms(
        self, injection_service
    ):
        lead = make_lead_dict(
            name="John",
            email="john@acme.com",
            phone="555-0100",
            custom_fields={
                "company_name": "Acme",
                "industry": "SaaS",
                "region": "NA",
                "tier": "gold",
                "last_interaction": "2024-01-01",
                "budget": "100k",
                "department": "Engineering",
            },
        )
        template = (
            "Hello {{lead_name}}, email {{lead_email}}, phone {{lead_phone}}, "
            "company {{company_name}}, industry {{industry}}, region {{region}}, "
            "tier {{tier}}, last {{last_interaction}}, budget {{budget}}, dept {{department}}"
        )

        start = time.monotonic()
        result = await injection_service.render_template(template, lead)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert result.was_rendered is True
        assert elapsed_ms < 10, f"Rendering took {elapsed_ms:.2f}ms, expected < 10ms"

    @pytest.mark.p1
    async def test_3_4_031_given_render_service_when_called_then_fast(
        self, injection_service
    ):
        lead = make_lead_dict(name="Fast Test")
        template = "Hi {{lead_name}}"

        start = time.monotonic()
        for _ in range(100):
            await injection_service.render_template(template, lead)
        elapsed_ms = (time.monotonic() - start) * 1000

        avg_ms = elapsed_ms / 100
        assert avg_ms < 1, f"Average {avg_ms:.3f}ms per call, expected < 1ms"
