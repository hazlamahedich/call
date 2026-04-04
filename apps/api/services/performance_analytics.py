"""Performance analytics service for voice preset recommendations.

Analyzes call performance data to generate data-driven voice preset recommendations.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.call_performance import CallPerformance
from models.voice_preset import VoicePreset

logger = logging.getLogger(__name__)


class PerformanceAnalyticsService:
    """Service for analyzing call performance and generating preset recommendations."""

    MIN_CALLS_FOR_RECOMMENDATION = 10
    RECOMMENDATION_LOOKBACK_DAYS = 30

    async def track_call(
        self,
        session: AsyncSession,
        org_id: str,
        call_id: str,
        agent_id: Optional[int],
        preset_id: Optional[int],
        use_case: str,
        duration_seconds: float,
        was_answered: bool,
        was_connected: bool,
        outcome: str,
        call_started_at: datetime,
        call_ended_at: Optional[datetime] = None,
        sentiment_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CallPerformance:
        """Record call performance metrics.

        Args:
            session: Database session
            org_id: Organization ID
            call_id: Unique call identifier
            agent_id: Agent ID used
            preset_id: Voice preset ID used
            use_case: Use case (sales, support, marketing)
            duration_seconds: Call duration
            was_answered: Whether call was answered
            was_connected: Whether call connected
            outcome: Call outcome
            call_started_at: Call start time
            call_ended_at: Call end time
            sentiment_score: Sentiment score (-1 to 1)
            metadata: Additional metadata

        Returns:
            Created CallPerformance record
        """
        performance = CallPerformance(
            org_id=org_id,
            call_id=call_id,
            agent_id=agent_id,
            preset_id=preset_id,
            use_case=use_case,
            duration_seconds=duration_seconds,
            was_answered=was_answered,
            was_connected=was_connected,
            has_callback=False,  # Could be updated separately
            outcome=outcome,
            sentiment_score=sentiment_score,
            call_started_at=call_started_at,
            call_ended_at=call_ended_at,
            metadata=metadata or {},
        )

        session.add(performance)
        await session.commit()
        await session.refresh(performance)

        logger.info(
            "Call performance tracked",
            extra={
                "code": "CALL_PERFORMANCE_TRACKED",
                "org_id": org_id,
                "call_id": call_id,
                "preset_id": preset_id,
                "use_case": use_case,
                "outcome": outcome,
            },
        )

        return performance

    async def get_preset_performance_stats(
        self,
        session: AsyncSession,
        org_id: str,
        preset_id: int,
        days: int = RECOMMENDATION_LOOKBACK_DAYS,
    ) -> Dict[str, Any]:
        """Get performance statistics for a specific preset.

        Args:
            session: Database session
            org_id: Organization ID
            preset_id: Preset ID to analyze
            days: Number of days to look back

        Returns:
            Dictionary with performance metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await session.execute(
            select(CallPerformance)
            .where(
                and_(
                    CallPerformance.org_id == org_id,
                    CallPerformance.preset_id == preset_id,
                    CallPerformance.call_started_at >= cutoff_date,
                )
            )
        )
        calls = result.scalars().all()

        if not calls:
            return {
                "total_calls": 0,
                "answered_calls": 0,
                "answered_rate": 0.0,
                "connected_rate": 0.0,
                "avg_duration": 0.0,
                "avg_sentiment": 0.0,
            }

        total_calls = len(calls)
        answered_calls = sum(1 for c in calls if c.was_answered)
        connected_calls = sum(1 for c in calls if c.was_connected)

        answered_rate = answered_calls / total_calls if total_calls > 0 else 0.0
        connected_rate = connected_calls / total_calls if total_calls > 0 else 0.0

        avg_duration = sum(c.duration_seconds for c in calls) / total_calls

        sentiment_scores = [c.sentiment_score for c in calls if c.sentiment_score is not None]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0

        return {
            "total_calls": total_calls,
            "answered_calls": answered_calls,
            "answered_rate": answered_rate,
            "connected_rate": connected_rate,
            "avg_duration": avg_duration,
            "avg_sentiment": avg_sentiment,
        }

    async def generate_recommendation(
        self,
        session: AsyncSession,
        org_id: str,
        use_case: str,
    ) -> Optional[Dict[str, Any]]:
        """Generate voice preset recommendation based on performance data.

        Args:
            session: Database session
            org_id: Organization ID
            use_case: Use case to analyze

        Returns:
            Recommendation dict with preset_id, improvement_pct, reasoning, or None if insufficient data
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.RECOMMENDATION_LOOKBACK_DAYS)

        # Get all presets for this use case
        presets_result = await session.execute(
            select(VoicePreset).where(
                and_(
                    VoicePreset.org_id == org_id,
                    VoicePreset.use_case == use_case,
                    VoicePreset.is_active == True,
                )
            )
        )
        presets = presets_result.scalars().all()

        if not presets:
            return None

        # Get total call count for this use case
        total_calls_result = await session.execute(
            select(func.count(CallPerformance.id))
            .where(
                and_(
                    CallPerformance.org_id == org_id,
                    CallPerformance.use_case == use_case,
                    CallPerformance.call_started_at >= cutoff_date,
                )
            )
        )
        total_calls = total_calls_result.scalar() or 0

        if total_calls < self.MIN_CALLS_FOR_RECOMMENDATION:
            logger.debug(
                "Insufficient calls for recommendation",
                extra={
                    "code": "INSUFFICIENT_CALLS",
                    "org_id": org_id,
                    "use_case": use_case,
                    "total_calls": total_calls,
                    "required": self.MIN_CALLS_FOR_RECOMMENDATION,
                },
            )
            return None

        # Analyze each preset's performance
        preset_stats = []
        for preset in presets:
            stats = await self.get_preset_performance_stats(session, org_id, preset.id)
            if stats["total_calls"] >= 3:  # Minimum calls per preset to consider
                preset_stats.append({
                    "preset_id": preset.id,
                    "preset_name": preset.name,
                    "answered_rate": stats["answered_rate"],
                    "connected_rate": stats["connected_rate"],
                    "avg_sentiment": stats["avg_sentiment"],
                    "total_calls": stats["total_calls"],
                })

        if not preset_stats:
            return None

        # Sort by combined score (answered rate + connected rate + sentiment)
        def calculate_score(stats: Dict[str, Any]) -> float:
            return (
                stats["answered_rate"] * 0.5 +
                stats["connected_rate"] * 0.3 +
                ((stats["avg_sentiment"] + 1) / 2) * 0.2  # Normalize -1..1 to 0..1
            )

        preset_stats.sort(key=calculate_score, reverse=True)

        # Get current preset (if any)
        current_preset_result = await session.execute(
            select(CallPerformance)
            .where(
                and_(
                    CallPerformance.org_id == org_id,
                    CallPerformance.use_case == use_case,
                )
            )
            .order_by(CallPerformance.call_started_at.desc())
            .limit(1)
        )
        current_preset_id = current_preset_result.scalar_one_or_none()

        current_preset_stats = None
        if current_preset_id and current_preset_id.preset_id:
            current_preset_stats = next(
                (s for s in preset_stats if s["preset_id"] == current_preset_id.preset_id),
                None,
            )

        # If best performer is different from current, recommend it
        best_preset = preset_stats[0]
        if current_preset_stats and best_preset["preset_id"] == current_preset_stats["preset_id"]:
            return None  # Already using the best preset

        # Calculate improvement percentage
        improvement_pct = 0.0
        if current_preset_stats:
            current_score = calculate_score(current_preset_stats)
            best_score = calculate_score(best_preset)
            improvement_pct = ((best_score - current_score) / current_score) * 100 if current_score > 0 else 0.0
        else:
            improvement_pct = 15.0  # Default recommendation message

        return {
            "preset_id": best_preset["preset_id"],
            "preset_name": best_preset["preset_name"],
            "improvement_pct": round(improvement_pct, 0),
            "reasoning": self._generate_reasoning(best_preset, current_preset_stats),
            "based_on_calls": total_calls,
        }

    def _generate_reasoning(
        self,
        best_stats: Dict[str, Any],
        current_stats: Optional[Dict[str, Any]],
    ) -> str:
        """Generate human-readable reasoning for recommendation.

        Args:
            best_stats: Stats for recommended preset
            current_stats: Stats for current preset (if any)

        Returns:
            Human-readable reasoning string
        """
        reasons = []

        if best_stats["answered_rate"] > 0.3:
            reasons.append(f"{best_stats['answered_rate']*100:.0f}% pickup rate")

        if best_stats["avg_sentiment"] > 0.2:
            reasons.append("positive caller sentiment")

        if best_stats["connected_rate"] > 0.8:
            reasons.append("high connection rate")

        if not reasons:
            reasons.append("strong overall performance")

        return "This preset has " + ", ".join(reasons)

    async def get_organization_call_count(
        self,
        session: AsyncSession,
        org_id: str,
        use_case: Optional[str] = None,
    ) -> int:
        """Get total call count for organization.

        Args:
            session: Database session
            org_id: Organization ID
            use_case: Optional use case filter

        Returns:
            Total call count
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.RECOMMENDATION_LOOKBACK_DAYS)

        query = select(func.count(CallPerformance.id)).where(
            and_(
                CallPerformance.org_id == org_id,
                CallPerformance.call_started_at >= cutoff_date,
            )
        )

        if use_case:
            query = query.where(CallPerformance.use_case == use_case)

        result = await session.execute(query)
        return result.scalar() or 0
