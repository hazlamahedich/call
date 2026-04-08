"""AC1: Claim extraction and verification tests."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from services.factual_hook import FactualHookService, ClaimVerification
from tests.conftest_3_6 import make_claim_verification


@pytest.mark.asyncio
class TestClaimExtraction:
    async def test_3_6_unit_001_given_numbers_when_extracting_then_claims_found(
        self, factual_hook_service
    ):
        response = "Our revenue grew 32% in Q3. We have over 5000 active users."
        claims = factual_hook_service._extract_claims(response)
        assert len(claims) >= 1
        assert any("32%" in c or "5000" in c for c in claims)

    async def test_3_6_unit_002_given_superlatives_when_extracting_then_claims_found(
        self, factual_hook_service
    ):
        response = "Our service is faster than the competition by 50 milliseconds."
        claims = factual_hook_service._extract_claims(response)
        assert len(claims) >= 1

    async def test_3_6_unit_003_given_greeting_when_extracting_then_empty(
        self, factual_hook_service
    ):
        response = "Hello! How are you today?"
        claims = factual_hook_service._extract_claims(response)
        assert claims == []

    async def test_3_6_unit_003b_given_mixed_when_extracting_then_only_claims(
        self, factual_hook_service
    ):
        response = "Hello there! Our revenue grew 32% in Q3. Thanks for asking."
        claims = factual_hook_service._extract_claims(response)
        assert len(claims) == 1
        assert "32%" in claims[0]

    async def test_3_6_unit_003c_given_filler_when_extracting_then_excluded(
        self, factual_hook_service
    ):
        response = "We will get back to you by end of day. You must try our service."
        claims = factual_hook_service._extract_claims(response)
        assert claims == []

    async def test_3_6_unit_004_given_matching_chunks_when_verifying_then_supported(
        self, factual_hook_service, mock_session
    ):
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = [
                {"chunk_id": 1, "content": "Revenue grew 32%", "similarity": 0.85}
            ]
            result = await factual_hook_service._verify_claim(
                "Our revenue grew 32%.",
                "org-123",
                None,
                0.75,
            )
            assert result.is_supported is True

    async def test_3_6_unit_005_given_no_chunks_when_verifying_then_unsupported(
        self, factual_hook_service
    ):
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []
            result = await factual_hook_service._verify_claim(
                "We made $50 million.",
                "org-123",
                None,
                0.75,
            )
            assert result.is_supported is False

    async def test_3_6_unit_006_given_verification_when_scoped_then_org_id_passed(
        self, factual_hook_service
    ):
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []
            await factual_hook_service._verify_claim(
                "Claim text.",
                "org-target",
                [42],
                0.75,
            )
            args, kwargs = mock_search.call_args
            assert args[2] == "org-target"
            assert kwargs.get("knowledge_base_ids") == [42]
