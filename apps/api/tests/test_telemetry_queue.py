"""
Unit Tests for Telemetry Queue
Story 2.4: Asynchronous Telemetry Sidecars for Voice Events

Tests for non-blocking push, batch processing, and metrics tracking.
"""

import asyncio
import time
from datetime import datetime, timezone

import pytest

from models.base import VoiceEventType, TelemetryProvider
from services.telemetry.queue import VoiceEvent, TelemetryQueue


class TestVoiceEvent:
    """[2.4-UNIT-QUEUE-001] Test VoiceEvent dataclass creation."""

    def test_voice_event_creation(self):
        """Test VoiceEvent can be created with required fields."""
        event = VoiceEvent(
            event_type="silence",
            tenant_id="org123",
            call_id=456,
        )

        assert event.event_type == "silence"
        assert event.tenant_id == "org123"
        assert event.call_id == 456
        assert isinstance(event.timestamp, datetime)

    def test_voice_event_with_optional_fields(self):
        """Test VoiceEvent with optional fields."""
        event = VoiceEvent(
            event_type="noise",
            tenant_id="org123",
            call_id=456,
            duration_ms=1500.0,
            audio_level=-15.5,
            confidence_score=0.9,
            sentiment_score=0.7,
            provider="deepgram",
            metadata={"test": "data"},
        )

        assert event.duration_ms == 1500.0
        assert event.audio_level == -15.5
        assert event.confidence_score == 0.9
        assert event.sentiment_score == 0.7
        assert event.provider == "deepgram"
        assert event.metadata == {"test": "data"}


class TestTelemetryQueuePush:
    """[2.4-UNIT-QUEUE-002] Tests for queue push operation."""

    @pytest.mark.asyncio
    async def test_push_succeeds(self):
        """Test successful push to queue."""
        queue = TelemetryQueue(max_size=100)
        event = VoiceEvent(
            event_type="silence",
            tenant_id="org123",
            call_id=456,
        )

        result = await queue.push(event)

        assert result is True
        assert queue._queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_push_latency_under_2ms(self):
        """[2.4-UNIT-QUEUE-003] Test push completes in <2ms (AC: 1, 3)."""
        queue = TelemetryQueue(max_size=10000, push_timeout_ms=2)
        event = VoiceEvent(
            event_type="silence",
            tenant_id="org123",
            call_id=456,
        )

        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            await queue.push(event)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        assert p95_latency < 2.0, f"P95 latency {p95_latency}ms exceeds 2ms threshold"
        assert avg_latency < 1.0, f"Average latency {avg_latency}ms should be well under 2ms"

    @pytest.mark.asyncio
    async def test_push_returns_false_when_queue_full(self):
        """[2.4-UNIT-QUEUE-004] Test push returns False when queue is full (AC: 8)."""
        queue = TelemetryQueue(max_size=5, batch_size=10)
        event = VoiceEvent(
            event_type="silence",
            tenant_id="org123",
            call_id=456,
        )

        # Fill queue to capacity
        for _ in range(5):
            await queue.push(event)

        # Next push should fail (queue full)
        result = await queue.push(event)

        assert result is False
        assert queue._queue.qsize() == 5  # Queue still at max capacity

    @pytest.mark.asyncio
    async def test_push_with_timeout(self):
        """Test push respects timeout setting."""
        queue = TelemetryQueue(max_size=1, push_timeout_ms=1)
        event = VoiceEvent(
            event_type="silence",
            tenant_id="org123",
            call_id=456,
        )

        # First push succeeds
        await queue.push(event)

        # Second push should fail quickly (1ms timeout)
        start = time.perf_counter()
        result = await queue.push(event)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result is False
        assert elapsed_ms < 10  # Should timeout quickly, not block


