"""Preset sample generation service with explicit caching strategy.

Generates and caches audio samples for voice presets using the TTS
orchestrator. Samples are cached for 24 hours to reduce API costs
and improve load times.
"""

import hashlib
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.session import set_tenant_context
from models.voice_preset import VoicePreset
from services.cache_strategy import CacheStrategy
from services.tts.orchestrator import TTSAllProvidersFailedError, TTSOrchestrator

logger = logging.getLogger(__name__)


class PresetSampleService:
    """Service for generating and caching voice preset samples."""

    def __init__(self, cache: CacheStrategy, tts_orchestrator: TTSOrchestrator):
        """Initialize the service.

        Args:
            cache: Cache strategy implementation (Redis, NoOp, etc.)
            tts_orchestrator: TTS orchestrator for synthesis
        """
        self.cache = cache
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

        # Check cache first using explicit cache strategy
        cache_key = self._generate_cache_key(preset)
        cached = await self.cache.get(cache_key)
        if cached:
            # Handle potential cache corruption
            try:
                if isinstance(cached, str):
                    cached = cached.encode('utf-8')
                logger.debug(
                    "Preset sample cache hit",
                    extra={"code": "PRESET_SAMPLE_CACHE_HIT", "preset_id": preset.id},
                )
                return cached
            except Exception as e:
                logger.warning(
                    f"Cache corruption detected for key {cache_key}: {e}",
                    extra={"code": "PRESET_SAMPLE_CACHE_CORRUPTION", "preset_id": preset.id},
                )
                # Delete corrupted entry and regenerate
                await self.cache.delete(cache_key)

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

            # Cache the sample using explicit cache strategy
            cache_key = self._generate_cache_key(preset)
            cached = await self.cache.set(cache_key, response.audio_bytes, self.cache_ttl)
            if cached:
                logger.info(
                    "Preset sample generated and cached",
                    extra={
                        "code": "PRESET_SAMPLE_GENERATED_CACHED",
                        "preset_id": preset.id,
                        "use_case": preset.use_case,
                        "latency_ms": response.latency_ms,
                    },
                )
            else:
                logger.info(
                    "Preset sample generated (cache unavailable)",
                    extra={
                        "code": "PRESET_SAMPLE_GENERATED_NO_CACHE",
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
        # Sanitize inputs to prevent key injection
        safe_voice_id = preset.voice_id.replace(":", "_").replace(" ", "_")

        # Use full SHA-256 hash instead of truncated MD5 for better collision resistance
        config_str = f"{safe_voice_id}:{preset.speech_speed}:{preset.stability}:{preset.temperature}"
        config_hash = hashlib.sha256(config_str.encode()).hexdigest()

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

        # Validate that sample_texts is configured
        if not sample_texts:
            logger.error(
                "PRESET_SAMPLE_TEXTS not configured in settings",
                extra={"code": "PRESET_SAMPLE_TEXTS_NOT_CONFIGURED"},
            )
            return "Hello, this is a sample of the voice preset."

        text = sample_texts.get(use_case)
        if not text:
            logger.warning(
                f"No sample text for use_case={use_case}. Available: {list(sample_texts.keys())}",
                extra={"code": "PRESET_SAMPLE_TEXT_MISSING", "use_case": use_case},
            )
            return "Hello, this is a sample of the voice preset."

        # Validate text is non-empty string
        if not isinstance(text, str) or len(text.strip()) == 0:
            logger.error(
                f"Invalid sample text for use_case={use_case}",
                extra={"code": "PRESET_SAMPLE_TEXT_INVALID", "use_case": use_case},
            )
            return "Hello, this is a sample of the voice preset."

        return text
