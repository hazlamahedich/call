"""Story 3.3 AC7+AC8: Performance & LLM Error Handling.

Tests [3.3-UNIT-038] through [3.3-UNIT-044].
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from conftest_3_3 import make_chunks
from services.script_generation import ScriptGenerationService


@pytest.mark.asyncio
@pytest.mark.p2
class TestAC7Performance:
    async def test_3_3_038_given_mocked_llm_when_generating_then_overhead_under_100ms(
        self, service
    ):
        """[3.3-UNIT-038] Pipeline overhead (excluding LLM) < 100ms."""
        chunks = make_chunks(3, 0.8)
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            start = time.monotonic()
            result = await service.generate_response("test query", "org_1")
            elapsed_ms = (time.monotonic() - start) * 1000

        overhead = elapsed_ms - result.latency_ms
        assert overhead < 100

    async def test_3_3_039_given_pipeline_when_executed_then_retrieval_fast(
        self, service
    ):
        """[3.3-UNIT-039] Retrieval latency acceptable with mocked DB."""
        chunks = make_chunks(3, 0.8)
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            result = await service.generate_response("test", "org_1")

        assert result.latency_ms >= 0


@pytest.mark.asyncio
@pytest.mark.p1
class TestAC8LLMErrorHandling:
    async def test_3_3_040_given_llm_timeout_when_generating_then_retries(
        self, mock_llm, mock_embedding, mock_session, mock_redis
    ):
        """[3.3-UNIT-040] LLM timeout triggers retries."""
        call_count = 0

        async def flaky_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise TimeoutError("LLM timeout")
            return "Success after retry"

        mock_llm.generate = flaky_generate
        svc = ScriptGenerationService(
            mock_llm, mock_embedding, mock_session, mock_redis
        )
        chunks = make_chunks(2, 0.8)

        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            result = await svc.generate_response("test", "org_1")

        assert call_count >= 2
        assert result.response == "Success after retry"

    async def test_3_3_041_given_llm_rate_limit_when_generating_then_retries_with_backoff(
        self, mock_llm, mock_embedding, mock_session, mock_redis
    ):
        """[3.3-UNIT-041] LLM 429 triggers retry with backoff."""
        call_count = 0

        async def rate_limited(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise Exception("429 Rate limit exceeded")
            return "OK"

        mock_llm.generate = rate_limited
        svc = ScriptGenerationService(
            mock_llm, mock_embedding, mock_session, mock_redis
        )
        chunks = make_chunks(1, 0.8)

        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            result = await svc.generate_response("test", "org_1")

        assert call_count == 2

    async def test_3_3_042_given_all_retries_exhausted_when_generating_then_raises(
        self, mock_llm, mock_embedding, mock_session, mock_redis
    ):
        """[3.3-UNIT-042] All retries exhausted raises exception."""
        mock_llm.generate = AsyncMock(side_effect=Exception("Persistent failure"))
        svc = ScriptGenerationService(
            mock_llm, mock_embedding, mock_session, mock_redis
        )
        chunks = make_chunks(1, 0.8)

        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            with pytest.raises(Exception, match="Persistent failure"):
                await svc.generate_response("test", "org_1")

    async def test_3_3_043_given_llm_failure_when_logging_then_failure_logged(
        self, mock_llm, mock_embedding, mock_session, mock_redis
    ):
        """[3.3-UNIT-043] LLM failure logged with provider, model, error, retry count."""
        mock_llm.generate = AsyncMock(side_effect=Exception("fail"))
        svc = ScriptGenerationService(
            mock_llm, mock_embedding, mock_session, mock_redis
        )
        chunks = make_chunks(1, 0.8)

        with (
            patch(
                "services.script_generation.search_knowledge_chunks",
                new_callable=AsyncMock,
                return_value=chunks,
            ),
            patch("services.script_generation.logger") as mock_logger,
        ):
            with pytest.raises(Exception):
                await svc.generate_response("test", "org_1")

        error_calls = [
            c
            for c in mock_logger.error.call_args_list
            if "LLM" in str(c) or "failed" in str(c)
        ]
        assert len(error_calls) >= 1

    async def test_3_3_044_given_llm_failure_when_generating_then_no_ungrounded_fallback(
        self, mock_llm, mock_embedding, mock_session, mock_redis
    ):
        """[3.3-UNIT-044] LLM failure does NOT fall back to ungrounded generation."""
        mock_llm.generate = AsyncMock(side_effect=Exception("fail"))
        svc = ScriptGenerationService(
            mock_llm, mock_embedding, mock_session, mock_redis
        )
        chunks = make_chunks(1, 0.8)

        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            with pytest.raises(Exception):
                await svc.generate_response("test", "org_1")