class TestTelemetryQueueMetrics:
    """[2.4-UNIT-QUEUE-005] Tests for queue metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_initial_state(self):
        """Test metrics return correct initial values."""
        queue = TelemetryQueue(max_size=1000)
        metrics = queue.get_metrics()

        assert metrics["current_depth"] == 0
        assert metrics["avg_depth"] == 0
        assert metrics["max_depth"] == 0
        assert metrics["is_running"] is False
        assert metrics["processing_latency_ms_p95"] == 0
        assert metrics["events_per_second"] == 0

    @pytest.mark.asyncio
    async def test_metrics_track_depth(self):
        """Test metrics track queue depth correctly."""
        queue = TelemetryQueue(max_size=1000)
        event = VoiceEvent(
            event_type="silence",
            tenant_id="org123",
            call_id=456,
        )

        # Add some events
        for _ in range(10):
            await queue.push(event)

        metrics = queue.get_metrics()
        assert metrics["current_depth"] == 10
        assert metrics["max_depth"] == 10


class TestTelemetryQueueWorker:
    """[2.4-UNIT-QUEUE-006] Tests for worker lifecycle and batch processing."""

    @pytest.mark.asyncio
    async def test_worker_starts_and_stops(self):
        """Test worker can be started and stopped gracefully."""
        queue = TelemetryQueue(max_size=1000)
        processed_batches = []

        async def mock_processor(batch):
            processed_batches.append(batch)

        await queue.start_worker(mock_processor)
        assert queue._is_running is True

        await queue.stop()
        assert queue._is_running is False
        assert queue._worker_task is None

    @pytest.mark.asyncio
    async def test_worker_processes_batches(self):
        """[2.4-UNIT-QUEUE-007] Test worker collects and processes batches."""
        queue = TelemetryQueue(max_size=1000, batch_size=5)
        processed_batches = []

        async def mock_processor(batch):
            processed_batches.append(batch)

        await queue.start_worker(mock_processor)

        # Add events
        for i in range(12):
            event = VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=456 + i,
            )
            await queue.push(event)

        # Wait for processing
        await asyncio.sleep(0.2)

        await queue.stop()

        # Should have processed 3 batches: 5, 5, 2 (or similar)
        assert len(processed_batches) >= 2
        total_processed = sum(len(batch) for batch in processed_batches)
        assert total_processed == 12

    @pytest.mark.asyncio
    async def test_worker_handles_processor_errors_gracefully(self):
        """[2.4-UNIT-QUEUE-008] Test worker continues after processor errors (AC: 8)."""
        queue = TelemetryQueue(max_size=1000, batch_size=2)
        processed_batches = []
        error_count = 0

        async def faulty_processor(batch):
            nonlocal error_count
            error_count += 1
            if error_count == 1:
                raise Exception("Simulated DB error")
            processed_batches.append(batch)

        await queue.start_worker(faulty_processor)

        # Add events
        for i in range(6):
            event = VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=456 + i,
            )
            await queue.push(event)

        # Wait for processing
        await asyncio.sleep(0.2)

        await queue.stop()

        # Worker should continue despite first error
        assert len(processed_batches) > 0
        assert error_count >= 1

    @pytest.mark.asyncio
    async def test_worker_respects_batch_deadline(self):
        """Test worker processes partial batch when deadline expires."""
        queue = TelemetryQueue(max_size=1000, batch_size=100)
        processed_batches = []

        async def mock_processor(batch):
            processed_batches.append(batch)

        await queue.start_worker(mock_processor)

        # Add only 3 events (well under batch size)
        for i in range(3):
            event = VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=456 + i,
            )
            await queue.push(event)

        # Wait for 1s deadline to trigger
        await asyncio.sleep(1.2)

        await queue.stop()

        # Should have processed partial batch due to deadline
        assert len(processed_batches) >= 1
        total_processed = sum(len(batch) for batch in processed_batches)
        assert total_processed == 3


class TestTelemetryQueueConcurrency:
    """[2.4-UNIT-QUEUE-009] Tests for concurrent push operations."""

    @pytest.mark.asyncio
    async def test_concurrent_push_operations(self):
        """[2.4-UNIT-QUEUE-010] Test queue handles 1000 concurrent pushes (AC: 3)."""
        queue = TelemetryQueue(max_size=10000)

        async def push_event(event_id):
            event = VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=event_id,
            )
            await queue.push(event)

        # Launch 1000 concurrent pushes
        tasks = [push_event(i) for i in range(1000)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)
        assert queue._queue.qsize() == 1000

    @pytest.mark.asyncio
    async def test_concurrent_push_with_worker(self):
        """Test concurrent pushes while worker is processing."""
        queue = TelemetryQueue(max_size=1000, batch_size=50)
        processed_batches = []

        async def mock_processor(batch):
            processed_batches.append(batch)
            await asyncio.sleep(0.01)  # Simulate DB work

        await queue.start_worker(mock_processor)

        # Launch 500 concurrent pushes
        async def push_event(event_id):
            event = VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=event_id,
            )
            await queue.push(event)

        tasks = [push_event(i) for i in range(500)]
        await asyncio.gather(*tasks)

        # Wait for processing to complete
        await asyncio.sleep(0.5)

        await queue.stop()

        # Most events should be processed
        total_processed = sum(len(batch) for batch in processed_batches)
        assert total_processed > 0
        assert total_processed <= 500
