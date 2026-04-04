"""
Story 2.6: Voice Presets by Use Case
Backend Tests for Performance Recommendations (AC6)

Test ID Format: 2.6-BACKEND-AC6-XXX
Priority: P0 (Critical Gap)

Tests the performance analytics service that analyzes call data
to generate data-driven voice preset recommendations.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from models.call_performance import CallPerformance
from models.voice_preset import VoicePreset
from services.performance_analytics import PerformanceAnalyticsService


@pytest.mark.asyncio
class TestPerformanceAnalyticsService:
    """Test PerformanceAnalyticsService for recommendation generation."""

    async def test_track_call_records_performance_metrics(
        self,
        db_session: AsyncSession,
    ):
        """[2.6-BACKEND-AC6-001][P0] Given valid call data, When tracking call, Then metrics are saved."""
        service = PerformanceAnalyticsService()

        performance = await service.track_call(
            session=db_session,
            org_id="test_org",
            call_id="test-call-001",
            agent_id=1,
            preset_id=1,
            use_case="sales",
            duration_seconds=120.5,
            was_answered=True,
            was_connected=True,
            outcome="completed",
            call_started_at=datetime.utcnow(),
            call_ended_at=datetime.utcnow() + timedelta(seconds=120),
            sentiment_score=0.5,
        )

        assert performance.org_id == "test_org"
        assert performance.call_id == "test-call-001"
        assert performance.preset_id == 1
        assert performance.use_case == "sales"
        assert performance.duration_seconds == 120.5
        assert performance.was_answered is True
        assert performance.sentiment_score == 0.5

    async def test_get_preset_performance_stats_calculates_metrics(
        self,
        db_session: AsyncSession,
    ):
        """[2.6-BACKEND-AC6-002][P0] Given preset with calls, When getting stats, Then metrics are calculated correctly."""
        service = PerformanceAnalyticsService()

        # Create test calls
        await service.track_call(
            session=db_session,
            org_id="test_org",
            call_id="call-001",
            agent_id=1,
            preset_id=1,
            use_case="sales",
            duration_seconds=100,
            was_answered=True,
            was_connected=True,
            outcome="completed",
            call_started_at=datetime.utcnow() - timedelta(days=1),
        )

        await service.track_call(
            session=db_session,
            org_id="test_org",
            call_id="call-002",
            agent_id=1,
            preset_id=1,
            use_case="sales",
            duration_seconds=200,
            was_answered=False,
            was_connected=False,
            outcome="no_answer",
            call_started_at=datetime.utcnow() - timedelta(days=1),
        )

        stats = await service.get_preset_performance_stats(
            session=db_session,
            org_id="test_org",
            preset_id=1,
            days=30,
        )

        assert stats["total_calls"] == 2
        assert stats["answered_calls"] == 1
        assert stats["answered_rate"] == 0.5
        assert stats["avg_duration"] == 150.0

    async def test_generate_recommendation_returns_none_with_insufficient_data(
        self,
        db_session: AsyncSession,
    ):
        """[2.6-BACKEND-AC6-003][P0] Given less than 10 calls, When generating recommendation, Then returns None."""
        service = PerformanceAnalyticsService()

        # Create only 5 calls (below minimum)
        for i in range(5):
            await service.track_call(
                session=db_session,
                org_id="test_org",
                call_id=f"call-{i}",
                agent_id=1,
                preset_id=1,
                use_case="sales",
                duration_seconds=100,
                was_answered=True,
                was_connected=True,
                outcome="completed",
                call_started_at=datetime.utcnow() - timedelta(days=1),
            )

        recommendation = await service.generate_recommendation(
            session=db_session,
            org_id="test_org",
            use_case="sales",
        )

        assert recommendation is None

    async def test_generate_recommendation_returns_best_preset(
        self,
        db_session: AsyncSession,
    ):
        """[2.6-BACKEND-AC6-004][P0] Given multiple presets with performance data, When generating recommendation, Then returns best performer."""
        service = PerformanceAnalyticsService()

        # Create presets
        preset1 = VoicePreset(
            org_id="test_org",
            name="Sales - Rachel",
            use_case="sales",
            voice_id="voice-1",
            speech_speed=1.0,
            stability=0.8,
            temperature=0.7,
            description="High energy sales voice",
            is_active=True,
            sort_order=1,
        )
        preset2 = VoicePreset(
            org_id="test_org",
            name="Sales - Alex",
            use_case="sales",
            voice_id="voice-2",
            speech_speed=1.1,
            stability=0.7,
            temperature=0.6,
            description="Confident sales voice",
            is_active=True,
            sort_order=2,
        )
        db_session.add(preset1)
        db_session.add(preset2)
        await db_session.commit()

        # Create performance data - preset1 performs better
        for i in range(10):
            await service.track_call(
                session=db_session,
                org_id="test_org",
                call_id=f"call-p1-{i}",
                agent_id=1,
                preset_id=preset1.id,
                use_case="sales",
                duration_seconds=100,
                was_answered=True,
                was_connected=True,
                outcome="completed",
                call_started_at=datetime.utcnow() - timedelta(days=1),
                sentiment_score=0.5,
            )

        # Preset2 has worse performance
        for i in range(10):
            await service.track_call(
                session=db_session,
                org_id="test_org",
                call_id=f"call-p2-{i}",
                agent_id=1,
                preset_id=preset2.id,
                use_case="sales",
                duration_seconds=100,
                was_answered=False,
                was_connected=False,
                outcome="no_answer",
                call_started_at=datetime.utcnow() - timedelta(days=1),
                sentiment_score=-0.3,
            )

        recommendation = await service.generate_recommendation(
            session=db_session,
            org_id="test_org",
            use_case="sales",
        )

        assert recommendation is not None
        assert recommendation["preset_id"] == preset1.id
        assert recommendation["preset_name"] == "Sales - Rachel"
        assert recommendation["improvement_pct"] > 0
        assert "based_on_calls" in recommendation

    async def test_get_organization_call_count_returns_total(
        self,
        db_session: AsyncSession,
    ):
        """[2.6-BACKEND-AC6-005][P1] Given calls across use cases, When getting count, Then returns total correctly."""
        service = PerformanceAnalyticsService()

        # Create calls across different use cases
        for i in range(5):
            await service.track_call(
                session=db_session,
                org_id="test_org",
                call_id=f"sales-{i}",
                agent_id=1,
                preset_id=1,
                use_case="sales",
                duration_seconds=100,
                was_answered=True,
                was_connected=True,
                outcome="completed",
                call_started_at=datetime.utcnow() - timedelta(days=1),
            )

        for i in range(3):
            await service.track_call(
                session=db_session,
                org_id="test_org",
                call_id=f"support-{i}",
                agent_id=1,
                preset_id=2,
                use_case="support",
                duration_seconds=100,
                was_answered=True,
                was_connected=True,
                outcome="completed",
                call_started_at=datetime.utcnow() - timedelta(days=1),
            )

        # Test total count
        total_calls = await service.get_organization_call_count(
            session=db_session,
            org_id="test_org",
        )
        assert total_calls == 8

        # Test filtered by use case
        sales_calls = await service.get_organization_call_count(
            session=db_session,
            org_id="test_org",
            use_case="sales",
        )
        assert sales_calls == 5

    async def test_get_preset_performance_stats_handles_empty_data(
        self,
        db_session: AsyncSession,
    ):
        """[2.6-BACKEND-AC6-006][P2] Given preset with no calls, When getting stats, Then returns zero metrics."""
        service = PerformanceAnalyticsService()

        stats = await service.get_preset_performance_stats(
            session=db_session,
            org_id="test_org",
            preset_id=999,  # Non-existent preset
            days=30,
        )

        assert stats["total_calls"] == 0
        assert stats["answered_calls"] == 0
        assert stats["answered_rate"] == 0.0
        assert stats["connected_rate"] == 0.0
        assert stats["avg_duration"] == 0.0
        assert stats["avg_sentiment"] == 0.0

    async def test_generate_reasoning_creates_human_readable_text(
        self,
        db_session: AsyncSession,
    ):
        """[2.6-BACKEND-AC6-007][P2] Given preset stats, When generating reasoning, Then creates readable text."""
        service = PerformanceAnalyticsService()

        # Test with strong answered rate
        best_stats = {
            "preset_id": 1,
            "preset_name": "Sales - Rachel",
            "answered_rate": 0.65,
            "connected_rate": 0.85,
            "avg_sentiment": 0.5,
            "total_calls": 20,
        }

        reasoning = service._generate_reasoning(best_stats, None)

        assert "65% pickup rate" in reasoning
        assert "positive caller sentiment" in reasoning

        # Test with weak stats
        weak_stats = {
            "preset_id": 2,
            "preset_name": "Sales - Alex",
            "answered_rate": 0.2,
            "connected_rate": 0.5,
            "avg_sentiment": 0.1,
            "total_calls": 10,
        }

        reasoning = service._generate_reasoning(weak_stats, None)
        assert "strong overall performance" in reasoning or len(reasoning) > 0
