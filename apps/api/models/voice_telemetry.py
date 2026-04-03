from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Index

from .base import TenantModel, VoiceEventType, TelemetryProvider


def _utc_now() -> datetime:
    """Get current UTC timestamp for telemetry events."""
    return datetime.now(timezone.utc)


class VoiceTelemetry(TenantModel, table=True):
    """
    Voice event telemetry for observability and analytics.

    Captures non-blocking telemetry from voice pipeline events:
    - Silence detection (VAD)
    - Noise floor events
    - Lead interruptions
    - Talkover overlaps

    This data is best-effort observability, not compliance records.
    Events may be dropped under load to preserve voice pipeline latency.
    """

    __tablename__ = "voice_telemetry"  # type: ignore

    # Foreign key to calls table
    call_id: Optional[int] = Field(
        default=None,
        foreign_key="calls.id",
        index=True,
        description="Related call record ID"
    )

    # Event classification
    event_type: VoiceEventType = Field(
        description="Type of voice event detected",
        max_length=50
    )

    # Timestamp when event occurred (indexed for time-series queries)
    timestamp: datetime = Field(
        default_factory=_utc_now,
        index=True,
        description="When the voice event was detected"
    )

    # Optional event metrics
    duration_ms: Optional[float] = Field(
        default=None,
        nullable=True,
        description="Duration of the event in milliseconds"
    )

    audio_level: Optional[float] = Field(
        default=None,
        nullable=True,
        description="Audio level in dB"
    )

    confidence_score: Optional[float] = Field(
        default=None,
        nullable=True,
        description="Detection confidence (0.0-1.0)"
    )

    sentiment_score: Optional[float] = Field(
        default=None,
        nullable=True,
        description="Sentiment analysis score if available"
    )

    # Provider identification
    provider: TelemetryProvider = Field(
        default="vapi",
        description="Provider that detected the event",
        max_length=30
    )

    # Flexible metadata for additional context
    session_metadata: Optional[dict] = Field(
        default=None,
        nullable=True,
        description="Additional session context as JSONB"
    )

    # Telemetry system metrics (for observability of the telemetry system)
    queue_depth_at_capture: Optional[int] = Field(
        default=None,
        nullable=True,
        description="Queue depth when event was captured"
    )

    processing_latency_ms: Optional[float] = Field(
        default=None,
        nullable=True,
        description="Time from capture to DB commit in milliseconds"
    )

    # Composite indexes for query performance (AC: 4)
    # Index on (org_id, timestamp) for tenant-scoped time-series queries
    # Index on (call_id, event_type) for call-specific event filtering
    __table_args__ = (
        Index("ix_voice_telemetry_org_id_timestamp", "org_id", "timestamp"),
        Index("ix_voice_telemetry_call_id_event_type", "call_id", "event_type"),
    )
