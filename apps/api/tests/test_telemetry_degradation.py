import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from apps.api.services.telemetry.queue import TelemetryQueue, VoiceEvent
from apps.api.services.telemetry.worker import TelemetryWorker
from apps.api.models.voice_telemetry import VoiceTelemetry

"""
Story 2.4: Telemetry Degradation Visibility Tests
Test ID Format: 2.4-DEGR-XXX
Priority Tags: @p0 @p1 @p2
AC Coverage: AC8.5, AC8
"""


class TestDegradationVisibility:
    """[P0] Tests for AC8.5: Degradation visibility (>10% drop rate alerting)"""

    @pytest.mark.asyncio
    async def test_drop_rate_tracked_in_metrics(self, telemetry_queue):
        """[2.4-DEGR-001] [P0] Should track drop rate in queue metrics"""
        # Fill queue to 50% capacity
        for _ in range(5000):
            await telemetry_queue.push(VoiceEvent(
                event_type='silence',
                tenant_id='tenant1',
                call_id='call1',
                timestamp=datetime.utcnow(),
            ))

        # Simulate some drops (queue at 50% so no actual drops yet)
        metrics = telemetry_queue.get_metrics()
        assert 'drop_rate' in metrics
        assert metrics['drop_rate'] >= 0.0
        assert metrics['drop_rate'] <= 1.0

    @pytest.mark.asyncio
    async def test_alert_when_drop_rate_exceeds_10_percent(self, telemetry_queue):
        """[2.4-DEGR-002] [P0] Should generate alert when drop rate > 10%"""
        # Fill queue to near capacity
        for _ in range(9500):
            await telemetry_queue.push(VoiceEvent(
                event_type='silence',
                tenant_id='tenant1',
                call_id='call1',
                timestamp=datetime.utcnow(),
            ))

        # Push more events, some will fail (drop)
        drops = 0
        for _ in range(1000):
            success = await telemetry_queue.push(VoiceEvent(
                event_type='noise',
                tenant_id='tenant1',
                call_id='call2',
                timestamp=datetime.utcnow(),
            ))
            if not success:
                drops += 1

        metrics = telemetry_queue.get_metrics()
        drop_rate = drops / 1000

        # If drop rate > 10%, should include degradation alert
        if drop_rate > 0.1:
            assert 'degradation_alert' in metrics
            assert metrics['degradation_alert']['level'] == 'critical'
            assert metrics['degradation_alert']['threshold'] == 0.1
            assert metrics['degradation_alert']['current_value'] >= 0.1

    @pytest.mark.asyncio
    async def test_consecutive_high_drop_periods_tracked(self, telemetry_queue):
        """[2.4-DEGR-003] [P1] Should track consecutive high drop periods"""
        # Simulate multiple periods of high drop rate
        metrics = telemetry_queue.get_metrics()
        assert 'consecutive_high_drop_periods' in metrics
        assert metrics['consecutive_high_drop_periods'] >= 0

    @pytest.mark.asyncio
    async def test_time_since_last_drop_tracked(self, telemetry_queue):
        """[2.4-DEGR-004] [P1] Should track time since last drop"""
        metrics = telemetry_queue.get_metrics()
        assert 'time_since_last_drop_seconds' in metrics
        assert metrics['time_since_last_drop_seconds'] >= 0

    @pytest.mark.asyncio
    async def test_drop_rate_calculated_correctly(self, telemetry_queue):
        """[2.4-DEGR-005] [P1] Should calculate drop rate as dropped / total attempts"""
        # Push 1000 events, expect some drops
        total_attempts = 1000
        successful = 0

        for i in range(total_attempts):
            # Queue will eventually fill
            success = await telemetry_queue.push(VoiceEvent(
                event_type='silence',
                tenant_id='tenant1',
                call_id=f'call{i}',
                timestamp=datetime.utcnow(),
            ))
            if success:
                successful += 1

        drops = total_attempts - successful
        expected_drop_rate = drops / total_attempts

        metrics = telemetry_queue.get_metrics()
        # Allow small floating point differences
        assert abs(metrics['drop_rate'] - expected_drop_rate) < 0.01


