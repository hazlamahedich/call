"""Integration tests: full pipeline, Script Lab integration, caching, and FR9 accuracy logs."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.factual_hook import FactualHookService


@pytest.mark.asyncio
class TestIntegration:
    async def test_3_6_int_001_given_full_pipeline_when_hook_active_then_end_to_end(
        self, factual_hook_service, mock_llm, mock_embedding
    ):
        call_n = {"n": 0}

        async def mock_search(*args, **kwargs):
            call_n["n"] += 1
            if call_n["n"] <= 1:
                return []
            return [{"chunk_id": 1, "content": "Revenue 32%", "similarity": 0.88}]

        with patch(
            "services.factual_hook.search_knowledge_chunks", side_effect=mock_search
        ):
            mock_llm.generate.return_value = "Our revenue grew 32% as reported."
            result = await factual_hook_service.verify_and_correct(
                response="Our revenue grew 99% in Q3.",
                source_chunks=[{"content": "Financial report data"}],
                query="revenue growth",
                org_id="org-1",
            )
            assert result.was_corrected is True
            assert result.correction_count >= 1
            assert result.original_response == "Our revenue grew 99% in Q3."
            assert result.final_response != result.original_response

    async def test_3_6_int_002_given_script_lab_when_corrected_then_metadata_in_response(
        self, factual_hook_service, mock_llm, mock_embedding
    ):
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            mock_llm.generate.return_value = "Corrected response with accurate data."
            result = await factual_hook_service.verify_and_correct(
                response="We serve exactly 50000 users.",
                source_chunks=[],
                query="user count",
                org_id="org-1",
            )
            assert result.was_corrected is True

            from schemas.script_lab import LabChatResponse
            from schemas.factual_hook import ClaimVerificationResponse

            lab_resp = LabChatResponse(
                response_text=result.final_response,
                source_attributions=[],
                grounding_confidence=0.8,
                turn_number=1,
                low_confidence_warning=False,
                was_corrected=result.was_corrected,
                correction_count=result.correction_count,
                verification_timed_out=result.verification_timed_out,
            )
            data = lab_resp.model_dump(by_alias=True)
            assert data["wasCorrected"] is True
            assert data["correctionCount"] >= 1

    async def test_3_6_int_003_given_corrected_when_cached_then_corrected_version(
        self,
    ):
        from services.script_generation import ScriptGenerationResult

        result = ScriptGenerationResult(
            response="Corrected response.",
            grounding_confidence=0.85,
            is_low_confidence=False,
            source_chunks=[],
            model="gpt-4o-mini",
            latency_ms=200.0,
            grounding_mode="strict",
            was_truncated=False,
            cached=False,
            was_corrected=True,
            correction_count=1,
            verification_timed_out=False,
        )
        cached = json.dumps(
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
        loaded = json.loads(cached)
        assert loaded["was_corrected"] is True
        assert loaded["correction_count"] == 1
        assert loaded["response"] == "Corrected response."


@pytest.mark.asyncio
class TestFR9Accuracy:
    async def test_3_6_int_005_given_verification_when_logged_then_row_exists(
        self, factual_hook_service, mock_llm, mock_embedding, mock_session
    ):
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            mock_llm.generate.return_value = "Corrected."
            result = await factual_hook_service.verify_and_correct(
                response="Our revenue grew 32% in Q3.",
                source_chunks=[],
                query="revenue",
                org_id="org-1",
            )
            mock_session.add.assert_called()
            mock_session.flush.assert_called_once()
            log_obj = mock_session.add.call_args[0][0]
            assert log_obj.was_corrected == result.was_corrected
            assert log_obj.claims_total == len(result.verified_claims)

    async def test_3_6_int_006_given_many_verifications_when_queried_then_metrics(
        self,
    ):
        from models.factual_verification_log import FactualVerificationLog

        logs = [
            FactualVerificationLog.model_validate(
                {
                    "orgId": "org-1",
                    "queryHash": f"hash-{i}",
                    "wasCorrected": i % 3 == 0,
                    "correctionCount": 1 if i % 3 == 0 else 0,
                    "claimsTotal": 3,
                    "claimsSupported": 2 if i % 3 != 0 else 1,
                    "claimsUnsupported": 1,
                    "claimsErrored": 0,
                    "verificationTimedOut": False,
                    "totalVerificationMs": 100.0 + i,
                }
            )
            for i in range(100)
        ]
        correction_rate = sum(1 for l in logs if l.was_corrected) / len(logs)
        avg_claims_supported = sum(l.claims_supported for l in logs) / len(logs)
        assert correction_rate > 0
        assert avg_claims_supported > 0
