"""
[2.3-UNIT-005] Test TTS orchestrator all-providers-failed scenario.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.tts.base import TTSResponse, TTSProviderBase
from services.tts.orchestrator import TTSOrchestrator, TTSAllProvidersFailedError
from tests.support.mock_helpers import _make_result


def _make_settings(**overrides):
    s = MagicMock()
    defaults = {
        "TTS_PRIMARY_PROVIDER": "elevenlabs",
        "TTS_FALLBACK_PROVIDER": "cartesia",
        "TTS_LATENCY_THRESHOLD_MS": 500,
        "TTS_CONSECUTIVE_SLOW_THRESHOLD": 3,
        "TTS_AUTO_RECOVERY_ENABLED": True,
        "TTS_RECOVERY_HEALTHY_COUNT": 5,
        "TTS_RECOVERY_LATENCY_MS": 300,
        "TTS_RECOVERY_COOLDOWN_SEC": 60,
        "TTS_SESSION_TTL_SEC": 3600,
        "TTS_CIRCUIT_OPEN_SEC": 30,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _mock_provider(
    name: str,
    *,
    latency_ms: float = 100.0,
    error: bool = False,
    error_message: str | None = None,
):
    p = MagicMock(spec=TTSProviderBase)
    p.provider_name = name
    p.synthesize = AsyncMock(
        return_value=TTSResponse(
            audio_bytes=b"",
            latency_ms=latency_ms,
            provider=name,
            content_type="",
            error=error,
            error_message=error_message,
        )
    )
    return p


def _mock_session():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_result())
    session.flush = AsyncMock()
    return session


class TestAllProvidersFailed:
    """
    [2.3-UNIT-005_P0] Given both providers timeout/error,
    when synthesize_for_call is invoked, then raises TTSAllProvidersFailedError.
    """

    @pytest.mark.asyncio
    async def test_both_timeout_raises_error(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", error=True, error_message="Timeout")
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        with pytest.raises(TTSAllProvidersFailedError):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-af",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

    @pytest.mark.asyncio
    async def test_both_attempts_logged_to_tts_requests(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", error=True, error_message="Error")
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        with pytest.raises(TTSAllProvidersFailedError):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-log",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        execute_calls = session.execute.call_args_list
        all_failed_calls = [
            c for c in execute_calls if len(c[0]) > 0 and "all_failed" in str(c[0][0])
        ]
        assert len(all_failed_calls) >= 2

    @pytest.mark.asyncio
    async def test_voice_event_emitted_on_all_failed(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", error=True, error_message="Timeout")
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        with pytest.raises(TTSAllProvidersFailedError):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-ve",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        execute_calls = session.execute.call_args_list
        voice_event_calls = [
            c
            for c in execute_calls
            if len(c[0]) > 0
            and "voice_events" in str(c[0][0])
            and "tts_all_providers_failed" in str(c)
        ]
        assert len(voice_event_calls) >= 1

    @pytest.mark.asyncio
    async def test_session_stays_on_last_attempted_provider(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", error=True, error_message="Timeout")
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        with pytest.raises(TTSAllProvidersFailedError):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-stay",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-stay") == "cartesia"

    @pytest.mark.asyncio
    async def test_error_code_is_correct(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", error=True, error_message="Timeout")
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = _mock_session()

        with pytest.raises(TTSAllProvidersFailedError) as exc_info:
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-code",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert exc_info.value.error_code == "TTS_ALL_PROVIDERS_FAILED"
