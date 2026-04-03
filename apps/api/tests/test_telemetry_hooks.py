"""
Unit Tests for Voice Event Hooks
Story 2.4: Asynchronous Telemetry Sidecars for Voice Events

Tests for hook functions that capture voice events.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from services.telemetry.queue import VoiceEvent
from services.telemetry.hooks import VoiceEventHooks
from services.telemetry import telemetry_queue


class TestOnSilenceDetected:
    """[2.4-UNIT-HOOKS-001] Test silence detection hook."""

    @pytest.mark.asyncio
    async def test_on_silence_detected_pushes_event(self):
        """Test hook pushes silence event to queue (AC: 5)."""
        # Mock queue push
        telemetry_queue.push = AsyncMock(return_value=True)

        await VoiceEventHooks.on_silence_detected(
            tenant_id="org123",
            call_id=456,
            duration_ms=2000.0,
            audio_level=-60.0,
        )

        # Verify push was called
        telemetry_queue.push.assert_called_once()
        event = telemetry_queue.push.call_args[0][0]
        assert isinstance(event, VoiceEvent)
        assert event.event_type == "silence"
        assert event.tenant_id == "org123"
        assert event.call_id == 456
        assert event.duration_ms == 2000.0
        assert event.audio_level == -60.0
        assert event.provider == "deepgram"


class TestOnNoiseDetected:
    """[2.4-UNIT-HOOKS-002] Test noise detection hook."""

    @pytest.mark.asyncio
    async def test_on_noise_detected_pushes_event(self):
        """Test hook pushes noise event to queue (AC: 5)."""
        telemetry_queue.push = AsyncMock(return_value=True)

        await VoiceEventHooks.on_noise_detected(
            tenant_id="org123",
            call_id=456,
            audio_level=-15.0,
        )

        telemetry_queue.push.assert_called_once()
        event = telemetry_queue.push.call_args[0][0]
        assert event.event_type == "noise"
        assert event.tenant_id == "org123"
        assert event.call_id == 456
        assert event.audio_level == -15.0


class TestOnInterruptionDetected:
    """[2.4-UNIT-HOOKS-003] Test interruption detection hook."""

    @pytest.mark.asyncio
    async def test_on_interruption_detected_pushes_event(self):
        """Test hook pushes interruption event to queue (AC: 5)."""
        telemetry_queue.push = AsyncMock(return_value=True)

        await VoiceEventHooks.on_interruption_detected(
            tenant_id="org123",
            call_id=456,
            confidence_score=0.9,
        )

        telemetry_queue.push.assert_called_once()
        event = telemetry_queue.push.call_args[0][0]
        assert event.event_type == "interruption"
        assert event.tenant_id == "org123"
        assert event.call_id == 456
        assert event.confidence_score == 0.9
        assert event.provider == "vapi"


class TestOnTalkoverDetected:
    """[2.4-UNIT-HOOKS-004] Test talkover detection hook."""

    @pytest.mark.asyncio
    async def test_on_talkover_detected_pushes_event(self):
        """Test hook pushes talkover event to queue (AC: 5)."""
        telemetry_queue.push = AsyncMock(return_value=True)

        await VoiceEventHooks.on_talkover_detected(
            tenant_id="org123",
            call_id=456,
            duration_ms=500.0,
        )

        telemetry_queue.push.assert_called_once()
        event = telemetry_queue.push.call_args[0][0]
        assert event.event_type == "talkover"
        assert event.tenant_id == "org123"
        assert event.call_id == 456
        assert event.duration_ms == 500.0


class TestHookNonBlocking:
    """[2.4-UNIT-HOOKS-005] Test hooks are non-blocking (AC: 1)."""

    @pytest.mark.asyncio
    async def test_hooks_return_immediately(self):
        """Test hooks return immediately after pushing to queue."""
        import time

        telemetry_queue.push = AsyncMock(return_value=True)

        start = time.perf_counter()
        await VoiceEventHooks.on_silence_detected(
            tenant_id="org123",
            call_id=456,
            duration_ms=2000.0,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should return immediately (<1ms)
        assert elapsed_ms < 1.0

    @pytest.mark.asyncio
    async def test_hooks_handle_missing_optional_fields(self):
        """[2.4-UNIT-HOOKS-006] Test hooks handle None values for optional fields."""
        telemetry_queue.push = AsyncMock(return_value=True)

        # All optional fields omitted
        await VoiceEventHooks.on_silence_detected(
            tenant_id="org123",
            call_id=456,
            duration_ms=2000.0,
        )

        event = telemetry_queue.push.call_args[0][0]
        assert event.audio_level == -60.0  # Default value
        assert event.confidence_score is None
        assert event.sentiment_score is None
        assert event.metadata is None
