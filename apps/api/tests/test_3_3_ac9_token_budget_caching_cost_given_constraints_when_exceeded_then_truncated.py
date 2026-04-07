"""Story 3.3 AC9+AC10+AC11: Token Budget, Caching & Cost Tracking.

Tests [3.3-UNIT-045] through [3.3-UNIT-054].
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from conftest_3_3 import make_chunks
from config.settings import settings
from services.script_generation import ScriptGenerationService


@pytest.mark.p2
class TestAC9TokenBudget:
    def test_3_3_045_given_exceeds_budget_when_building_prompt_then_truncates(self):
        """[3.3-UNIT-045] Context exceeding budget truncated from lowest-similarity end."""
        svc = ScriptGenerationService.__new__(ScriptGenerationService)
        chunks = [
            {
                "chunk_id": i,
                "knowledge_base_id": 1,
                "content": "word " * 500,
                "similarity": 0.9 - i * 0.1,
                "metadata": {},
            }
            for i in range(10)
        ]
        with (
            patch.object(settings, "AI_LLM_MAX_TOKENS", 200),
            patch.object(settings, "TOKEN_RESERVATION", 50),
        ):
            _, _, was_truncated, _ = svc._build_grounded_prompt(
                "short query", chunks, "strict"
            )

        assert was_truncated is True

    def test_3_3_046_given_within_budget_when_building_prompt_then_no_truncation(self):
        """[3.3-UNIT-046] Context within budget → no truncation."""
        svc = ScriptGenerationService.__new__(ScriptGenerationService)
        chunks = make_chunks(2, 0.8, "short")
        with (
            patch.object(settings, "AI_LLM_MAX_TOKENS", 10000),
            patch.object(settings, "TOKEN_RESERVATION", 500),
        ):
            _, _, was_truncated, _ = svc._build_grounded_prompt(
                "query", chunks, "strict"
            )

        assert was_truncated is False


@pytest.mark.asyncio
@pytest.mark.p2
class TestAC9TokenBudgetAsync:
    async def test_3_3_047_given_tight_budget_when_generating_then_truncation_warning_logged(
        self, service
    ):
        """[3.3-UNIT-047] Truncation triggers warning with original vs truncated counts."""
        with (
            patch.object(settings, "AI_LLM_MAX_TOKENS", 100),
            patch.object(settings, "TOKEN_RESERVATION", 50),
            patch(
                "services.script_generation.search_knowledge_chunks",
                new_callable=AsyncMock,
                return_value=make_chunks(10, 0.8, "word " * 50),
            ),
            patch("services.script_generation.logger") as mock_logger,
        ):
            result = await service.generate_response("test", "org_1")

        assert result.was_truncated is True
        warn_calls = [
            c for c in mock_logger.warning.call_args_list if "truncat" in str(c).lower()
        ]
        assert len(warn_calls) >= 1

    async def test_3_3_048_given_tight_budget_when_generating_then_metadata_includes_truncation_flag(
        self, service
    ):
        """[3.3-UNIT-048] wasTruncated=true in metadata when truncation occurred."""
        with (
            patch.object(settings, "AI_LLM_MAX_TOKENS", 100),
            patch.object(settings, "TOKEN_RESERVATION", 50),
            patch(
                "services.script_generation.search_knowledge_chunks",
                new_callable=AsyncMock,
                return_value=make_chunks(10, 0.8, "word " * 50),
            ),
        ):
            result = await service.generate_response("test", "org_1")

        assert result.was_truncated is True


@pytest.mark.asyncio
@pytest.mark.p2
class TestAC10Caching:
    async def test_3_3_049_given_cache_hit_when_generating_then_returns_cached(
        self, service, mock_redis
    ):
        """[3.3-UNIT-049] Cache hit returns cached response with cached=true."""
        cached_data = json.dumps(
            {
                "response": "Cached response",
                "grounding_confidence": 0.9,
                "is_low_confidence": False,
                "source_chunks": [],
                "model": "gpt-4o-mini",
                "grounding_mode": "strict",
                "was_truncated": False,
                "cost_estimate": 0.0,
            }
        )
        mock_redis.get = AsyncMock(return_value=cached_data)

        result = await service.generate_response("cached query", "org_1")
        assert result.cached is True
        assert result.response == "Cached response"

    async def test_3_3_050_given_cache_miss_when_generating_then_result_cached(
        self, service, mock_redis
    ):
        """[3.3-UNIT-050] Cache miss → fresh generation → result cached."""
        chunks = make_chunks(1, 0.8)
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            result = await service.generate_response("new query", "org_1")

        assert result.cached is False
        assert mock_redis.setex.called

    async def test_3_3_051_given_config_update_when_invalidation_then_cache_cleared(
        self, service, mock_redis
    ):
        """[3.3-UNIT-051] Config update triggers cache invalidation."""

        class _AsyncIter:
            def __init__(self, items):
                self._it = iter(items)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self._it)
                except StopIteration:
                    raise StopAsyncIteration

        mock_redis.scan_iter = MagicMock(
            return_value=_AsyncIter(["script_gen:org_1:1:abc"])
        )
        await service.invalidate_cache("org_1", 1)
        assert mock_redis.delete.called

    async def test_3_3_052_given_no_redis_when_caching_then_graceful(
        self, mock_llm, mock_embedding, mock_session
    ):
        """[3.3-UNIT-052] No Redis → graceful degradation, no errors."""
        svc = ScriptGenerationService(
            mock_llm, mock_embedding, mock_session, redis_client=None
        )
        chunks = make_chunks(1, 0.8)
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            result = await svc.generate_response("test", "org_1")

        assert result.cached is False


@pytest.mark.asyncio
@pytest.mark.p2
class TestAC11CostTracking:
    async def test_3_3_053_given_success_when_logging_then_cost_included(self, service):
        """[3.3-UNIT-053] Cost estimate included in audit log."""
        chunks = make_chunks(2, 0.8)
        with (
            patch(
                "services.script_generation.search_knowledge_chunks",
                new_callable=AsyncMock,
                return_value=chunks,
            ),
            patch("services.script_generation.logger") as mock_logger,
        ):
            await service.generate_response("test", "org_1")

        info_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "generation_completed" in str(c)
        ]
        extra = info_calls[0].kwargs.get("extra", {}) or info_calls[0][1].get(
            "extra", {}
        )
        assert "cost_estimate" in extra

    async def test_3_3_054_given_tracking_disabled_when_generating_then_zero_cost(
        self, mock_llm, mock_embedding, mock_session, mock_redis
    ):
        """[3.3-UNIT-054] COST_TRACKING_ENABLED=false → cost is 0.0."""
        chunks = make_chunks(1, 0.8)
        with (
            patch(
                "services.script_generation.search_knowledge_chunks",
                new_callable=AsyncMock,
                return_value=chunks,
            ),
            patch.object(settings, "COST_TRACKING_ENABLED", False),
        ):
            svc = ScriptGenerationService(
                mock_llm, mock_embedding, mock_session, mock_redis
            )
            result = await svc.generate_response("test", "org_1")

        assert result.cost_estimate == 0.0
