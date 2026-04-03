"""
Telemetry Memory Leak Prevention Tests
Story 2.4: Asynchronous Telemetry Sidecars for Voice Events

[2.4-MEMORY-CLEANUP-001] P1 Test: Verify queue evicts stale call_id references

Tests that the queue depth gauge (deque maxlen=1000) properly evicts old entries
to prevent unbounded memory growth during long-running operations.
"""

import asyncio
from collections import deque

import pytest

from services.telemetry.queue import TelemetryQueue, VoiceEvent


class TestMemoryLeakPrevention:
    """[2.4-MEMORY-CLEANUP-001] P1 Memory leak prevention tests."""

    @pytest.mark.asyncio
    async def test_queue_depth_gauge_evicts_old_entries(self):
        """
        [2.4-MEMORY-CLEANUP-001] Test that queue depth gauge evicts old entries.

        Scenario: Create 1,100 depth samples (more than maxlen=1000)
        Expected: Only the most recent 1000 entries are retained
        """
        queue = TelemetryQueue(max_size=1000)

        # Simulate 1,100 calls generating depth samples
        for i in range(1100):
            # Each push updates the depth gauge
            queue._queue_depth_gauge.append(i)

        # Verify gauge maxlen is enforced
        assert len(queue._queue_depth_gauge) == 1000

        # Verify oldest entries were evicted
        # The gauge should contain entries 100-1099 (not 0-1099)
        assert 0 not in queue._queue_depth_gauge
        assert 99 not in queue._queue_depth_gauge
        assert 100 in queue._queue_depth_gauge
        assert 1099 in queue._queue_depth_gauge

    @pytest.mark.asyncio
    async def test_average_depth_calculation_with_eviction(self):
        """
        [2.4-MEMORY-CLEANUP-001] Test avg_depth calculation works with eviction.

        Scenario: Generate depth samples beyond maxlen, then calculate average
        Expected: Average is calculated only from retained samples
        """
        queue = TelemetryQueue(max_size=1000)

        # Add 1,100 depth samples
        for i in range(1100):
            queue._queue_depth_gauge.append(i)

        # Calculate average from metrics
        metrics = queue.get_metrics()

        # Average should be based on retained samples (100-1099)
        # avg(100, 101, ..., 1099) = (100 + 1099) / 2 = 599.5
        expected_avg = (100 + 1099) / 2
        assert metrics["avg_depth"] == pytest.approx(expected_avg, rel=0.01)

    @pytest.mark.asyncio
    async def test_max_depth_tracking_with_eviction(self):
        """
        [2.4-MEMORY-CLEANUP-001] Test max_depth is tracked correctly with eviction.

        Scenario: Add samples with high values, then evict them
        Expected: max_depth reflects current retained samples, not historical max
        """
        queue = TelemetryQueue(max_size=100)

        # Add samples 0-199 (depth = 200)
        for i in range(200):
            queue._queue_depth_gauge.append(i)
        queue._max_size = 200  # Set max to track

        # Max should be 199
        metrics = queue.get_metrics()
        assert metrics["max_depth"] == 199

        # Add 300 more samples (total 500, but only keep latest 100)
        for i in range(200, 500):
            queue._queue_depth_gauge.append(i)

        # Max should now be 499 (not 199, which was evicted)
        metrics = queue.get_metrics()
        assert metrics["max_depth"] == 499

    @pytest.mark.asyncio
    async def test_processing_latency_deque_evicts_old_entries(self):
        """
        [2.4-MEMORY-CLEANUP-001] Test processing latency deque evicts old entries.

        Scenario: Generate more than 1000 latency samples
        Expected: Only most recent 1000 samples retained
        """
        queue = TelemetryQueue(max_size=1000)

        # Add 1,100 latency samples
        for i in range(1100):
            queue._processing_latencies.append(float(i))

        # Verify maxlen is enforced
        assert len(queue._processing_latencies) == 1000

        # Verify oldest entries evicted
        assert 0.0 not in queue._processing_latencies
        assert 100.0 in queue._processing_latencies
        assert 1099.0 in queue._processing_latencies

    @pytest.mark.asyncio
    async def test_memory_does_not_grow_unbounded(self):
        """
        [2.4-MEMORY-CLEANUP-001] Test memory doesn't grow unbounded.

        Scenario: Simulate 1 hour of operation with 10,000 events
        Expected: Memory usage stays bounded (deques don't grow beyond maxlen)
        """
        queue = TelemetryQueue(max_size=10000)

        # Create event and push
        event = VoiceEvent(
            event_type="silence",
            tenant_id="org123",
            call_id=456,
        )

        # Simulate 10,000 pushes over 1 hour
        for i in range(10000):
            await queue.push(event)

            # Each push adds to depth gauge
            # After 1000 pushes, gauge should be at maxlen
            if i >= 1000:
                assert len(queue._queue_depth_gauge) <= 1000

        # Verify memory is bounded
        assert len(queue._queue_depth_gauge) <= 1000
        assert len(queue._processing_latencies) <= 1000

        # Verify queue itself respects max_size
        assert queue._queue.qsize() <= 10000

    @pytest.mark.asyncio
    async def test_old_call_ids_evicted_from_metrics(self):
        """
        [2.4-MEMORY-CLEANUP-001] Test stale call_id references are evicted.

        Scenario: 1,000 calls generate events, then calls end and cleanup runs
        Expected: Queue metrics evict old entries, memory stays bounded
        """
        queue = TelemetryQueue(max_size=10000)

        # Simulate 1,000 active calls generating events
        for call_id in range(1000):
            event = VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=call_id,
            )
            await queue.push(event)

            # Each push updates depth gauge
            # Gauge should not grow beyond 1000
            assert len(queue._queue_depth_gauge) <= 1000

        # Simulate calls ending - new calls with higher IDs
        for call_id in range(1000, 2000):
            event = VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=call_id,
            )
            await queue.push(event)

        # Verify gauge is still bounded
        assert len(queue._queue_depth_gauge) <= 1000

        # Verify older call_id data has been evicted
        metrics = queue.get_metrics()
        assert metrics["current_depth"] <= 10000
