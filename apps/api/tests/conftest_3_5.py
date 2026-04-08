import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.script_lab_session import ScriptLabSession
from models.script_lab_turn import ScriptLabTurn
from schemas.script_lab import SourceAttribution

TEST_ORG = "test_org_123"
TEST_ORG_B = "test_org_456"


def make_lab_session(**kwargs):
    defaults = {
        "id": 1,
        "org_id": TEST_ORG,
        "agent_id": 1,
        "script_id": 1,
        "lead_id": None,
        "scenario_overlay": None,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "status": "active",
        "turn_count": 0,
        "soft_delete": False,
    }
    defaults.update(kwargs)
    return ScriptLabSession.model_validate(defaults)


def make_lab_turn(**kwargs):
    defaults = {
        "id": 1,
        "org_id": TEST_ORG,
        "session_id": 1,
        "turn_number": 1,
        "role": "user",
        "content": "Hello",
        "source_attributions": None,
        "grounding_confidence": None,
        "low_confidence_warning": False,
        "soft_delete": False,
    }
    defaults.update(kwargs)
    return ScriptLabTurn.model_validate(defaults)


def make_source_attribution(**kwargs):
    defaults = {
        "chunk_id": 42,
        "document_name": "product_brochure.pdf",
        "page_number": 3,
        "excerpt": "Acme Corp offers enterprise SaaS solutions for modern businesses...",
        "similarity_score": 0.92,
    }
    defaults.update(kwargs)
    return SourceAttribution(**defaults)


def make_raw_chunk(**kwargs):
    defaults = {
        "chunk_id": 42,
        "knowledge_base_id": 1,
        "content": "Acme Corp offers enterprise SaaS solutions for modern businesses seeking growth.",
        "metadata": {
            "source_file": "product_brochure.pdf",
            "page_number": 3,
            "chunk_index": 7,
        },
        "similarity": 0.92,
    }
    defaults.update(kwargs)
    return defaults


def make_active_row(**overrides):
    defaults = {
        "id": 1,
        "org_id": TEST_ORG,
        "agent_id": 1,
        "script_id": 10,
        "lead_id": None,
        "scenario_overlay": None,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "status": "active",
        "turn_count": 0,
    }
    defaults.update(overrides)
    return tuple(defaults.values())


def make_expired_row(**overrides):
    defaults = {
        "id": 1,
        "org_id": TEST_ORG,
        "agent_id": 1,
        "script_id": 1,
        "lead_id": None,
        "scenario_overlay": None,
        "expires_at": datetime.now(timezone.utc) - timedelta(minutes=5),
        "status": "active",
        "turn_count": 0,
    }
    defaults.update(overrides)
    return tuple(defaults.values())


def make_overlay_row(**overrides):
    defaults = {
        "id": 1,
        "org_id": TEST_ORG,
        "agent_id": 1,
        "script_id": 1,
        "lead_id": None,
        "status": "active",
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "scenario_overlay": None,
    }
    defaults.update(overrides)
    return tuple(defaults.values())


def mock_gen_result(response="AI response", confidence=0.85, chunks=None):
    gen_result = MagicMock()
    gen_result.response = response
    gen_result.grounding_confidence = confidence
    gen_result.source_chunks = chunks or [make_raw_chunk()]
    return gen_result


def mock_gen_service(gen_result):
    svc = AsyncMock()
    svc.generate_response.return_value = gen_result
    return svc


@asynccontextmanager
async def chat_pipeline_patches(
    gen_result, *, variable_injection=False, max_turns=50, script_content="Script"
):
    with (
        patch("services.script_lab.set_rls_context", new_callable=AsyncMock),
        patch("services.script_lab.settings") as mock_settings,
        patch(
            "services.script_lab.load_script_for_context", new_callable=AsyncMock
        ) as mock_load_script,
        patch("services.script_generation.ScriptGenerationService") as mock_gen_cls,
    ):
        mock_settings.SCRIPT_LAB_MAX_TURNS = max_turns
        mock_settings.VARIABLE_INJECTION_ENABLED = variable_injection
        mock_script = MagicMock()
        mock_script.content = script_content
        mock_load_script.return_value = mock_script
        mock_gen_cls.return_value = mock_gen_service(gen_result)
        yield {"gen_cls": mock_gen_cls, "settings": mock_settings}


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def lab_service(mock_session):
    from services.script_lab import ScriptLabService

    return ScriptLabService(mock_session)


@pytest.fixture
def sample_session():
    return make_lab_session()


@pytest.fixture
def sample_source_attribution():
    return make_source_attribution()


@pytest.fixture
def sample_raw_chunks():
    return [
        make_raw_chunk(),
        make_raw_chunk(
            chunk_id=43,
            metadata={
                "source_file": "pricing_guide.docx",
                "page_number": 1,
                "chunk_index": 0,
            },
            content="Our enterprise plan starts at $299 per month with full API access.",
            similarity=0.85,
        ),
        make_raw_chunk(
            chunk_id=44,
            metadata={"source_file": "faq.md", "page_number": None, "chunk_index": 2},
            content="We offer a 30-day money-back guarantee on all plans.",
            similarity=0.78,
        ),
    ]
