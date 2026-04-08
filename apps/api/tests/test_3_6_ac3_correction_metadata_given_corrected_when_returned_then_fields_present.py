"""AC3: Correction metadata tests."""

from unittest.mock import AsyncMock, patch

import pytest

from services.factual_hook import FactualHookService


@pytest.mark.asyncio
class TestCorrectionMetadata:
    async def test_3_6_unit_011_given_corrected_when_inspecting_then_was_corrected_true(
        self, factual_hook_service, mock_llm, mock_embedding
    ):
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            mock_llm.generate.return_value = "Corrected response."
            result = await factual_hook_service.verify_and_correct(
                response="Our revenue grew 32% in Q3.",
                source_chunks=[],
                query="rev",
                org_id="o1",
            )
            assert result.was_corrected is True

    async def test_3_6_unit_012_given_two_corrections_when_inspecting_then_count_2(
        self, factual_hook_service, mock_llm, mock_embedding
    ):
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            mock_llm.generate.return_value = "Still has 50000 users claim."
            result = await factual_hook_service.verify_and_correct(
                response="We serve 50000 users.",
                source_chunks=[],
                query="q",
                org_id="o1",
            )
            assert result.correction_count == 2

    async def test_3_6_unit_013_given_script_lab_result_when_serialized_then_camel_case(
        self,
    ):
        from schemas.script_lab import LabChatResponse
        from schemas.factual_hook import ClaimVerificationResponse

        resp = LabChatResponse(
            response_text="test",
            source_attributions=[],
            grounding_confidence=0.9,
            turn_number=1,
            low_confidence_warning=False,
            was_corrected=True,
            correction_count=1,
            verification_timed_out=False,
            verified_claims=[
                ClaimVerificationResponse(
                    claim_text="c", is_supported=True, max_similarity=0.8
                )
            ],
        )
        data = resp.model_dump(by_alias=True)
        assert "wasCorrected" in data
        assert "correctionCount" in data
        assert "verifiedClaims" in data

    async def test_3_6_unit_014b_given_cached_corrected_when_served_then_has_metadata(
        self,
    ):
        from services.script_generation import ScriptGenerationResult

        result = ScriptGenerationResult(
            response="corrected",
            grounding_confidence=0.8,
            is_low_confidence=False,
            source_chunks=[],
            model="gpt-4o-mini",
            latency_ms=100.0,
            grounding_mode="strict",
            was_truncated=False,
            cached=False,
            was_corrected=True,
            correction_count=1,
            verification_timed_out=False,
        )
        import json

        data = json.loads(
            json.dumps(
                {
                    "response": result.response,
                    "grounding_confidence": result.grounding_confidence,
                    "is_low_confidence": result.is_low_confidence,
                    "source_chunks": result.source_chunks,
                    "model": result.model,
                    "grounding_mode": result.grounding_mode,
                    "was_truncated": result.was_truncated,
                    "cost_estimate": result.cost_estimate,
                    "was_corrected": result.was_corrected,
                    "correction_count": result.correction_count,
                    "verification_timed_out": result.verification_timed_out,
                }
            )
        )
        assert data["was_corrected"] is True
        assert data["correction_count"] == 1

    async def test_3_6_unit_014c_given_old_cache_when_deserialized_then_defaults(self):
        from services.script_generation import ScriptGenerationResult
        import json

        old_cache = json.dumps(
            {
                "response": "old",
                "grounding_confidence": 0.5,
                "is_low_confidence": False,
                "source_chunks": [],
                "model": "gpt-4o-mini",
                "grounding_mode": "strict",
                "was_truncated": False,
                "cost_estimate": 0.0,
            }
        )
        cached_data = json.loads(old_cache)
        cached_data.setdefault("was_corrected", False)
        cached_data.setdefault("correction_count", 0)
        cached_data.setdefault("verification_timed_out", False)
        cached_data["latency_ms"] = 50.0
        cached_data["cached"] = True
        result = ScriptGenerationResult(**cached_data)
        assert result.was_corrected is False
        assert result.correction_count == 0
        assert result.verification_timed_out is False