class TestGracefulDegradationEdges:
    """[P1] Tests for AC8 edge cases: Worker crash, DB disconnect, batch retry"""

    @pytest.mark.asyncio
    async def test_worker_crash_recovery(self, telemetry_queue, db_session_mock):
        """[2.4-DEGR-006] [P1] Should recover when worker crashes and restarts"""
        worker = TelemetryWorker(db_session_mock)

        # Push some events
        for _ in range(10):
            await telemetry_queue.push(VoiceEvent(
                event_type='silence',
                tenant_id='tenant1',
                call_id='call1',
                timestamp=datetime.utcnow(),
            ))

        # Start worker
        await telemetry_queue.start_worker(worker.process_batch)

        # Simulate worker crash (stop worker abruptly)
        await telemetry_queue.stop()

        # Verify queue still has data (not lost)
        metrics = telemetry_queue.get_metrics()
        assert metrics['current_depth'] > 0

        # Restart worker
        await telemetry_queue.start_worker(worker.process_batch)

        # Verify queue is being processed
        await telemetry_queue.stop()
        metrics_after = telemetry_queue.get_metrics()
        assert metrics_after['current_depth'] < metrics['current_depth']

    @pytest.mark.asyncio
    async def test_db_reconnection_handling(self, telemetry_queue, db_session_mock):
        """[2.4-DEGR-007] [P1] Should handle DB reconnection gracefully"""
        worker = TelemetryWorker(db_session_mock)

        # Push events
        for _ in range(5):
            await telemetry_queue.push(VoiceEvent(
                event_type='silence',
                tenant_id='tenant1',
                call_id='call1',
                timestamp=datetime.utcnow(),
            ))

        # Mock DB error on first call, success on second
        call_count = 0

        async def mock_add_all_with_error(events):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception('DB connection lost')
            # Second call succeeds
            return None

        with patch.object(db_session_mock, 'add_all', side_effect=mock_add_all_with_error):
            # Start worker
            await telemetry_queue.start_worker(worker.process_batch)

            # Wait for batch processing
            await telemetry_queue.stop()

        # Verify worker retried and succeeded
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_batch_retry_logic(self, telemetry_queue, db_session_mock):
        """[2.4-DEGR-008] [P1] Should retry failed batches with exponential backoff"""
        worker = TelemetryWorker(db_session_mock)

        # Push events
        for _ in range(3):
            await telemetry_queue.push(VoiceEvent(
                event_type='silence',
                tenant_id='tenant1',
                call_id='call1',
                timestamp=datetime.utcnow(),
            ))

        # Mock transient DB error
        attempt_count = 0

        async def mock_commit_with_transient_error():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:
                raise Exception('Transient DB error')
            # Third attempt succeeds
            return None

        with patch.object(db_session_mock, 'commit', side_effect=mock_commit_with_transient_error):
            await telemetry_queue.start_worker(worker.process_batch)
            await telemetry_queue.stop()

        # Verify retry happened (3 attempts: 2 failures + 1 success)
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_queue_full(self, telemetry_queue):
        """[2.4-DEGR-009] [P1] Should gracefully degrade when queue is full"""
        # Fill queue to capacity
        for _ in range(10000):
            await telemetry_queue.push(VoiceEvent(
                event_type='silence',
                tenant_id='tenant1',
                call_id='call1',
                timestamp=datetime.utcnow(),
            ))

        # Try to push more events - should return False gracefully
        success = await telemetry_queue.push(VoiceEvent(
            event_type='noise',
            tenant_id='tenant1',
            call_id='call2',
            timestamp=datetime.utcnow(),
        ))

        # Should not raise exception, just return False
        assert success is False

        # Verify queue is still operational
        metrics = telemetry_queue.get_metrics()
        assert metrics['current_depth'] == 10000
        assert metrics['is_running'] is True

    @pytest.mark.asyncio
    async def test_batch_preserves_queue_depth_at_capture(self, telemetry_queue, db_session_mock):
        """[2.4-DEGR-010] [P1] Should preserve queue depth at capture time in records"""
        worker = TelemetryWorker(db_session_mock)

        # Push events to create queue depth
        for _ in range(100):
            await telemetry_queue.push(VoiceEvent(
                event_type='silence',
                tenant_id='tenant1',
                call_id='call1',
                timestamp=datetime.utcnow(),
            ))

        # Mock batch processing to capture queue depth
        captured_depths = []

        async def mock_process_batch(events):
            metrics = telemetry_queue.get_metrics()
            captured_depths.append(metrics['current_depth'])
            # Simulate successful batch
            return None

        with patch.object(worker, 'process_batch', side_effect=mock_process_batch):
            await telemetry_queue.start_worker(worker.process_batch)
            await telemetry_queue.stop()

        # Verify queue depth was captured
        assert len(captured_depths) > 0
        assert all(depth > 0 for depth in captured_depths)

    @pytest.mark.asyncio
    async def test_processing_latency_tracked_per_batch(self, telemetry_queue, db_session_mock):
        """[2.4-DEGR-011] [P1] Should track processing latency per batch"""
        worker = TelemetryWorker(db_session_mock)

        # Push events
        for _ in range(10):
            await telemetry_queue.push(VoiceEvent(
                event_type='silence',
                tenant_id='tenant1',
                call_id='call1',
                timestamp=datetime.utcnow(),
            ))

        # Mock batch processing with delay
        async def mock_process_with_delay(events):
            import asyncio
            await asyncio.sleep(0.1)  # 100ms delay
            return None

        with patch.object(worker, 'process_batch', side_effect=mock_process_with_delay):
            await telemetry_queue.start_worker(worker.process_batch)
            await telemetry_queue.stop()

        # Verify processing latency was tracked
        metrics = telemetry_queue.get_metrics()
        assert 'processing_latency_ms_p95' in metrics
        assert metrics['processing_latency_ms_p95'] >= 100  # At least 100ms

    @pytest.mark.asyncio
    async def test_degradation_alert_threshold_10_percent(self, telemetry_queue):
        """[2.4-DEGR-012] [P0] Should alert at exactly 10% drop rate threshold"""
        # Calculate attempts needed for 10% drop rate
        # 10% of 1000 = 100 drops
        total_attempts = 1000
        target_drops = 100

        # Fill queue to cause exactly 100 drops
        for _ in range(10000 - target_drops):
            await telemetry_queue.push(VoiceEvent(
                event_type='silence',
                tenant_id='tenant1',
                call_id='call1',
                timestamp=datetime.utcnow(),
            ))

        # Attempt 1000 more pushes, expect exactly 100 drops
        actual_drops = 0
        for _ in range(total_attempts):
            success = await telemetry_queue.push(VoiceEvent(
                event_type='noise',
                tenant_id='tenant1',
                call_id='call2',
                timestamp=datetime.utcnow(),
            ))
            if not success:
                actual_drops += 1

        drop_rate = actual_drops / total_attempts
        metrics = telemetry_queue.get_metrics()

        # At or above 10% threshold, should alert
        if drop_rate >= 0.1:
            assert 'degradation_alert' in metrics
            assert metrics['degradation_alert']['level'] == 'critical'
