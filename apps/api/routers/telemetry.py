"""
Telemetry API Router
Story 2.4: Asynchronous Telemetry Sidecars for Voice Events

Endpoints for telemetry metrics and event querying.
"""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from database.session import get_session
from dependencies.org_context import get_current_org_id
from models.voice_telemetry import VoiceTelemetry
from schemas.telemetry import (
    TelemetryMetricsResponse,
    VoiceTelemetryResponse,
    TelemetryEventListResponse,
)
from services.telemetry import telemetry_queue


router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


@router.get(
    "/metrics",
    response_model=TelemetryMetricsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_metrics() -> TelemetryMetricsResponse:
    """
    Get telemetry queue health metrics.

    AC: 6 - Queue metrics exposed for monitoring
    No auth required for monitoring endpoint.
    """
    metrics = telemetry_queue.get_metrics()
    return TelemetryMetricsResponse(**metrics)


@router.get(
    "/events",
    response_model=TelemetryEventListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_events(
    call_id: int = Query(None, description="Filter by call ID"),
    event_type: str = Query(None, description="Filter by event type"),
    start_time: str = Query(None, description="Start timestamp (ISO format)"),
    end_time: str = Query(None, description="End timestamp (ISO format)"),
    limit: int = Query(1000, ge=1, le=10000, description="Max results"),
    session: AsyncSession = Depends(get_session),
    current_org_id: str = Depends(get_current_org_id),
) -> TelemetryEventListResponse:
    """
    Query telemetry events with filters.

    AC: 7 - Tenant-isolated querying with filters and pagination
    """
    # Set tenant context for RLS enforcement
    from database.session import set_tenant_context
    await set_tenant_context(session, current_org_id)

    # Build base query with RLS enforced
    query = select(VoiceTelemetry)

    # Apply filters
    if call_id is not None:
        query = query.where(VoiceTelemetry.call_id == call_id)

    if event_type is not None:
        query = query.where(VoiceTelemetry.event_type == event_type)

    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            query = query.where(VoiceTelemetry.timestamp >= start_dt)
        except ValueError:
            logging.warning(f"Invalid start_time format: {start_time}")

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            query = query.where(VoiceTelemetry.timestamp <= end_dt)
        except ValueError:
            logging.warning(f"Invalid end_time format: {end_time}")

    # Apply pagination
    query = query.limit(limit)

    # Execute query
    result = await session.execute(query)
    results = result.scalars().all()

    # Convert to response models
    events = [
        VoiceTelemetryResponse(
            id=r.id,
            org_id=r.org_id,
            call_id=r.call_id,
            event_type=r.event_type,
            timestamp=r.timestamp.isoformat(),
            duration_ms=r.duration_ms,
            audio_level=r.audio_level,
            confidence_score=r.confidence_score,
            sentiment_score=r.sentiment_score,
            provider=r.provider,
            queue_depth_at_capture=r.queue_depth_at_capture,
            processing_latency_ms=r.processing_latency_ms,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in results
    ]

    return TelemetryEventListResponse(
        events=events,
        total=len(events),
        limit=limit,
    )
