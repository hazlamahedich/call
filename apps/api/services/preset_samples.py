"""Preset sample generation service with Redis caching.

Generates and caches audio samples for voice presets using the TTS
orchestrator. Samples are cached for 24 hours to reduce API costs
and improve load times.
"""

import hashlib
import logging

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.session import set_tenant_context
from models.voice_preset import VoicePreset
from services.tts.orchestrator import TTSAllProvidersFailedError, TTSOrchestrator

logger = logging.getLogger(__name__)


class PresetSampleService:
    """Service for generating and caching voice preset samples."""

    def __init__(self, redis_client: redis.Redis | None, tts_orchestrator: TTSOrchestrator):
        """Initialize the service.

        Args:
            redis_client: Redis client for caching (can be None)
            tts_orchestrator: TTS orchestrator for synthesis
        """
        self.redis = redis_client
        self.tts = tts_orchestrator
        self.cache_ttl = getattr(settings, "SAMPLE_CACHE_TTL_SECONDS", 86400)  # 24 hours

    async def generate_sample_for_preset(
        self,
        session: AsyncSession,
        preset: VoicePreset,
        org_id: str,
    ) -> bytes:
        """Generate and cache preset audio sample.

        Args:
            session: Database session
            preset: VoicePreset model instance
            org_id: Organization ID for tenant context

        Returns:
            Audio bytes for the preset sample

        Raises:
            TTSAllProvidersFailedError: If TTS synthesis fails
        """
        await set_tenant_context(session, org_id)

        # Check cache first if Redis is available
        if self.redis:
            cache_key = self._generate_cache_key(preset)
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(
                    "Preset sample cache hit",
                    extra={"code": "PRESET_SAMPLE_CACHE_HIT", "preset_id": preset.id},
                )
                return cached

        # Generate new sample
        sample_text = self._get_sample_text(preset.use_case)

        try:
            response = await self.tts.synthesize_for_test(
                text=sample_text,
                voice_id=preset.voice_id,
                speech_speed=preset.speech_speed,
                stability=preset.stability,
                temperature=preset.temperature,
            )

            # Cache the sample if Redis is available
            if self.redis:
                cache_key = self._generate_cache_key(preset)
                await self.redis.setex(
                    cache_key,
                    self.cache_ttl,
                    response.audio_bytes,
                )

            logger.info(
                "Preset sample generated" + (" and cached" if self.redis else " (Redis not available)"),
                extra={
                    "code": "PRESET_SAMPLE_GENERATED",
                    "preset_id": preset.id,
                    "use_case": preset.use_case,
                    "latency_ms": response.latency_ms,
                },
            )

            return response.audio_bytes

        except TTSAllProvidersFailedError:
            logger.error(
                "Failed to generate preset sample",
                extra={
                    "code": "PRESET_SAMPLE_GENERATION_FAILED",
                    "preset_id": preset.id,
                    "use_case": preset.use_case,
                },
            )
            raise

    def _generate_cache_key(self, preset: VoicePreset) -> str:
        """Generate Redis cache key for preset sample.

        The key includes preset configuration hash to ensure cache
        invalidation when preset settings change.

        Args:
            preset: VoicePreset model instance

        Returns:
            Redis cache key
        """
        # Hash preset configuration for cache key
        config_str = f"{preset.voice_id}:{preset.speech_speed}:{preset.stability}:{preset.temperature}"
        config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]

        return f"preset_sample:{preset.id}:{config_hash}"

    def _get_sample_text(self, use_case: str) -> str:
        """Get sample text for preset use case.

        Args:
            use_case: Use case (sales, support, marketing)

        Returns:
            Sample text for TTS synthesis

        Raises:
            ValueError: If use_case is not recognized
        """
        sample_texts = getattr(settings, "PRESET_SAMPLE_TEXTS", {})

        text = sample_texts.get(use_case)
        if not text:
            # Fallback default text
            logger.warning(
                "No sample text found for use case, using default",
                extra={"code": "PRESET_SAMPLE_TEXT_MISSING", "use_case": use_case},
            )
            return "Hello, this is a sample of the voice preset."

        return text
