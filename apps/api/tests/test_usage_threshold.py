"""
Story 1.7: Resource Guardrails - Usage Monitoring & Hard Caps
Unit Tests for _compute_threshold Pure Function

Test ID Format: [1.7-UNIT-XXX]
"""

from services.usage import _compute_threshold


class TestComputeThresholdBoundaries:
    """[1.7-UNIT-067..072] _compute_threshold boundary edge cases"""

    def test_1_7_unit_067_P0_given_79_pct_usage_when_compute_threshold_then_returns_ok(
        self,
    ):
        assert _compute_threshold(790, 1000) == "ok"

    def test_1_7_unit_068_P0_given_80_pct_usage_when_compute_threshold_then_returns_warning(
        self,
    ):
        assert _compute_threshold(800, 1000) == "warning"

    def test_1_7_unit_069_P1_given_94_pct_usage_when_compute_threshold_then_returns_warning(
        self,
    ):
        assert _compute_threshold(940, 1000) == "warning"

    def test_1_7_unit_070_P0_given_95_pct_usage_when_compute_threshold_then_returns_critical(
        self,
    ):
        assert _compute_threshold(950, 1000) == "critical"

    def test_1_7_unit_071_P1_given_99_pct_usage_when_compute_threshold_then_returns_critical(
        self,
    ):
        assert _compute_threshold(990, 1000) == "critical"

    def test_1_7_unit_072_P0_given_over_100_pct_usage_when_compute_threshold_then_returns_exceeded(
        self,
    ):
        assert _compute_threshold(1001, 1000) == "exceeded"
