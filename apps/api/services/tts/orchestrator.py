from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings, settings
from database.session import set_tenant_context
from .base import TTSProviderBase, TTSResponse

logger = logging.getLogger(__name__)


class ProviderCircuitBreaker:
    """Tracks per-provider failure state for circuit breaker pattern.

    After a provider accumulates enough session-level fallbacks (trip_threshold),
    the circuit opens for open_duration_sec. While open, new sessions skip the
    provider and start on a healthy fallback. The circuit auto-closes after the
    cooldown, allowing one new session to retry.
    """

    def __init__(
        self, open_duration_sec: float = 30.0, trip_threshold: int = 3
    ) -> None:
        self._open_duration = open_duration_sec
        self._trip_threshold = trip_threshold
        self._global_fallback_count: dict[str, int] = {}
        self._open_until: dict[str, float] = {}

    def record_fallback(self, provider_name: str) -> None:
        count = self._global_fallback_count.get(provider_name, 0) + 1
        self._global_fallback_count[provider_name] = count
        if count >= self._trip_threshold:
            self._open_until[provider_name] = time.monotonic() + self._open_duration
            logger.warning(
                "TTS provider circuit breaker tripped",
                extra={
                    "code": "TTS_CIRCUIT_TRIPPED",
                    "provider": provider_name,
                    "fallback_count": count,
                    "open_duration_sec": self._open_duration,
                },
            )

    def is_open(self, provider_name: str) -> bool:
        deadline = self._open_until.get(provider_name)
        if deadline is None:
            return False
        if time.monotonic() >= deadline:
            del self._open_until[provider_name]
            self._global_fallback_count.pop(provider_name, None)
            return False
        return True

    def record_success(self, provider_name: str) -> None:
        self._global_fallback_count.pop(provider_name, None)
        self._open_until.pop(provider_name, None)


class TTSAllProvidersFailedError(Exception):
    def __init__(self, message: str = "All TTS providers failed"):
        self.error_code = "TTS_ALL_PROVIDERS_FAILED"
        super().__init__(message)


@dataclass
class SessionTTSState:
    active_provider: str
    consecutive_slow: int = 0
    recovery_healthy_count: int = 0
    latency_history: deque = field(default_factory=lambda: deque(maxlen=10))
    last_switch_at: float = 0.0
    created_at: float = field(default_factory=time.monotonic)


