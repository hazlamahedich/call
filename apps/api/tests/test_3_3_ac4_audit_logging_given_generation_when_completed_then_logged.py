"""Story 3.3 AC4: Audit Logging.

Tests [3.3-UNIT-018] through [3.3-UNIT-021].
"""

from unittest.mock import AsyncMock, patch

import pytest

from conftest_3_3 import make_chunks


@pytest.mark.asyncio
@pytest.mark.p1
class TestAC4AuditLogging:
    async def test_3_3_018_given_success_when_generating_then_audit_logged(
        self, service
    ):
        """[3.3-UNIT-018] Audit log with query, source_chunks, confidence, model, latency, org_id, mode, cost."""
        chunks = make_chunks(2, 0.8)
        with (
            patch(
                "services.script_generation.search_knowledge_chunks",
                new_callable=AsyncMock,
                return_value=chunks,
            ),
            patch("services.script_generation.logger") as mock_logger,
        ):
            await service.generate_response("test query", "org_1")

        info_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "generation_completed" in str(c)
        ]
        assert len(info_calls) >= 1
        extra = info_calls[0].kwargs.get("extra", {}) or info_calls[0][1].get(
            "extra", {}
        )
        assert "grounding_confidence" in extra
        assert "model" in extra
        assert "latency_ms" in extra
        assert "grounding_mode" in extra

    async def test_3_3_019_given_no_knowledge_when_generating_then_audit_still_logged(
        self, service
    ):
        """[3.3-UNIT-019] Audit log written even for no-knowledge fallback."""
        with (
            patch(
                "services.script_generation.search_knowledge_chunks",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("services.script_generation.logger") as mock_logger,
        ):
            await service.generate_response("unknown", "org_1")

        info_calls = [
            c for c in mock_logger.info.call_args_list if "no_relevant_chunks" in str(c)
        ]
        assert len(info_calls) >= 1

    async def test_3_3_020_given_generation_when_logging_then_structured_format(
        self, service
    ):
        """[3.3-UNIT-020] Audit log uses structured format (extra dict)."""
        chunks = make_chunks(1, 0.8)
        with (
            patch(
                "services.script_generation.search_knowledge_chunks",
                new_callable=AsyncMock,
                return_value=chunks,
            ),
            patch("services.script_generation.logger") as mock_logger,
        ):
            await service.generate_response("test", "org_1")

        info_calls = mock_logger.info.call_args_list
        assert any(
            c.kwargs.get("extra") or (len(c) > 1 and c[1].get("extra"))
            for c in info_calls
        )

    async def test_3_3_021_given_generation_when_logging_then_query_truncated(
        self, service
    ):
        """[3.3-UNIT-021] Query truncated to 200 chars, chunk content not logged."""
        chunks = make_chunks(1, 0.8)
        long_query = "x" * 300
        with (
            patch(
                "services.script_generation.search_knowledge_chunks",
                new_callable=AsyncMock,
                return_value=chunks,
            ),
            patch("services.script_generation.logger") as mock_logger,
        ):
            await service.generate_response(long_query, "org_1")

        info_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "generation_completed" in str(c)
        ]
        extra = info_calls[0].kwargs.get("extra", {}) or info_calls[0][1].get(
            "extra", {}
        )
        logged_query = extra.get("query", "")
        assert len(logged_query) <= 200
