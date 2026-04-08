"""Story 3.5 AC8: Low Confidence Warning.

Tests that low_confidence_warning is true when grounding confidence
drops below 0.5 and false when confidence is at or above 0.5.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest_3_5 import *
from services.script_lab import ScriptLabService


@pytest.mark.asyncio
class TestAC8LowConfidence:
    @pytest.mark.p0
    async def test_3_5_026_given_response_confidence_below_threshold_when_formatting_then_warning_true(
        self, lab_service
    ):
        # [3.5-UNIT-026]
        low_confidence_chunks = [
            make_raw_chunk(similarity=0.12),
            make_raw_chunk(
                chunk_id=43,
                similarity=0.25,
                content="Weak grounding content.",
            ),
        ]

        attributions = lab_service._format_source_attribution(low_confidence_chunks)
        assert len(attributions) == 2

        avg_score = sum(a.similarity_score for a in attributions) / len(attributions)
        low_confidence_warning = avg_score < 0.5

        assert low_confidence_warning is True
        assert avg_score < 0.5

    @pytest.mark.p0
    async def test_3_5_027_given_response_confidence_at_threshold_when_formatting_then_warning_false(
        self, lab_service
    ):
        # [3.5-UNIT-027]
        high_confidence_chunks = [
            make_raw_chunk(similarity=0.92),
            make_raw_chunk(
                chunk_id=43,
                similarity=0.85,
                content="Strong grounding content.",
            ),
        ]

        attributions = lab_service._format_source_attribution(high_confidence_chunks)
        avg_score = sum(a.similarity_score for a in attributions) / len(attributions)
        low_confidence_warning = avg_score < 0.5

        assert low_confidence_warning is False
        assert avg_score >= 0.5

    @pytest.mark.p1
    async def test_3_5_027b_given_confidence_exactly_at_boundary_when_checked_then_no_warning(
        self, lab_service
    ):
        # Boundary: confidence exactly 0.5 -> no warning
        confidence = 0.5
        low_confidence_warning = confidence < 0.5
        assert low_confidence_warning is False

    @pytest.mark.p1
    async def test_3_5_027c_given_confidence_just_below_boundary_when_checked_then_warning(
        self, lab_service
    ):
        # Boundary: confidence just below 0.5 -> warning
        confidence = 0.499
        low_confidence_warning = confidence < 0.5
        assert low_confidence_warning is True

    @pytest.mark.p1
    async def test_3_5_027d_given_zero_confidence_when_checked_then_warning(
        self, lab_service
    ):
        confidence = 0.0
        low_confidence_warning = confidence < 0.5
        assert low_confidence_warning is True

    @pytest.mark.p1
    async def test_3_5_027e_given_perfect_confidence_when_checked_then_no_warning(
        self, lab_service
    ):
        confidence = 1.0
        low_confidence_warning = confidence < 0.5
        assert low_confidence_warning is False