class TTSOrchestrator:
    # IMPORTANT: _session_state is a plain dict protected by asyncio's single-threaded
    # event loop. All dict mutations MUST occur within async coroutines — never in
    # run_in_executor or thread pools. If the codebase later introduces multi-threading
    # for TTS, replace with asyncio.Lock-protected access.

    def __init__(
        self,
        providers: dict[str, TTSProviderBase],
        app_settings: Settings | None = None,
    ) -> None:
        self._providers = providers
        self._settings = app_settings or settings
        self._session_state: dict[str, SessionTTSState] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._circuit_breaker = ProviderCircuitBreaker(
            open_duration_sec=getattr(self._settings, "TTS_CIRCUIT_OPEN_SEC", 30),
            trip_threshold=self._settings.TTS_CONSECUTIVE_SLOW_THRESHOLD,
        )

    async def synthesize_for_call(
        self,
        session: AsyncSession,
        call_id: int,
        vapi_call_id: str,
        org_id: str,
        text: str,
        voice_id: str,
        agent_tts_config: dict | None = None,
    ) -> TTSResponse:
        await set_tenant_context(session, org_id)

        state = self._get_or_create_session(vapi_call_id)
        agent_config = agent_tts_config or {}

        primary_override = agent_config.get("tts_provider")
        fallback_override = agent_config.get("fallback_tts_provider")

        if primary_override and primary_override != "auto":
            primary_name = primary_override
        else:
            primary_name = state.active_provider

        if primary_name not in self._providers:
            primary_name = self._settings.TTS_PRIMARY_PROVIDER

        fallback_name = (
            fallback_override
            if fallback_override and fallback_override in self._providers
            else self._settings.TTS_FALLBACK_PROVIDER
        )

        provider = self._providers.get(primary_name)
        if provider is None:
            provider = self._providers.get(fallback_name)
            if provider is None:
                raise TTSAllProvidersFailedError("No TTS providers configured")
            primary_name, fallback_name = fallback_name, primary_name

        if primary_name == fallback_name:
            fallback_name = next(
                (pn for pn in self._providers if pn != primary_name), primary_name
            )

        tts_model = agent_config.get("tts_voice_model") or None
        response = await provider.synthesize(text, voice_id, model=tts_model)

        is_slow = (
            response.error
            or response.latency_ms > self._settings.TTS_LATENCY_THRESHOLD_MS
        )

        if is_slow:
            state.consecutive_slow += 1
            state.recovery_healthy_count = 0
        else:
            if response.latency_ms < self._settings.TTS_RECOVERY_LATENCY_MS:
                state.recovery_healthy_count += 1
            else:
                state.recovery_healthy_count = 0
            state.consecutive_slow = 0

        state.latency_history.append(response.latency_ms)

        req_status = (
            "success"
            if not response.error
            else ("timeout" if response.error_message == "Timeout" else "error")
        )

        await self._record_request(
            session,
            call_id,
            vapi_call_id,
            org_id,
            provider=primary_name,
            voice_id=voice_id,
            text_length=len(text),
            latency_ms=response.latency_ms if not response.error else None,
            status=req_status,
            error_message=response.error_message if response.error else None,
        )

        if not response.error and self._check_fallback_condition(vapi_call_id):
            to_provider = fallback_name
            if to_provider != primary_name:
                self._circuit_breaker.record_fallback(primary_name)
                await self._perform_switch(
                    session,
                    call_id,
                    vapi_call_id,
                    org_id,
                    from_provider=primary_name,
                    to_provider=to_provider,
                    reason="latency_threshold_exceeded",
                    consecutive_slow=state.consecutive_slow,
                    last_latency_ms=response.latency_ms,
                )
                state.active_provider = to_provider
                state.consecutive_slow = 0
                state.recovery_healthy_count = 0
                state.last_switch_at = time.monotonic()

                fallback_provider = self._providers.get(to_provider)
                if fallback_provider:
                    response = await fallback_provider.synthesize(
                        text, voice_id, model=tts_model
                    )
                    fb_status = (
                        "success"
                        if not response.error
                        else (
                            "timeout"
                            if response.error_message == "Timeout"
                            else "error"
                        )
                    )
                    await self._record_request(
                        session,
                        call_id,
                        vapi_call_id,
                        org_id,
                        provider=to_provider,
                        voice_id=voice_id,
                        text_length=len(text),
                        latency_ms=response.latency_ms if not response.error else None,
                        status=fb_status,
                        error_message=response.error_message
                        if response.error
                        else None,
                    )
                    state.latency_history.append(response.latency_ms)

        elif response.error:
            fallback_provider = self._providers.get(fallback_name)
            if fallback_provider:
                self._circuit_breaker.record_fallback(primary_name)
                fb_response = await fallback_provider.synthesize(
                    text, voice_id, model=tts_model
                )
                fb_status = (
                    "success"
                    if not fb_response.error
                    else (
                        "timeout" if fb_response.error_message == "Timeout" else "error"
                    )
                )
                await self._record_request(
                    session,
                    call_id,
                    vapi_call_id,
                    org_id,
                    provider=fallback_name,
                    voice_id=voice_id,
                    text_length=len(text),
                    latency_ms=fb_response.latency_ms
                    if not fb_response.error
                    else None,
                    status=fb_status,
                    error_message=fb_response.error_message
                    if fb_response.error
                    else None,
                )
                state.latency_history.append(fb_response.latency_ms)

                if fb_response.error:
                    self._circuit_breaker.record_fallback(fallback_name)
                    await self._record_all_failed(
                        session, call_id, vapi_call_id, org_id
                    )
                    await self._emit_voice_event(
                        session,
                        call_id,
                        vapi_call_id,
                        org_id,
                        from_provider=primary_name,
                        to_provider=fallback_name,
                        reason="all_providers_failed",
                    )
                    state.active_provider = fallback_name
                    raise TTSAllProvidersFailedError(
                        f"Both providers failed: {primary_name} ({response.error_message}), "
                        f"{fallback_name} ({fb_response.error_message})"
                    )
                else:
                    self._circuit_breaker.record_success(fallback_name)
                    state.active_provider = fallback_name
                    state.consecutive_slow = 0
                    state.recovery_healthy_count = 0
                    state.last_switch_at = time.monotonic()
                    await self._perform_switch(
                        session,
                        call_id,
                        vapi_call_id,
                        org_id,
                        from_provider=primary_name,
                        to_provider=fallback_name,
                        reason="provider_error",
                        consecutive_slow=0,
                        last_latency_ms=response.latency_ms,
                    )
                    response = fb_response
            else:
                self._circuit_breaker.record_fallback(primary_name)
                await self._record_all_failed(session, call_id, vapi_call_id, org_id)
                await self._emit_voice_event(
                    session,
                    call_id,
                    vapi_call_id,
                    org_id,
                    from_provider=primary_name,
                    to_provider="none",
                    reason="all_providers_failed",
                )
                raise TTSAllProvidersFailedError(
                    f"Primary failed and no fallback: {response.error_message}"
                )
        else:
            self._circuit_breaker.record_success(primary_name)
            if (
                self._settings.TTS_AUTO_RECOVERY_ENABLED
                and state.active_provider != self._settings.TTS_PRIMARY_PROVIDER
                and self._check_recovery_condition(vapi_call_id)
            ):
                original_primary = self._settings.TTS_PRIMARY_PROVIDER
                await self._perform_switch(
                    session,
                    call_id,
                    vapi_call_id,
                    org_id,
                    from_provider=state.active_provider,
                    to_provider=original_primary,
                    reason="recovery_healthy",
                    consecutive_slow=0,
                    last_latency_ms=response.latency_ms,
                )
                logger.info(
                    "TTS provider recovered to primary",
                    extra={
                        "code": "TTS_RECOVERY_PROMOTED",
                        "vapi_call_id": vapi_call_id,
                        "to_provider": original_primary,
                    },
                )
                state.active_provider = original_primary
                state.recovery_healthy_count = 0
                state.last_switch_at = time.monotonic()

        return response

    def get_session_provider(self, vapi_call_id: str) -> str:
        state = self._session_state.get(vapi_call_id)
        if state:
            return state.active_provider
        return self._settings.TTS_PRIMARY_PROVIDER

    def get_session_latency_history(self, vapi_call_id: str) -> list[float]:
        state = self._session_state.get(vapi_call_id)
        if state:
            return list(state.latency_history)
        return []

    def reset_session(self, vapi_call_id: str) -> None:
        self._session_state.pop(vapi_call_id, None)

    async def get_providers_health(self) -> dict[str, bool]:
        return {
            name: await provider.health_check()
            for name, provider in self._providers.items()
        }

    def _get_or_create_session(self, vapi_call_id: str) -> SessionTTSState:
        if vapi_call_id not in self._session_state:
            primary = self._settings.TTS_PRIMARY_PROVIDER
            if primary not in self._providers and self._providers:
                primary = next(iter(self._providers))
            if self._circuit_breaker.is_open(primary):
                for alt in self._providers:
                    if alt != primary and not self._circuit_breaker.is_open(alt):
                        primary = alt
                        break
                else:
                    logger.warning(
                        "All TTS providers have open circuit breakers for new session",
                        extra={
                            "code": "TTS_ALL_CIRCUITS_OPEN",
                            "vapi_call_id": vapi_call_id,
                        },
                    )
            self._session_state[vapi_call_id] = SessionTTSState(
                active_provider=primary,
            )
        return self._session_state[vapi_call_id]

    def _check_fallback_condition(self, vapi_call_id: str) -> bool:
        state = self._session_state.get(vapi_call_id)
        if state is None:
            return False
        return state.consecutive_slow >= self._settings.TTS_CONSECUTIVE_SLOW_THRESHOLD

    def _check_recovery_condition(self, vapi_call_id: str) -> bool:
        state = self._session_state.get(vapi_call_id)
        if state is None:
            return False
        if state.recovery_healthy_count < self._settings.TTS_RECOVERY_HEALTHY_COUNT:
            return False
        elapsed_since_switch = time.monotonic() - state.last_switch_at
        if elapsed_since_switch < self._settings.TTS_RECOVERY_COOLDOWN_SEC:
            return False
        return True

    async def _record_request(
        self,
        session: AsyncSession,
        call_id: int,
        vapi_call_id: str,
        org_id: str,
        provider: str,
        voice_id: str,
        text_length: int,
        latency_ms: float | None,
        status: str,
        error_message: str | None,
    ) -> None:
        try:
            await session.execute(
                text(
                    "INSERT INTO tts_requests "
                    "(org_id, call_id, vapi_call_id, provider, voice_id, text_length, "
                    "latency_ms, status, error_message, received_at, created_at, updated_at) "
                    "VALUES (:org_id, :call_id, :vci, :provider, :voice_id, :text_length, "
                    ":latency_ms, :status, :error_message, NOW(), NOW(), NOW())"
                ),
                {
                    "org_id": org_id,
                    "call_id": call_id,
                    "vci": vapi_call_id,
                    "provider": provider,
                    "voice_id": voice_id,
                    "text_length": text_length,
                    "latency_ms": latency_ms,
                    "status": status,
                    "error_message": error_message,
                },
            )
            await session.flush()
        except Exception as exc:
            logger.error(
                "Failed to record TTS request",
                extra={
                    "code": "TTS_REQUEST_RECORD_ERROR",
                    "vapi_call_id": vapi_call_id,
                    "error": str(exc),
                },
            )

    async def _record_all_failed(
        self,
        session: AsyncSession,
        call_id: int,
        vapi_call_id: str,
        org_id: str,
    ) -> None:
        for provider_name in self._providers:
            try:
                await session.execute(
                    text(
                        "INSERT INTO tts_requests "
                        "(org_id, call_id, vapi_call_id, provider, voice_id, text_length, "
                        "latency_ms, status, error_message, received_at, created_at, updated_at) "
                        "VALUES (:org_id, :call_id, :vci, :provider, '', 0, "
                        "NULL, 'all_failed', 'all providers failed', NOW(), NOW(), NOW())"
                    ),
                    {
                        "org_id": org_id,
                        "call_id": call_id,
                        "vci": vapi_call_id,
                        "provider": provider_name,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "Failed to record all_failed row for provider",
                    extra={
                        "code": "TTS_ALL_FAILED_RECORD_ERROR",
                        "vapi_call_id": vapi_call_id,
                        "provider": provider_name,
                        "error": str(exc),
                    },
                )
        try:
            await session.flush()
        except Exception as exc:
            logger.error(
                "Failed to flush all_failed TTS records",
                extra={
                    "code": "TTS_ALL_FAILED_FLUSH_ERROR",
                    "vapi_call_id": vapi_call_id,
                    "error": str(exc),
                },
            )

    async def _perform_switch(
        self,
        session: AsyncSession,
        call_id: int,
        vapi_call_id: str,
        org_id: str,
        from_provider: str,
        to_provider: str,
        reason: str,
        consecutive_slow: int,
        last_latency_ms: float | None,
    ) -> None:
        try:
            await session.execute(
                text(
                    "INSERT INTO tts_provider_switches "
                    "(org_id, call_id, vapi_call_id, from_provider, to_provider, reason, "
                    "consecutive_slow_count, last_latency_ms, switched_at, created_at, updated_at) "
                    "VALUES (:org_id, :call_id, :vci, :from_p, :to_p, :reason, "
                    ":consecutive_slow, :last_latency_ms, NOW(), NOW(), NOW())"
                ),
                {
                    "org_id": org_id,
                    "call_id": call_id,
                    "vci": vapi_call_id,
                    "from_p": from_provider,
                    "to_p": to_provider,
                    "reason": reason,
                    "consecutive_slow": consecutive_slow,
                    "last_latency_ms": last_latency_ms,
                },
            )
            await session.flush()
        except Exception as exc:
            logger.error(
                "Failed to record TTS provider switch",
                extra={
                    "code": "TTS_SWITCH_FAILED",
                    "vapi_call_id": vapi_call_id,
                    "error": str(exc),
                },
            )

        await self._emit_voice_event(
            session,
            call_id,
            vapi_call_id,
            org_id,
            from_provider=from_provider,
            to_provider=to_provider,
            reason=reason,
            consecutive_slow=consecutive_slow,
            last_latency_ms=last_latency_ms,
        )

    async def _emit_voice_event(
        self,
        session: AsyncSession,
        call_id: int,
        vapi_call_id: str,
        org_id: str,
        from_provider: str,
        to_provider: str,
        reason: str,
        consecutive_slow: int = 0,
        last_latency_ms: float | None = None,
    ) -> None:
        event_type = "tts_provider_switch"
        if reason == "all_providers_failed":
            event_type = "tts_all_providers_failed"

        metadata = {
            "from_provider": from_provider,
            "to_provider": to_provider,
            "reason": reason,
            "consecutive_slow": consecutive_slow,
            "last_latency_ms": last_latency_ms,
        }
        try:
            await session.execute(
                text(
                    "INSERT INTO voice_events "
                    "(org_id, call_id, vapi_call_id, event_type, speaker, event_metadata, "
                    "received_at, created_at, updated_at) "
                    "VALUES (:org_id, :call_id, :vci, :event_type, NULL, :metadata, "
                    "NOW(), NOW(), NOW()) "
                    "RETURNING id"
                ),
                {
                    "org_id": org_id,
                    "call_id": call_id,
                    "vci": vapi_call_id,
                    "event_type": event_type,
                    "metadata": json.dumps(metadata),
                },
            )
            await session.flush()
        except Exception as exc:
            logger.error(
                "Failed to emit TTS voice event",
                extra={
                    "code": "TTS_VOICE_EVENT_ERROR",
                    "vapi_call_id": vapi_call_id,
                    "error": str(exc),
                },
            )

    def _cleanup_stale_sessions(self) -> int:
        now = time.monotonic()
        ttl = self._settings.TTS_SESSION_TTL_SEC
        stale_keys = [
            k for k, v in self._session_state.items() if (now - v.created_at) > ttl
        ]
        for k in stale_keys:
            del self._session_state[k]
        return len(stale_keys)

    async def start_cleanup_task(self) -> None:
        if self._cleanup_task is not None:
            return

        async def _run():
            interval = self._settings.TTS_SESSION_TTL_SEC / 2
            while True:
                await asyncio.sleep(interval)
                cleaned = self._cleanup_stale_sessions()
                if cleaned:
                    logger.info(
                        "TTS session cleanup",
                        extra={
                            "code": "TTS_SESSION_CLEANUP",
                            "cleaned_count": cleaned,
                        },
                    )

        self._cleanup_task = asyncio.create_task(_run())

    async def synthesize_for_test(
        self,
        text: str,
        voice_id: str,
        provider: str | None = None,
        speech_speed: float = 1.0,
        stability: float = 0.8,
        temperature: float = 0.7,
    ) -> TTSResponse:
        """Synthesize short audio for preset samples (non-session context).

        Bypasses session state tracking but respects circuit breaker state.
        Used by PresetSampleService to generate preset audio samples.

        Args:
            text: Text to synthesize
            voice_id: Voice ID to use
            provider: Specific provider to use (or None for primary)
            speech_speed: Speech rate multiplier
            stability: Voice stability
            temperature: Voice expressiveness

        Returns:
            TTSResponse with audio_bytes

        Raises:
            TTSAllProvidersFailedError: If provider is not available or synthesis fails
        """
        target_provider = provider or self._get_primary_provider()

        if self._circuit_breaker.is_open(target_provider):
            raise TTSAllProvidersFailedError(
                f"Provider {target_provider} circuit is open"
            )

        tts_impl = self._providers.get(target_provider)
        if not tts_impl:
            raise TTSAllProvidersFailedError(
                f"Provider {target_provider} not found"
            )

        try:
            response = await tts_impl.synthesize(
                text=text,
                voice_id=voice_id,
                model=None,  # Use default model for samples
            )
            self._circuit_breaker.record_success(target_provider)
            return response
        except Exception as e:
            self._circuit_breaker.record_fallback(target_provider)
            raise TTSAllProvidersFailedError(f"TTS synthesis failed: {str(e)}")

    def _get_primary_provider(self) -> str:
        """Get the primary TTS provider from settings."""
        return self._settings.TTS_PRIMARY_PROVIDER

    async def stop_cleanup_task(self) -> None:
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
