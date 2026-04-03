"""
Telemetry Worker Service
Story 2.4: Asynchronous Telemetry Sidecars for Voice Events

Background worker that persists voice telemetry events to the database.
Processes batches asynchronously without blocking the voice pipeline.
"""

import time
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from models.base import utc_now
from models.voice_telemetry import VoiceTelemetry
from .queue import VoiceEvent


class TelemetryWorker:
    """
    Background worker for batch persistence of voice telemetry.

    Processes events from the in-memory queue and persists to database.
    Handles DB errors gracefully to avoid blocking voice pipeline.

    AC: 2, 3, 8 - Async persistence, <100ms P95 latency, graceful degradation
    """

    def __init__(self, session_factory):
        """
        Initialize telemetry worker.

        Args:
            session_factory: Factory function for creating DB sessions
        """
        self.session_factory = session_factory

    async def process_batch(self, events: List[VoiceEvent]) -> None:
        """
        Persist batch of voice events to database.

        Measures processing latency and handles DB errors gracefully.

        AC: 2 - Bulk INSERT operations with proper tenant isolation
        AC: 3 - Track processing latency (<100ms P95 target)
        AC: 8 - Graceful degradation on DB errors

        Args:
            events: List of voice events to persist
        """
        if not events:
            return

        batch_start = time.perf_counter()

        try:
            async with self.session_factory() as session:
                # Convert VoiceEvent dataclass to VoiceTelemetry SQLModel
                telemetry_records = []
                for event in events:
                    # Use model_validate pattern (AC: 4)
                    record_data = {
                        "callId": event.call_id,
                        "eventType": event.event_type,
                        "timestamp": event.timestamp,
                        "durationMs": event.duration_ms,
                        "audioLevel": event.audio_level,
                        "confidenceScore": event.confidence_score,
                        "sentimentScore": event.sentiment_score,
                        "provider": event.provider,
                        "sessionMetadata": event.metadata,
                    }

                    # Create VoiceTelemetry record
                    record = VoiceTelemetry.model_validate(record_data)
                    telemetry_records.append(record)

                # Set computed fields
                processing_latency_ms = (time.perf_counter() - batch_start) * 1000

                for record in telemetry_records:
                    record.processing_latency_ms = processing_latency_ms
                    # Note: queue_depth_at_capture would be set by queue if needed
                    # For now, we don't track this at the record level

                # Bulk insert all records
                session.add_all(telemetry_records)
                await session.commit()

        except Exception as e:
            # DB error - log and continue (graceful degradation)
            # Events are lost - acceptable for telemetry
            import logging

            logging.error(
                f"Failed to persist telemetry batch: {e}",
                extra={
                    "code": "TELEMETRY_DB_ERROR",
                    "batch_size": len(events),
                    "error": str(e),
                },
            )
            # Don't re-raise - worker continues processing
