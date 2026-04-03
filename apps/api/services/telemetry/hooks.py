"""
Voice Event Hooks
Story 2.4: Asynchronous Telemetry Sidecars for Voice Events

Hook functions called from voice pipeline when events are detected.
Push events to telemetry queue non-blocking (<2ms).

AC: 1, 5 - Non-blocking event capture with structured event data
"""

import logging

from models.base import VoiceEventType, TelemetryProvider, utc_now
from .queue import VoiceEvent, telemetry_queue


class VoiceEventHooks:
    """
    Static hook functions for voice event detection.

    Called from transcription service and Vapi webhooks when events occur.
    Pushes events to telemetry queue immediately without blocking.

    AC: 1 - Push to queue within 2ms, non-blocking
    AC: 5 - Hook functions for all event types
    """

    @staticmethod
    async def on_silence_detected(
        tenant_id: str,
        call_id: int,
        duration_ms: float,
        audio_level: float = -60.0,
    ) -> None:
        """
        Hook called when silence is detected (VAD).

        Args:
            tenant_id: Tenant organization ID
            call_id: Related call record ID
            duration_ms: Duration of silence in milliseconds
            audio_level: Audio level in dB (default -60 for silence)
        """
        event = VoiceEvent(
            event_type="silence",
            tenant_id=tenant_id,
            call_id=call_id,
            timestamp=utc_now(),
            duration_ms=duration_ms,
            audio_level=audio_level,
            provider="deepgram",  # VAD from transcription service
        )

        await telemetry_queue.push(event)

    @staticmethod
    async def on_noise_detected(
        tenant_id: str,
        call_id: int,
        audio_level: float,
    ) -> None:
        """
        Hook called when noise floor exceeds threshold.

        Args:
            tenant_id: Tenant organization ID
            call_id: Related call record ID
            audio_level: Audio level in dB
        """
        event = VoiceEvent(
            event_type="noise",
            tenant_id=tenant_id,
            call_id=call_id,
            timestamp=utc_now(),
            audio_level=audio_level,
            provider="deepgram",
        )

        await telemetry_queue.push(event)

    @staticmethod
    async def on_interruption_detected(
        tenant_id: str,
        call_id: int,
        confidence_score: float = 0.8,
    ) -> None:
        """
        Hook called when lead interrupts AI speech.

        Args:
            tenant_id: Tenant organization ID
            call_id: Related call record ID
            confidence_score: Detection confidence (0.0-1.0)
        """
        event = VoiceEvent(
            event_type="interruption",
            tenant_id=tenant_id,
            call_id=call_id,
            timestamp=utc_now(),
            confidence_score=confidence_score,
            provider="vapi",
        )

        await telemetry_queue.push(event)

    @staticmethod
    async def on_talkover_detected(
        tenant_id: str,
        call_id: int,
        duration_ms: float,
    ) -> None:
        """
        Hook called when talkover (overlap) is detected.

        Args:
            tenant_id: Tenant organization ID
            call_id: Related call record ID
            duration_ms: Duration of overlap in milliseconds
        """
        event = VoiceEvent(
            event_type="talkover",
            tenant_id=tenant_id,
            call_id=call_id,
            timestamp=utc_now(),
            duration_ms=duration_ms,
            provider="deepgram",
        )

        await telemetry_queue.push(event)
