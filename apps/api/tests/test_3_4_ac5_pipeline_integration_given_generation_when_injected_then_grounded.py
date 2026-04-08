"""Story 3.4 AC5: Pipeline Integration.

Tests that variable injection integrates correctly with the
script generation pipeline, grounding queries with rendered text.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from conftest_3_4 import (
    make_lead,
    make_lead_with_custom_fields,
    make_agent,
    make_script_with_variables,
    make_lead_dict,
    TEST_ORG,
)
from services.variable_injection import VariableInjectionService, RenderResult
from services.script_generation import ScriptGenerationService


@pytest.mark.asyncio
class TestAC5PipelineIntegration:
    @pytest.mark.p1
    async def test_3_4_021_given_lead_and_script_ids_when_generated_then_injection_runs(
        self, injection_service
    ):
        lead = make_lead_dict(name="Sarah")
        template = "Tell me about products for {{lead_name}}"
        result = await injection_service.render_template(template, lead)
        assert "Sarah" in result.rendered_text
        assert "{{lead_name}}" not in result.rendered_text
        assert result.was_rendered is True

    @pytest.mark.p1
    async def test_3_4_022_given_rendered_query_when_rag_retrieves_then_uses_rendered_text(
        self, injection_service
    ):
        lead = make_lead_dict(name="Marcus")
        template = "What solutions for {{lead_name}}?"
        result = await injection_service.render_template(template, lead)
        rendered = result.rendered_text
        assert rendered == "What solutions for Marcus?"
        assert "lead_name" in result.resolved_variables

    @pytest.mark.p1
    async def test_3_4_023_given_no_lead_id_when_generated_then_backward_compatible(
        self,
    ):
        mock_llm = AsyncMock()
        mock_embedding = AsyncMock()
        mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_session = AsyncMock()

        service = ScriptGenerationService(
            llm_service=mock_llm,
            embedding_service=mock_embedding,
            session=mock_session,
            redis_client=AsyncMock(),
        )

        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch.object(
                service,
                "_check_cache_by_key",
                new_callable=AsyncMock,
                return_value=None,
            ):
                result = await service.generate_response(
                    query="Tell me about pricing",
                    org_id=TEST_ORG,
                    lead_id=None,
                    script_id=None,
                )
                assert result is not None
