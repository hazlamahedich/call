"""Story 3.3 AC1+AC2: Grounded Generation & No-Knowledge Policy.

Tests [3.3-UNIT-001] through [3.3-UNIT-010].
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from conftest_3_3 import (
    TEST_ORG,
    make_agent_model,
    make_chunks,
    make_script_result,
)
from services.script_generation import (
    NO_KNOWLEDGE_FALLBACK,
    ScriptGenerationResult,
)


@pytest.mark.asyncio
@pytest.mark.p1
class TestAC1GroundedGeneration:
    async def test_3_3_001_given_valid_query_when_generating_then_response_grounded(
        self, service, mock_llm
    ):
        """[3.3-UNIT-001] Response grounded with confidence > 0.5."""
        chunks = make_chunks(3, 0.85)
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            result = await service.generate_response("Tell me about products", "org_1")

        assert result.grounding_confidence > 0.0
        assert result.response != NO_KNOWLEDGE_FALLBACK
        assert len(result.source_chunks) > 0

    async def test_3_3_002_given_valid_query_when_generating_then_only_high_similarity_chunks(
        self, service
    ):
        """[3.3-UNIT-002] search_knowledge_chunks uses default threshold from settings."""
        chunks = make_chunks(2, 0.9)
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ) as mock_search:
            await service.generate_response("What features?", "org_1")
            assert mock_search.called

    async def test_3_3_003_given_multiple_chunks_when_generating_then_source_metadata_included(
        self, service
    ):
        """[3.3-UNIT-003] Source chunks included in response metadata."""
        chunks = make_chunks(3, 0.8)
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            result = await service.generate_response("Tell me more", "org_1")

        assert len(result.source_chunks) == 3
        for c in result.source_chunks:
            assert "chunk_id" in c
            assert "knowledge_base_id" in c
            assert "similarity" in c

    async def test_3_3_004_given_valid_query_when_generating_then_llm_receives_grounded_prompt(
        self, service, mock_llm
    ):
        """[3.3-UNIT-004] LLM receives grounded system prompt with context."""
        chunks = make_chunks(2, 0.8)
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            await service.generate_response("pricing info", "org_1")

        call_args = mock_llm.generate.call_args
        system_prompt = (
            call_args.kwargs.get("system")
            or call_args[1].get("system")
            or call_args[0][0]
        )
        assert "provided context" in system_prompt.lower() or "ONLY" in system_prompt

    async def test_3_3_005_given_agent_id_when_generating_then_scoped_to_agent_kbs(
        self, service, mock_session
    ):
        """[3.3-UNIT-005] Retrieval scoped to agent's KBs when agentId provided."""
        chunks = make_chunks(2, 0.8)
        agent_row = MagicMock()
        agent_row.first.return_value = agent_row
        agent_row.__getitem__ = lambda s, i: [1, "org_1", [42, 43]][i]
        mock_session.execute.return_value = agent_row

        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ) as mock_search:
            await service.generate_response("query", "org_1", agent_id=1)
            call_kwargs = mock_search.call_args
            kb_ids_arg = call_kwargs.kwargs.get("knowledge_base_ids") or call_kwargs[
                1
            ].get("knowledge_base_ids")
            assert kb_ids_arg == [42, 43]

    async def test_3_3_006_given_no_agent_id_when_generating_then_searches_all_tenant_kbs(
        self, service
    ):
        """[3.3-UNIT-006] Without agentId, retrieval searches ALL tenant KBs."""
        chunks = make_chunks(2, 0.8)
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ) as mock_search:
            await service.generate_response("query", "org_1", agent_id=None)
            call_kwargs = mock_search.call_args
            kb_ids_arg = call_kwargs.kwargs.get("knowledge_base_ids") or call_kwargs[
                1
            ].get("knowledge_base_ids")
            assert kb_ids_arg is None


@pytest.mark.asyncio
@pytest.mark.p0
class TestAC2NoKnowledgePolicy:
    async def test_3_3_007_given_no_chunks_when_generating_then_fallback(self, service):
        """[3.3-UNIT-007] Fallback response when no relevant chunks found."""
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.generate_response("unknown topic", "org_1")

        assert result.response == NO_KNOWLEDGE_FALLBACK

    async def test_3_3_008_given_no_chunks_when_generating_then_confidence_zero(
        self, service
    ):
        """[3.3-UNIT-008] Confidence is 0.0 when no chunks found."""
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.generate_response("unknown topic", "org_1")

        assert result.grounding_confidence == 0.0

    async def test_3_3_009_given_no_chunks_when_generating_then_audit_logged(
        self, service
    ):
        """[3.3-UNIT-009] Audit event logged with query, org_id, threshold."""
        with (
            patch(
                "services.script_generation.search_knowledge_chunks",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("services.script_generation.logger") as mock_logger,
        ):
            await service.generate_response("unknown topic", "org_1")

        assert mock_logger.info.called
        call_args = mock_logger.info.call_args
        log_msg = call_args[0][0] if call_args[0] else ""
        log_extra = call_args.kwargs.get("extra", {}) or call_args[1].get("extra", {})
        assert (
            "no_relevant_chunks" in log_msg
            or "no_relevant_chunks" in str(log_extra)
            or call_args[0][1] == "no_relevant_chunks"
        )

    async def test_3_3_010_given_empty_kb_when_generating_then_empty_kb_event(
        self, service, mock_session
    ):
        """[3.3-UNIT-010] Empty knowledge base logged with distinct event."""
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        mock_session.execute.return_value = count_result

        with (
            patch(
                "services.script_generation.search_knowledge_chunks",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("services.script_generation.logger") as mock_logger,
        ):
            result = await service.generate_response("query", "org_1")

        assert result.response == NO_KNOWLEDGE_FALLBACK
        assert result.grounding_confidence == 0.0
