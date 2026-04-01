"""
[2.3-UNIT-016] Test TTS recording edge cases — _record_all_failed per-provider exceptions,
flush exceptions, _perform_switch continues to emit after DB error.
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
        "TTS_SESSION_TTL_SEC": 7200,
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
            audio_bytes=b"" if error else b"audio",
            latency_ms=latency_ms,
            provider=name,
            content_type="" if error else "audio/mpeg",
            error=error,
            error_message=error_message,
        )
    )
    return p


class TestRecordAllFailedExceptions:
    """
    [2.3-UNIT-016_P1] Exception handling in _record_all_failed.
    """

    @pytest.mark.asyncio
    async def test_P1_per_provider_insert_exception_handled(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", error=True, error_message="Timeout")
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )

        session = AsyncMock()
        call_count = [0]

        async def _execute(*args, **kwargs):
            call_count[0] += 1
            if "all_failed" in str(args):
                raise RuntimeError("DB error during all_failed insert")
            return _make_result()

        session.execute = AsyncMock(side_effect=_execute)
        session.flush = AsyncMock()

        with pytest.raises(TTSAllProvidersFailedError):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-af1",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

    @pytest.mark.asyncio
    async def test_P1_flush_exception_handled(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", error=True, error_message="Timeout")
        fallback = _mock_provider("cartesia", error=True, error_message="Timeout")
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )

        session = AsyncMock()
        flush_count = [0]

        async def _execute(*args, **kwargs):
            return _make_result()

        async def _flush():
            flush_count[0] += 1
            if flush_count[0] >= 3:
                raise RuntimeError("DB flush failed on all_failed")

        session.execute = AsyncMock(side_effect=_execute)
        session.flush = AsyncMock(side_effect=_flush)

        with pytest.raises(TTSAllProvidersFailedError):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-af2",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )


class TestPerformSwitchContinuesAfterDBError:
    """
    [2.3-UNIT-016_P1] _perform_switch still emits voice event after switch insert fails.
    """

    @pytest.mark.asyncio
    async def test_P1_voice_event_emitted_after_switch_insert_failure(self):
        settings = _make_settings()
        primary = _mock_provider("elevenlabs", latency_ms=600)
        fallback = _mock_provider("cartesia", latency_ms=100)
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )

        session = AsyncMock()
        switch_insert_failed = [False]

        async def _execute(*args, **kwargs):
            sql_str = str(args[0]) if args else ""
            if "tts_provider_switches" in sql_str and not switch_insert_failed[0]:
                switch_insert_failed[0] = True
                raise RuntimeError("Switch insert failed")
            return _make_result()

        session.execute = AsyncMock(side_effect=_execute)
        session.flush = AsyncMock()

        for _ in range(3):
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-switch-err",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        assert orchestrator.get_session_provider("vci-switch-err") == "cartesia"

        calls = session.execute.call_args_list
        voice_event_calls = [
            c for c in calls if len(c[0]) > 0 and "voice_events" in str(c[0][0])
        ]
        assert len(voice_event_calls) >= 1


class TestAllFailedErrorMessages:
    """
    [2.3-UNIT-016_P2] Error messages contain both provider error details.
    """

    @pytest.mark.asyncio
    async def test_P2_both_providers_failed_error_contains_details(self):
        settings = _make_settings()
        primary = _mock_provider(
            "elevenlabs", error=True, error_message="Connection refused"
        )
        fallback = _mock_provider("cartesia", error=True, error_message="Rate limited")
        orchestrator = TTSOrchestrator(
            providers={"elevenlabs": primary, "cartesia": fallback},
            app_settings=settings,
        )
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_make_result())
        session.flush = AsyncMock()

        with pytest.raises(TTSAllProvidersFailedError) as exc_info:
            await orchestrator.synthesize_for_call(
                session,
                call_id=1,
                vapi_call_id="vci-msg",
                org_id="org-1",
                text="hello",
                voice_id="v1",
            )

        msg = str(exc_info.value)
        assert "Connection refused" in msg
        assert "Rate limited" in msg
