"""
Telemetry API Schemas
Story 2.4: Asynchronous Telemetry Sidecars for Voice Events

Request/response schemas for telemetry API endpoints.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class TelemetryMetricsResponse(BaseModel):
    """Response schema for queue metrics (AC: 6)."""

    current_depth: int = Field(..., description="Current number of events in queue")
    avg_depth: float = Field(..., description="Average queue depth")
    max_depth: int = Field(..., description="Maximum queue depth observed")
    is_running: bool = Field(..., description="Whether worker is running")
    processing_latency_ms_p95: float = Field(..., description="P95 processing latency in ms")
    events_per_second: float = Field(..., description="Events processed per second")


class TelemetryEventQueryParams(BaseModel):
    """Query parameters for telemetry events (AC: 7)."""

    call_id: Optional[int] = Field(None, description="Filter by call ID")
    event_type: Optional[str] = Field(None, description="Filter by event type")
    start_time: Optional[str] = Field(None, description="Start timestamp (ISO format)")
    end_time: Optional[str] = Field(None, description="End timestamp (ISO format)")
    limit: int = Field(1000, ge=1, le=10000, description="Max results (default 1000, max 10000)")


class VoiceTelemetryResponse(BaseModel):
    """Response schema for voice telemetry event (AC: 7)."""

    id: int
    org_id: str
    call_id: Optional[int]
    event_type: str
    timestamp: str
    duration_ms: Optional[float]
    audio_level: Optional[float]
    confidence_score: Optional[float]
    sentiment_score: Optional[float]
    provider: str
    queue_depth_at_capture: Optional[int]
    processing_latency_ms: Optional[float]
    created_at: str

    class Config:
        from_attributes = True


class TelemetryEventListResponse(BaseModel):
    """Response schema for telemetry events list."""

    events: List[VoiceTelemetryResponse]
    total: int
    limit: int
