"""AC2: Self-correction loop tests."""

from unittest.mock import AsyncMock, patch

import pytest

from services.factual_hook import (
    FactualHookService,
    ClaimVerification,
    NO_KNOWLEDGE_FALLBACK,
)


@pytest.mark.asyncio
class TestSelfCorrection:
    async def test_3_6_unit_007_given_unsupported_when_correcting_then_reprompted(
        self, factual_hook_service, mock_llm
    ):
        unsupported = ClaimVerification(
            claim_text="We serve 50000 users.", is_supported=False, supporting_chunks=[]
        )
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await factual_hook_service._correct_response(
                "We serve 50000 users across 12 countries.",
                [unsupported],
                [{"content": "Actual data about company"}],
                "Tell me about your company",
            )
            mock_llm.generate.assert_called_once()
            assert result is not None

    async def test_3_6_unit_008_given_corrected_when_passing_then_stops(
        self, factual_hook_service, mock_llm, mock_embedding
    ):
        call_count = {"n": 0}

        async def mock_search(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                return []
            return [{"chunk_id": 1, "content": "data", "similarity": 0.85}]

        with patch(
            "services.factual_hook.search_knowledge_chunks", side_effect=mock_search
        ):
            mock_llm.generate.return_value = "Our supported revenue data."
            result = await factual_hook_service.verify_and_correct(
                response="Our revenue grew 99% last quarter.",
                source_chunks=[{"content": "Revenue data"}],
                query="revenue info",
                org_id="org-1",
                max_corrections=2,
            )
            assert result.was_corrected is True
            assert result.correction_count >= 1

    async def test_3_6_unit_009_given_max_corrections_when_exhausted_then_fallback(
        self, factual_hook_service, mock_llm, mock_embedding
    ):
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            mock_llm.generate.return_value = (
                "Still has unsupported claims about 50000 users."
            )
            result = await factual_hook_service.verify_and_correct(
                response="We serve 50000 users across 12 countries.",
                source_chunks=[],
                query="user count",
                org_id="org-1",
                max_corrections=2,
            )
            assert result.correction_count == 2
            assert NO_KNOWLEDGE_FALLBACK in result.final_response

    async def test_3_6_unit_010_given_all_supported_when_verifying_then_no_correction(
        self, factual_hook_service, mock_embedding
    ):
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[
                {"chunk_id": 1, "content": "Revenue 32%", "similarity": 0.90}
            ],
        ):
            result = await factual_hook_service.verify_and_correct(
                response="Our revenue grew 32% in Q3.",
                source_chunks=[{"content": "Revenue data"}],
                query="revenue",
                org_id="org-1",
            )
            assert result.was_corrected is False
            assert result.correction_count == 0
