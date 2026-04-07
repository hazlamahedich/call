"""Story 3.3 AC3: Confidence Scoring.

Tests [3.3-UNIT-011] through [3.3-UNIT-017].
"""

import pytest

from conftest_3_3 import make_chunks
from services.grounding import GroundingService


@pytest.mark.p0
class TestAC3ConfidenceScoring:
    def test_3_3_011_given_high_similarity_chunks_when_scoring_then_high_confidence(
        self,
    ):
        """[3.3-UNIT-011] High similarity chunks → high confidence."""
        chunks = make_chunks(
            5, 0.95, "product analytics dashboard reporting features capabilities"
        )
        result = GroundingService.compute_confidence(
            chunks,
            "The product analytics dashboard reporting features capabilities are great",
        )
        assert result.score > 0.6

    def test_3_3_012_given_low_similarity_chunk_when_scoring_then_low_confidence(self):
        """[3.3-UNIT-012] Low similarity chunk → low confidence."""
        chunks = make_chunks(1, 0.3, "unrelated random text about weather")
        result = GroundingService.compute_confidence(
            chunks,
            "Tell me about product pricing",
            max_source_chunks=5,
            min_confidence=0.5,
        )
        assert result.score < 0.5

    def test_3_3_013_given_mixed_similarity_when_scoring_then_weighted_breakdown(self):
        """[3.3-UNIT-013] Mixed similarity → weighted breakdown components."""
        chunks = make_chunks(3, 0.7, "product features analytics dashboard reporting")
        result = GroundingService.compute_confidence(chunks, "Product has analytics")
        assert result.chunk_coverage > 0.0
        assert result.avg_similarity > 0.0
        assert result.attribution_ratio >= 0.0
        expected = (
            result.chunk_coverage * 0.3
            + result.avg_similarity * 0.4
            + result.attribution_ratio * 0.3
        )
        assert abs(result.score - round(expected, 4)) < 0.001

    def test_3_3_014_given_low_confidence_when_scoring_then_flag_is_true(self):
        """[3.3-UNIT-014] isLowConfidence true when score < threshold."""
        chunks = make_chunks(1, 0.2, "random unrelated content")
        result = GroundingService.compute_confidence(
            chunks, "Something completely different", min_confidence=0.5
        )
        assert result.is_low_confidence is True

    def test_3_3_015_given_zero_chunks_when_scoring_then_no_division_by_zero(self):
        """[3.3-UNIT-015] Zero chunks → score 0.0, no division by zero."""
        result = GroundingService.compute_confidence([], "any response")
        assert result.score == 0.0
        assert result.chunk_coverage == 0.0
        assert result.source_chunk_ids == []

    def test_3_3_016_given_threshold_similarity_when_scoring_then_included(self):
        """[3.3-UNIT-016] Chunks at exact threshold included in score."""
        chunks = make_chunks(1, 0.7, "test content about features")
        result = GroundingService.compute_confidence(
            chunks, "features test content about"
        )
        assert result.score > 0.0

    def test_3_3_017_given_max_chunks_when_scoring_then_handles_correctly(self):
        """[3.3-UNIT-017] 20 chunks (max allowed) handled correctly."""
        chunks = make_chunks(20, 0.8, "consistent content about the product")
        result = GroundingService.compute_confidence(
            chunks, "the product content", max_source_chunks=20
        )
        assert result.score > 0.0
        assert len(result.source_chunk_ids) == 20
