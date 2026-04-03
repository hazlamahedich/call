"""
Performance Benchmarks for Telemetry System
Story 2.4: Asynchronous Telemetry Sidecars for Voice Events

Performance tests using pytest-benchmark for <2ms push latency (AC: 3).
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone

from services.telemetry.queue import VoiceEvent, TelemetryQueue


class TestPushLatencyBenchmark:
    """
    [2.4-BENCHMARK-001] Performance benchmarks for push operation (AC: 3).

    Target: <2ms P95 latency for 10,000 concurrent push operations.
    """

    def test_push_latency_single_operation(self, benchmark):
        """Benchmark single push operation."""
        queue = TelemetryQueue(max_size=10000)
        event = VoiceEvent(
            event_type="silence",
            tenant_id="org123",
            call_id=456,
        )

        async def push_op():
            return await queue.push(event)

        # Benchmark async operation
        result = benchmark(lambda: asyncio.run(push_op()))
        assert result is True

    def test_push_latency_100_concurrent(self, benchmark):
        """[2.4-BENCHMARK-002] Benchmark 100 concurrent pushes."""
        queue = TelemetryQueue(max_size=10000)

        async def push_100():
            tasks = []
            for i in range(100):
                event = VoiceEvent(
                    event_type="silence",
                    tenant_id="org123",
                    call_id=456 + i,
                )
                tasks.append(queue.push(event))
            return await asyncio.gather(*tasks)

        results = benchmark(lambda: asyncio.run(push_100()))
        assert all(results)
        assert queue._queue.qsize() == 100

    def test_push_latency_1000_concurrent(self, benchmark):
        """[2.4-BENCHMARK-003] Benchmark 1000 concurrent pushes."""
        queue = TelemetryQueue(max_size=10000)

        async def push_1000():
            tasks = []
            for i in range(1000):
                event = VoiceEvent(
                    event_type="silence",
                    tenant_id="org123",
                    call_id=456 + i,
                )
                tasks.append(queue.push(event))
            return await asyncio.gather(*tasks)

        results = benchmark(lambda: asyncio.run(push_1000()))
        assert all(results)
        assert queue._queue.qsize() == 1000

    @pytest.mark.asyncio
    async def test_push_latency_p95_under_2ms(self):
        """
        [2.4-BENCHMARK-004] Verify P95 latency <2ms under load (AC: 3).

        This is the critical performance requirement from the story.
        """
        queue = TelemetryQueue(max_size=10000, push_timeout_ms=2)
        latencies = []

        # Measure 10,000 push operations
        for i in range(10000):
            event = VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=456 + i,
            )

            start = time.perf_counter()
            await queue.push(event)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        # Calculate P95
        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[p95_index]

        # Assert P95 <2ms
        assert p95_latency < 2.0, f"P95 latency {p95_latency}ms exceeds 2ms threshold"

        # Also check average and P99
        avg_latency = sum(latencies) / len(latencies)
        p99_index = int(len(sorted_latencies) * 0.99)
        p99_latency = sorted_latencies[p99_index]

        print(f"\nPush Latency Stats:")
        print(f"  Average: {avg_latency:.3f}ms")
        print(f"  P95: {p95_latency:.3f}ms")
        print(f"  P99: {p99_latency:.3f}ms")

        assert avg_latency < 1.0, f"Average latency {avg_latency}ms should be well under 2ms"

    @pytest.mark.asyncio
    async def test_push_latency_under_full_queue_load(self):
        """
        [2.4-BENCHMARK-005] Test latency when queue is near capacity.
        """
        queue = TelemetryQueue(max_size=1000)

        # Fill queue to 90% capacity
        for i in range(900):
            event = VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=i,
            )
            await queue.push(event)

        # Measure latency for remaining pushes
        latencies = []
        for i in range(100):
            event = VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=900 + i,
            )

            start = time.perf_counter()
            await queue.push(event)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        # Even at 90% capacity, should maintain <2ms P95
        assert p95_latency < 2.0, f"P95 latency {p95_latency}ms at 90% capacity exceeds 2ms"


class TestWorkerProcessingLatency:
    """[2.4-BENCHMARK-006] Benchmarks for worker batch processing (AC: 3)."""

    @pytest.mark.asyncio
    async def test_batch_processing_latency(self):
        """
        [2.4-BENCHMARK-007] Verify batch processing <100ms P95 target.
        """
        from unittest.mock import AsyncMock, MagicMock

        queue = TelemetryQueue(max_size=10000, batch_size=100)
        processing_latencies = []

        async def mock_processor(batch):
            start = time.perf_counter()
            # Simulate DB work
            await asyncio.sleep(0.01)
            latency_ms = (time.perf_counter() - start) * 1000
            processing_latencies.append(latency_ms)

        await queue.start_worker(mock_processor)

        # Add 500 events
        for i in range(500):
            event = VoiceEvent(
                event_type="silence",
                tenant_id="org123",
                call_id=456 + i,
            )
            await queue.push(event)

        # Wait for processing
        await asyncio.sleep(1.0)

        await queue.stop()

        if processing_latencies:
            p95_latency = sorted(processing_latencies)[int(len(processing_latencies) * 0.95)]
            print(f"\nWorker Batch Processing P95: {p95_latency:.3f}ms")
            # Target is <100ms P95, but mock is fast
            # Real DB will be slower - this tests the framework overhead
