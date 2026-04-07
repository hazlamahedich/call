"""Story 3.3: Grounding Mode Tests.

Tests [3.3-UNIT-055] through [3.3-UNIT-057].
"""

from unittest.mock import AsyncMock, patch

import pytest

from conftest_3_3 import make_chunks


@pytest.mark.asyncio
@pytest.mark.p3
class TestGroundingModes:
    async def test_3_3_055_given_balanced_mode_when_generating_then_prompt_includes_general_knowledge(
        self, service, mock_llm
    ):
        """[3.3-UNIT-055] Balanced mode prompt includes [General knowledge] instruction."""
        chunks = make_chunks(1, 0.8)
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            await service.generate_response("test", "org_1", grounding_mode="balanced")

        call_args = mock_llm.generate.call_args
        system = (
            call_args.kwargs.get("system")
            or call_args[1].get("system")
            or call_args[0][0]
        )
        assert "[General knowledge]" in system

    async def test_3_3_056_given_creative_mode_when_generating_then_prompt_includes_additional_context(
        self, service, mock_llm
    ):
        """[3.3-UNIT-056] Creative mode prompt includes [Additional context] instruction."""
        chunks = make_chunks(1, 0.8)
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            await service.generate_response("test", "org_1", grounding_mode="creative")

        call_args = mock_llm.generate.call_args
        system = (
            call_args.kwargs.get("system")
            or call_args[1].get("system")
            or call_args[0][0]
        )
        assert "[Additional context]" in system

    async def test_3_3_057_given_creative_mode_thin_kb_when_scoring_then_confidence_applies(
        self, service
    ):
        """[3.3-UNIT-057] Creative mode with thin KB still has confidence scoring."""
        chunks = make_chunks(1, 0.3, "thin content")
        with patch(
            "services.script_generation.search_knowledge_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ):
            result = await service.generate_response(
                "test", "org_1", grounding_mode="creative"
            )

        assert result.grounding_confidence >= 0.0
        assert result.grounding_mode == "creative"
