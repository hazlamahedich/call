"""Shared fixtures and helpers for Story 3.4 tests."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.variable_injection import (
    VariableInjectionService,
    VariableInfo,
    RenderResult,
)
from models.lead import Lead
from models.agent import Agent
from models.script import Script

TEST_ORG = "test_org_123"


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def injection_service(mock_session):
    return VariableInjectionService(mock_session)


def make_lead(**kwargs):
    defaults = {
        "id": 1,
        "org_id": TEST_ORG,
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "555-0100",
        "status": "new",
        "custom_fields": None,
    }
    defaults.update(kwargs)
    lead = Lead.model_validate(defaults)
    return lead


def make_lead_with_custom_fields(fields: dict, **kwargs):
    return make_lead(custom_fields=fields, **kwargs)


def make_script_with_variables(content: str, **kwargs):
    defaults = {
        "id": 1,
        "org_id": TEST_ORG,
        "name": "Test Script",
        "content": content,
    }
    defaults.update(kwargs)
    return Script.model_validate(defaults)


def make_agent(**kwargs):
    defaults = {
        "id": 1,
        "org_id": TEST_ORG,
        "name": "SalesBot",
    }
    defaults.update(kwargs)
    return Agent.model_validate(defaults)


def make_lead_dict(**kwargs):
    defaults = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "555-0100",
        "status": "new",
        "custom_fields": None,
    }
    defaults.update(kwargs)
    return defaults


def create_render_result(
    rendered_text, resolved=None, unresolved=None, was_rendered=True
):
    return RenderResult(
        rendered_text=rendered_text,
        resolved_variables=resolved or {},
        unresolved_variables=unresolved or [],
        was_rendered=was_rendered,
    )


def assert_variable_resolved(result: RenderResult, var_name: str, expected_value: str):
    assert var_name in result.resolved_variables, (
        f"Variable '{var_name}' not in resolved_variables"
    )
    assert result.resolved_variables[var_name] == expected_value, (
        f"Expected '{expected_value}' for '{var_name}', got '{result.resolved_variables[var_name]}'"
    )


@pytest.fixture
def sample_lead():
    return make_lead()


@pytest.fixture
def sample_lead_with_custom():
    return make_lead_with_custom_fields(
        {"company_name": "Acme Corp", "industry": "SaaS"}
    )


@pytest.fixture
def sample_agent():
    return make_agent()


@pytest.fixture
def sample_template():
    return (
        "Hello {{lead_name}}, this is {{agent_name}} calling. "
        "I wanted to reach out about {{company_name}}'s {{industry}} needs. "
        "We last spoke {{last_interaction:recently}}. "
        "Is {{lead_phone}} still the best number to reach you?"
    )
