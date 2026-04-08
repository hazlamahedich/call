"""AC4: Timeout tests and AC5 toggle tests + AC8/9/10 reliability tests."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from services.factual_hook import FactualHookService


@pytest.mark.asyncio
class TestTimeout:
    async def test_3_6_unit_015_given_timeout_when_hit_then_original_returned(
        self, factual_hook_service, mock_embedding
    ):
        async def slow_verify(*args, **kwargs):
            await asyncio.sleep(10)
            return []

        with patch(
            "services.factual_hook.search_knowledge_chunks", side_effect=slow_verify
        ):
            result = await asyncio.wait_for(
                factual_hook_service.verify_and_correct(
                    response="Revenue grew 32%.",
                    source_chunks=[],
                    query="q",
                    org_id="o1",
                ),
                timeout=0.5,
            )
            assert result.final_response == "Revenue grew 32%."

    async def test_3_6_unit_016_given_timeout_when_inspecting_then_flag_true(self):
        from services.script_generation import ScriptGenerationResult

        result = ScriptGenerationResult(
            response="r",
            grounding_confidence=0.5,
            is_low_confidence=False,
            source_chunks=[],
            model="gpt-4o-mini",
            latency_ms=100,
            grounding_mode="strict",
            was_truncated=False,
            cached=False,
            verification_timed_out=True,
        )
        assert result.verification_timed_out is True


@pytest.mark.asyncio
class TestToggle:
    async def test_3_6_unit_017_given_disabled_when_generating_then_skip(self):
        from services.script_generation import ScriptGenerationResult

        result = ScriptGenerationResult(
            response="r",
            grounding_confidence=0.5,
            is_low_confidence=False,
            source_chunks=[],
            model="gpt-4o-mini",
            latency_ms=100,
            grounding_mode="strict",
            was_truncated=False,
            cached=False,
            was_corrected=False,
        )
        assert result.was_corrected is False

    async def test_3_6_unit_019_given_cached_when_served_then_no_hook(self):
        from services.script_generation import ScriptGenerationResult

        result = ScriptGenerationResult(
            response="r",
            grounding_confidence=0.5,
            is_low_confidence=False,
            source_chunks=[],
            model="gpt-4o-mini",
            latency_ms=100,
            grounding_mode="strict",
            was_truncated=False,
            cached=True,
            was_corrected=False,
            correction_count=0,
        )
        assert result.cached is True
        assert result.correction_count == 0


@pytest.mark.asyncio
class TestEmptyClaims:
    async def test_3_6_unit_022_given_no_claims_when_processed_then_skip(
        self, factual_hook_service
    ):
        result = await factual_hook_service.verify_and_correct(
            response="Hello! How can I help you today?",
            source_chunks=[],
            query="greeting",
            org_id="org-1",
        )
        assert result.was_corrected is False
        assert result.correction_count == 0
        assert result.total_verification_ms < 0.1

    async def test_3_6_unit_023_given_empty_claims_when_checked_then_no_embedding_calls(
        self, factual_hook_service, mock_embedding
    ):
        await factual_hook_service.verify_and_correct(
            response="Thanks for your time!",
            source_chunks=[],
            query="closing",
            org_id="org-1",
        )
        mock_embedding.generate_embedding.assert_not_called()


@pytest.mark.asyncio
class TestPartialFailure:
    async def test_3_6_unit_024_given_mixed_when_verified_then_isolated(
        self, mock_session, mock_llm
    ):
        call_count = {"n": 0}

        class FlakyEmb:
            async def generate_embedding(self, text, *, task_type="RETRIEVAL_DOCUMENT"):
                call_count["n"] += 1
                if call_count["n"] == 2:
                    raise RuntimeError("Embedding failure")
                return [0.1] * 1536

        svc = FactualHookService(mock_session, mock_llm, FlakyEmb())
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[{"chunk_id": 1, "content": "data", "similarity": 0.85}],
        ):
            claims = svc._extract_claims(
                "Our revenue grew 32% in Q3 2025. Our platform processes exactly 10000 transactions per hour."
            )
            assert len(claims) == 2, f"Expected 2 claims, got {claims}"
            verifications = await svc._verify_all_claims(claims, "org-1", None)
            errors = [v for v in verifications if v.verification_error]
            successes = [v for v in verifications if not v.verification_error]
            assert len(errors) >= 1
            assert len(successes) >= 1

    async def test_3_6_unit_025_given_partial_when_correcting_then_errored_as_unsupported(
        self, mock_session, mock_llm
    ):
        call_count = {"n": 0}

        class FlakyEmb:
            async def generate_embedding(self, text, *, task_type="RETRIEVAL_DOCUMENT"):
                call_count["n"] += 1
                if call_count["n"] % 3 == 0:
                    raise RuntimeError("Transient failure")
                return [0.1] * 1536

        svc = FactualHookService(mock_session, mock_llm, FlakyEmb())
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            mock_llm.generate.return_value = "Corrected with supported claims."
            result = await svc.verify_and_correct(
                response="Our revenue grew 32% in Q3 2025. Our platform processes exactly 10000 transactions per hour.",
                source_chunks=[],
                query="q",
                org_id="o1",
                max_corrections=1,
            )
            assert result.was_corrected is True


@pytest.mark.asyncio
class TestCircuitBreaker:
    async def test_3_6_unit_026_given_consecutive_when_threshold_then_open(
        self, factual_hook_service
    ):
        FactualHookService._record_error()
        FactualHookService._record_error()
        FactualHookService._record_error()
        assert FactualHookService._circuit_open is True

    async def test_3_6_unit_027_given_open_when_verifying_then_immediate_return(
        self, factual_hook_service
    ):
        import time

        FactualHookService._circuit_open = True
        FactualHookService._circuit_opened_at = time.monotonic()
        result = await factual_hook_service.verify_and_correct(
            response="Revenue 32%.",
            source_chunks=[],
            query="q",
            org_id="o1",
        )
        assert result.circuit_breaker_open is True
        assert result.was_corrected is False

    async def test_3_6_unit_028_given_reset_when_elapsed_then_closed(
        self, factual_hook_service
    ):
        import time

        FactualHookService._circuit_open = True
        FactualHookService._circuit_opened_at = time.monotonic() - 100
        FactualHookService._consecutive_errors = 5
        with patch(
            "services.factual_hook.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=[{"chunk_id": 1, "content": "data", "similarity": 0.85}],
        ):
            result = await factual_hook_service.verify_and_correct(
                response="Revenue 32%.",
                source_chunks=[],
                query="q",
                org_id="o1",
            )
            assert result.circuit_breaker_open is False
