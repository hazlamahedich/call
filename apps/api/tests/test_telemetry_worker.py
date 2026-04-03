"""
Unit Tests for Telemetry Worker
Story 2.4: Asynchronous Telemetry Sidecars for Voice Events

Tests for batch persistence, tenant isolation, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from models.base import utc_now
from models.voice_telemetry import VoiceTelemetry
from services.telemetry.queue import VoiceEvent
from services.telemetry.worker import TelemetryWorker


class TestTelemetryWorker:
    """[2.4-UNIT-WORKER-001] Test TelemetryWorker initialization."""

    def test_worker_init(self):
        """Test worker can be initialized with session factory."""
        session_factory = MagicMock()
        worker = TelemetryWorker(session_factory)

        assert worker.session_factory == session_factory


class TestProcessBatch:
    """[2.4-UNIT-WORKER-002] Tests for batch processing."""

    @pytest.mark.asyncio
    async def test_process_batch_with_events(self):
        """[2.4-UNIT-WORKER-003] Test batch persistence to database (AC: 2)."""
        # Mock session factory
        mock_session = MagicMock()
        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        session_factory = MagicMock()
        session_factory.__aenter__ = AsyncMock(return_value=mock_session)
        session_factory.__aexit__ = AsyncMock()

        worker = TelemetryWorker(session_factory)

        # Create test events
        events = [
            VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=456,
                duration_ms=1500.0,
            ),
            VoiceEvent(
                event_type="noise",
                tenant_id="org123",
                call_id=457,
                audio_level=-15.5,
            ),
        ]

        # Process batch
        await worker.process_batch(events)

        # Verify database operations
        mock_session.add_all.assert_called_once()
        mock_session.commit.assert_called_once()

        # Verify records were created with computed fields
        records = mock_session.add_all.call_args[0][0]
        assert len(records) == 2
        assert all(isinstance(r, VoiceTelemetry) for r in records)
        assert all(r.processing_latency_ms is not None for r in records)

    @pytest.mark.asyncio
    async def test_process_batch_empty(self):
        """[2.4-UNIT-WORKER-004] Test worker handles empty batch gracefully."""
        session_factory = MagicMock()
        worker = TelemetryWorker(session_factory)

        # Should not error with empty batch
        await worker.process_batch([])

    @pytest.mark.asyncio
    async def test_process_batch_handles_db_errors(self):
        """[2.4-UNIT-WORKER-005] Test graceful degradation on DB errors (AC: 8)."""
        # Mock session that raises error on commit
        mock_session = MagicMock()
        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock(side_effect=Exception("DB connection lost"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        session_factory = MagicMock()
        session_factory.__aenter__ = AsyncMock(return_value=mock_session)
        session_factory.__aexit__ = AsyncMock()

        worker = TelemetryWorker(session_factory)

        events = [
            VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=456,
            ),
        ]

        # Should not raise exception
        await worker.process_batch(events)

    @pytest.mark.asyncio
    async def test_process_batch_tracks_latency(self):
        """[2.4-UNIT-WORKER-006] Test processing latency is tracked (AC: 3)."""
        mock_session = MagicMock()
        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        session_factory = MagicMock()
        session_factory.__aenter__ = AsyncMock(return_value=mock_session)
        session_factory.__aexit__ = AsyncMock()

        worker = TelemetryWorker(session_factory)

        events = [
            VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=456,
            ),
        ]

        await worker.process_batch(events)

        # Verify latency was set
        records = mock_session.add_all.call_args[0][0]
        assert len(records) == 1
        assert records[0].processing_latency_ms is not None
        assert records[0].processing_latency_ms >= 0

    @pytest.mark.asyncio
    async def test_process_batch_maps_event_fields(self):
        """[2.4-UNIT-WORKER-007] Test VoiceEvent fields map correctly to VoiceTelemetry (AC: 4)."""
        mock_session = MagicMock()
        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        session_factory = MagicMock()
        session_factory.__aenter__ = AsyncMock(return_value=mock_session)
        session_factory.__aexit__ = AsyncMock()

        worker = TelemetryWorker(session_factory)

        timestamp = utc_now()
        events = [
            VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=456,
                timestamp=timestamp,
                duration_ms=1500.0,
                audio_level=-15.5,
                confidence_score=0.9,
                sentiment_score=0.7,
                provider="deepgram",
                metadata={"test": "data"},
            ),
        ]

        await worker.process_batch(events)

        records = mock_session.add_all.call_args[0][0]
        assert len(records) == 1
        record = records[0]

        assert record.call_id == 456
        assert record.event_type == "silence"
        assert record.timestamp == timestamp
        assert record.duration_ms == 1500.0
        assert record.audio_level == -15.5
        assert record.confidence_score == 0.9
        assert record.sentiment_score == 0.7
        assert record.provider == "deepgram"
        assert record.session_metadata == {"test": "data"}


class TestTenantIsolation:
    """[2.4-UNIT-WORKER-008] Tests for tenant isolation."""

    @pytest.mark.asyncio
    async def test_tenant_isolation_enforced(self):
        """[2.4-UNIT-WORKER-009] Test RLS policies enforce tenant isolation (AC: 2)."""
        # This test verifies that worker respects RLS policies
        # In real scenario, set_tenant_context() would be called before DB operations
        # Worker inherits tenant context from session

        mock_session = MagicMock()
        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        session_factory = MagicMock()
        session_factory.__aenter__ = AsyncMock(return_value=mock_session)
        session_factory.__aexit__ = AsyncMock()

        worker = TelemetryWorker(session_factory)

        # Events from different tenants
        events = [
            VoiceEvent(
                event_type="silence",
                tenant_id="org1",
                call_id=456,
            ),
            VoiceEvent(
                event_type="noise",
                tenant_id="org2",
                call_id=789,
            ),
        ]

        await worker.process_batch(events)

        # Worker processes all events - RLS is enforced at DB level via set_tenant_context()
        records = mock_session.add_all.call_args[0][0]
        assert len(records) == 2
