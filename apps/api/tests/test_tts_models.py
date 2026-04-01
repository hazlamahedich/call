"""
[2.3-UNIT-009] Test TTS model validation.
"""

import pytest
from datetime import datetime, timezone

from models.tts_request import TTSRequest
from models.tts_provider_switch import TTSProviderSwitch


class TestTTSRequestModel:
    """
    [2.3-UNIT-009_P1] Given TTSRequest fields,
    when model is validated, then fields have correct constraints.
    """

    def test_tts_request_fields_present(self):
        data = {
            "callId": 1,
            "vapiCallId": "vci-test",
            "provider": "elevenlabs",
            "voiceId": "voice-123",
            "textLength": 42,
            "latencyMs": 150.5,
            "status": "success",
            "errorMessage": None,
        }
        req = TTSRequest.model_validate(data)
        assert req.provider == "elevenlabs"
        assert req.status == "success"
        assert req.latency_ms == 150.5

    def test_latency_ms_nullable_for_error_rows(self):
        data = {
            "call_id": 1,
            "vapi_call_id": "vci-err",
            "provider": "elevenlabs",
            "voice_id": "voice-123",
            "text_length": 42,
            "latency_ms": None,
            "status": "timeout",
            "error_message": "Connection timeout",
        }
        req = TTSRequest.model_validate(data)
        assert req.latency_ms is None
        assert req.status == "timeout"

    def test_status_all_failed(self):
        data = {
            "call_id": 1,
            "vapi_call_id": "vci-af",
            "provider": "cartesia",
            "voice_id": "voice-456",
            "text_length": 10,
            "latency_ms": None,
            "status": "all_failed",
            "error_message": "all providers failed",
        }
        req = TTSRequest.model_validate(data)
        assert req.status == "all_failed"

    def test_received_at_auto_set(self):
        before = datetime.now(timezone.utc)
        data = {
            "provider": "elevenlabs",
            "status": "success",
        }
        req = TTSRequest.model_validate(data)
        after = datetime.now(timezone.utc)
        assert before <= req.received_at <= after


class TestTTSProviderSwitchModel:
    """
    [2.3-UNIT-009_P1] Given TTSProviderSwitch fields,
    when model is validated, then switched_at and created_at are semantically distinct.
    """

    def test_provider_switch_fields_present(self):
        data = {
            "callId": 1,
            "vapiCallId": "vci-switch",
            "fromProvider": "elevenlabs",
            "toProvider": "cartesia",
            "reason": "latency_threshold_exceeded",
            "consecutiveSlowCount": 3,
            "lastLatencyMs": 550.0,
        }
        switch = TTSProviderSwitch.model_validate(data)
        assert switch.from_provider == "elevenlabs"
        assert switch.to_provider == "cartesia"
        assert switch.consecutive_slow_count == 3

    def test_switched_at_semantic_distinction(self):
        data = {
            "fromProvider": "elevenlabs",
            "toProvider": "cartesia",
            "reason": "latency_threshold_exceeded",
        }
        switch = TTSProviderSwitch.model_validate(data)
        assert switch.switched_at is not None
        assert isinstance(switch.switched_at, datetime)

    def test_last_latency_ms_nullable(self):
        data = {
            "fromProvider": "elevenlabs",
            "toProvider": "cartesia",
            "reason": "provider_error",
            "lastLatencyMs": None,
        }
        switch = TTSProviderSwitch.model_validate(data)
        assert switch.last_latency_ms is None
