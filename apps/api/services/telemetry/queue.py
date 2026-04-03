"""
Telemetry Queue System
Story 2.4: Asynchronous Telemetry Sidecars for Voice Events

Provides non-blocking (<2ms) event capture for voice telemetry.
Uses in-memory queue with background batch processing.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Deque, List, Optional

from models.base import VoiceEventType, TelemetryProvider


@dataclass
class VoiceEvent:
    """
    Voice event data captured for telemetry.

    Designed for minimal overhead during event capture.
    All fields are optional to support different event types.
    """

    event_type: VoiceEventType
    tenant_id: str
    call_id: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: Optional[float] = None
    audio_level: Optional[float] = None
    confidence_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    provider: TelemetryProvider = "vapi"
    metadata: Optional[dict] = None
    queue_depth_at_capture: Optional[int] = None  # AC: 6 - Track queue depth for monitoring


class TelemetryQueue:
    """
    Non-blocking queue for voice event telemetry.

    Guarantees <2ms push latency to avoid blocking voice pipeline.
    Events are dropped (with warning log) if queue is full.

    AC: 1, 3, 8 - Non-blocking capture, <2ms latency, graceful degradation
    """

    def __init__(
        self,
        max_size: int = 10000,
        batch_size: int = 100,
        push_timeout_ms: int = 2,
    ):
        """
        Initialize telemetry queue.

        Args:
            max_size: Maximum queue capacity (events dropped if full)
            batch_size: Target batch size for worker processing
            push_timeout_ms: Timeout for push operation (enforces <2ms guarantee)
        """
        self._queue: asyncio.Queue[VoiceEvent] = asyncio.Queue(maxsize=max_size)
        self._max_size = max_size
        self._batch_size = batch_size
        self._push_timeout = push_timeout_ms / 1000.0  # Convert to seconds

        # Worker state
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running = False

        # Metrics tracking (AC: 6)
        self._queue_depth_gauge: Deque[int] = deque(maxlen=1000)
        self._processing_latencies: Deque[float] = deque(maxlen=1000)
        self._events_processed = 0
        self._start_time: Optional[datetime] = None

    async def push(self, event: VoiceEvent) -> bool:
        """
        Non-blocking push to telemetry queue.

        Guarantees <2ms latency via timeout. Events dropped if queue full.

        AC: 1, 3 - Push completes <2ms OR returns False (event dropped)

        Args:
            event: Voice event to capture

        Returns:
            True if event queued successfully, False if dropped
        """
        start_time = time.perf_counter()

        try:
            # Non-blocking push with 2ms timeout
            await asyncio.wait_for(
                self._queue.put(event),
                timeout=self._push_timeout,
            )

            # Track push latency
            latency_ms = (time.perf_counter() - start_time) * 1000
            if latency_ms > self._push_timeout * 1000:
                # Log warning if push exceeded timeout (shouldn't happen)
                import logging
                logging.warning(
                    f"Push latency {latency_ms:.2f}ms exceeded threshold {self._push_timeout * 1000}ms",
                    extra={"code": "TELEMETRY_PUSH_SLOW"},
                )

            # Track queue depth and store it in the event
            current_depth = self._queue.qsize()
            self._queue_depth_gauge.append(current_depth)

            # Store queue depth in event for AC: 6
            event.queue_depth_at_capture = current_depth

            return True

        except asyncio.TimeoutError:
            # Push timed out - event dropped (graceful degradation)
            import logging
            logging.warning(
                "Telemetry queue full - event dropped",
                extra={
                    "code": "TELEMETRY_QUEUE_FULL",
                    "dropped": 1,
                    "queue_size": self._max_size,
                },
            )
            return False

        except Exception as e:
            # Unexpected error - log and drop event
            import logging
            logging.error(
                f"Telemetry queue push error: {e}",
                extra={"code": "TELEMETRY_QUEUE_ERROR"},
            )
            return False

    async def start_worker(self, processor: Callable[[List[VoiceEvent]], None]) -> None:
        """
        Start background worker for batch processing.

        AC: 2 - Background worker processes events asynchronously

        Args:
            processor: Async callable that processes event batches
        """
        if self._is_running:
            import logging
            logging.warning("Worker already running", extra={"code": "TELEMETRY_WORKER_RUNNING"})
            return

        self._is_running = True
        self._start_time = datetime.now(timezone.utc)
        self._worker_task = asyncio.create_task(self._worker_loop(processor))

        import logging
        logging.info(
            f"Telemetry worker started (batch_size={self._batch_size})",
            extra={"code": "TELEMETRY_WORKER_STARTED"},
        )

    async def _worker_loop(
        self,
        processor: Callable[[List[VoiceEvent]], None],
    ) -> None:
        """
        Background worker loop for batch processing.

        Collects events into batches and calls processor.
        Batches when: batch_size collected OR 1s deadline expires.

        AC: 2 - Batch processing with 1s deadline
        AC: 8 - Graceful degradation on errors
        """
        import logging

        while self._is_running:
            try:
                batch: List[VoiceEvent] = []
                deadline = time.time() + 1.0  # 1 second deadline

                # Collect up to batch_size events
                while len(batch) < self._batch_size and time.time() < deadline:
                    try:
                        # Wait for next event with timeout
                        remaining_time = max(0, deadline - time.time())
                        event = await asyncio.wait_for(
                            self._queue.get(),
                            timeout=remaining_time,
                        )
                        batch.append(event)
                    except asyncio.TimeoutError:
                        # Deadline expired - process what we have
                        break

                # Process batch if we have events
                if batch:
                    batch_start = time.perf_counter()

                    try:
                        await processor(batch)

                        # Track processing latency
                        latency_ms = (time.perf_counter() - batch_start) * 1000
                        self._processing_latencies.append(latency_ms)
                        self._events_processed += len(batch)

                        logging.info(
                            f"Telemetry batch processed: {len(batch)} events in {latency_ms:.2f}ms",
                            extra={
                                "code": "TELEMETRY_BATCH_SUCCESS",
                                "batch_size": len(batch),
                                "latency_ms": latency_ms,
                            },
                        )

                    except Exception as e:
                        # DB error - log and continue (graceful degradation)
                        logging.error(
                            f"Telemetry batch processing failed: {e}",
                            extra={
                                "code": "TELEMETRY_BATCH_ERROR",
                                "batch_size": len(batch),
                                "error": str(e),
                            },
                        )
                        # Events are lost - acceptable for telemetry

            except asyncio.CancelledError:
                # Worker shutdown requested
                break
            except Exception as e:
                # Unexpected error - log and continue
                logging.error(
                    f"Telemetry worker loop error: {e}",
                    extra={"code": "TELEMETRY_WORKER_ERROR"},
                )
                await asyncio.sleep(0.1)  # Brief pause before retry

    async def stop(self) -> None:
        """
        Graceful shutdown of worker.

        AC: 8 - Clean shutdown
        """
        if not self._is_running:
            return

        self._is_running = False

        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await asyncio.wait_for(self._worker_task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        import logging
        logging.info(
            "Telemetry worker stopped",
            extra={
                "code": "TELEMETRY_WORKER_STOPPED",
                "events_processed": self._events_processed,
            },
        )

    def get_metrics(self) -> dict:
        """
        Get queue metrics for monitoring.

        AC: 6 - Queue health metrics exposed

        Returns:
            Dict with current_depth, avg_depth, max_depth, is_running,
                 processing_latency_ms_p95, events_per_second
        """
        current_depth = self._queue.qsize()

        # Calculate average depth
        if self._queue_depth_gauge:
            avg_depth = sum(self._queue_depth_gauge) / len(self._queue_depth_gauge)
            max_depth = max(self._queue_depth_gauge)
        else:
            avg_depth = 0
            max_depth = 0

        # Calculate P95 processing latency
        if self._processing_latencies:
            sorted_latencies = sorted(self._processing_latencies)
            p95_index = int(len(sorted_latencies) * 0.95)
            p95_latency = sorted_latencies[p95_index]
        else:
            p95_latency = 0.0

        # Calculate events per second
        if self._start_time:
            uptime_seconds = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            events_per_second = self._events_processed / uptime_seconds if uptime_seconds > 0 else 0
        else:
            events_per_second = 0

        return {
            "current_depth": current_depth,
            "avg_depth": round(avg_depth, 2),
            "max_depth": max_depth,
            "is_running": self._is_running,
            "processing_latency_ms_p95": round(p95_latency, 2),
            "events_per_second": round(events_per_second, 2),
        }


# Global singleton instance (AC: 1)
telemetry_queue = TelemetryQueue()
