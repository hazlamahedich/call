"""Voice preset recommendation API endpoints.

Provides data-driven voice preset recommendations based on call performance analytics.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session as get_db
from middleware.auth import AuthMiddleware
from dependencies.org_context import get_current_org_id
from services.performance_analytics import PerformanceAnalyticsService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/voice-presets/recommendations/stats")
async def get_recommendation_stats(
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = token.org_id
    analytics_service = PerformanceAnalyticsService()

    try:
        total_calls = await analytics_service.get_organization_call_count(
            session=session,
            org_id=org_id,
        )

        sales_calls = await analytics_service.get_organization_call_count(
            session=session,
            org_id=org_id,
            use_case="sales",
        )

        support_calls = await analytics_service.get_organization_call_count(
            session=session,
            org_id=org_id,
            use_case="support",
        )

        marketing_calls = await analytics_service.get_organization_call_count(
            session=session,
            org_id=org_id,
            use_case="marketing",
        )

        min_required = analytics_service.MIN_CALLS_FOR_RECOMMENDATION

        return {
            "total_calls": total_calls,
            "calls_by_use_case": {
                "sales": sales_calls,
                "support": support_calls,
                "marketing": marketing_calls,
            },
            "recommendations_available": {
                "sales": sales_calls >= min_required,
                "support": support_calls >= min_required,
                "marketing": marketing_calls >= min_required,
            },
            "min_calls_required": min_required,
        }

    except Exception as e:
        logger.error(
            "Failed to get recommendation stats",
            extra={
                "code": "RECOMMENDATION_STATS_ERROR",
                "org_id": org_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "STATS_FAILED",
                "message": "Failed to get recommendation statistics",
            },
        )


@router.get("/voice-presets/recommendations/{use_case}")
async def get_preset_recommendation(
    use_case: str,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = token.org_id

    VALID_USE_CASES = {"sales", "support", "marketing"}
    if use_case not in VALID_USE_CASES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_USE_CASE",
                "message": "Use case must be one of: sales, support, marketing",
            },
        )

    analytics_service = PerformanceAnalyticsService()

    try:
        recommendation = await analytics_service.generate_recommendation(
            session=session,
            org_id=org_id,
            use_case=use_case,
        )

        if not recommendation:
            return {
                "recommendation": None,
                "reason": "Insufficient call data for recommendations",
                "min_calls_required": analytics_service.MIN_CALLS_FOR_RECOMMENDATION,
            }

        return {
            "recommendation": recommendation,
            "reason": f"Based on {recommendation['based_on_calls']} calls in the last {analytics_service.RECOMMENDATION_LOOKBACK_DAYS} days",
        }

    except Exception as e:
        logger.error(
            "Failed to generate recommendation",
            extra={
                "code": "RECOMMENDATION_ERROR",
                "org_id": org_id,
                "use_case": use_case,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RECOMMENDATION_FAILED",
                "message": "Failed to generate recommendation",
            },
        )
