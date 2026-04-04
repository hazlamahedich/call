"""Unit tests for PresetSampleService.

[2.6-BACKEND-SAMPLES-001] Test sample generation for preset
[2.6-BACKEND-SAMPLES-002] Test Redis caching of samples
[2.6-BACKEND-SAMPLES-003] Test cache invalidation
[2.6-BACKEND-SAMPLES-004] Test provider failure handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from models.voice_preset import VoicePreset
from services.preset_samples import PresetSampleService
from services.tts.orchestrator import TTSAllProvidersFailedError, TTSResponse


@pytest.mark.asyncio
async def test_sample_generation_for_preset(
    db_session: AsyncSession,
    preset_factory,
):
    """[2.6-BACKEND-SAMPLES-001] Generate audio sample for preset."""
    preset = await preset_factory(
        org_id="test_org",
        use_case="sales",
        voice_id="test_voice",
        speech_speed=1.2,
        stability=0.7,
        temperature=0.8,
    )

    # Mock TTS orchestrator
    mock_orchestrator = AsyncMock()
    mock_orchestrator.synthesize_for_test.return_value = TTSResponse(
        audio_bytes=b"fake audio data",
        latency_ms=100,
        provider="test_provider",
        content_type="audio/mpeg",
    )

    # Mock Redis (optional)
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Cache miss

    service = PresetSampleService(redis_client=mock_redis, tts_orchestrator=mock_orchestrator)

    # Generate sample
    audio_bytes = await service.generate_sample_for_preset(
        session=db_session,
        preset=preset,
        org_id="test_org",
    )

    # Verify TTS was called with correct parameters
    mock_orchestrator.synthesize_for_test.assert_called_once_with(
        text="Hi, this is Alex from TechCorp. I'm calling to show you how our platform can increase your sales by 30% in just 30 days.",
        voice_id="test_voice",
        speech_speed=1.2,
        stability=0.7,
        temperature=0.8,
    )

    assert audio_bytes == b"fake audio data"


@pytest.mark.asyncio
async def test_redis_caching_of_samples(
    db_session: AsyncSession,
    preset_factory,
):
    """[2.6-BACKEND-SAMPLES-002] Cached samples are returned without regenerating."""
    preset = await preset_factory(
        org_id="test_org",
        use_case="sales",
        voice_id="test_voice",
        speech_speed=1.0,
        stability=0.8,
        temperature=0.7,
    )

    # Mock Redis with cached data
    mock_redis = AsyncMock()
    mock_redis.get.return_value = b"cached audio data"

    # Mock TTS orchestrator (should not be called)
    mock_orchestrator = AsyncMock()

    service = PresetSampleService(redis_client=mock_redis, tts_orchestrator=mock_orchestrator)

    # Generate sample (should return cached)
    audio_bytes = await service.generate_sample_for_preset(
        session=db_session,
        preset=preset,
        org_id="test_org",
    )

    # Verify TTS was NOT called (cache hit)
    mock_orchestrator.synthesize_for_test.assert_not_called()

    # Verify Redis was checked
    mock_redis.get.assert_called_once()

    assert audio_bytes == b"cached audio data"


@pytest.mark.asyncio
async def test_cache_invalidation_on_config_change(
    db_session: AsyncSession,
    preset_factory,
):
    """[2.6-BACKEND-SAMPLES-003] Cache key includes preset config hash."""
    preset = await preset_factory(
        org_id="test_org",
        voice_id="test_voice",
        speech_speed=1.0,
        stability=0.8,
        temperature=0.7,
    )

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Cache miss
    mock_orchestrator = AsyncMock()
    mock_orchestrator.synthesize_for_test.return_value = TTSResponse(
        audio_bytes=b"audio data",
        latency_ms=100,
        provider="test",
        content_type="audio/mpeg",
    )

    service = PresetSampleService(redis_client=mock_redis, tts_orchestrator=mock_orchestrator)

    # Generate sample with original config
    await service.generate_sample_for_preset(
        session=db_session,
        preset=preset,
        org_id="test_org",
    )

    # Get the cache key that was used
    first_call_key = mock_redis.setex.call_args[0][0]

    # Update preset config
    preset.speech_speed = 1.5
    preset.stability = 0.6
    await db_session.commit()

    # Reset mocks
    mock_redis.get.reset_mock()
    mock_redis.get.return_value = None  # Still cache miss for new key

    # Generate sample again
    await service.generate_sample_for_preset(
        session=db_session,
        preset=preset,
        org_id="test_org",
    )

    # Get the new cache key
    second_call_key = mock_redis.setex.call_args[0][0]

    # Cache keys should be different (config changed)
    assert first_call_key != second_call_key


@pytest.mark.asyncio
async def test_provider_failure_handling(
    db_session: AsyncSession,
    preset_factory,
):
    """[2.6-BACKEND-SAMPLES-004] TTS provider failure raises TTSAllProvidersFailedError."""
    preset = await preset_factory(
        org_id="test_org",
        use_case="sales",
    )

    # Mock TTS to raise error
    mock_orchestrator = AsyncMock()
    mock_orchestrator.synthesize_for_test.side_effect = TTSAllProvidersFailedError(
        "All providers failed"
    )

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    service = PresetSampleService(redis_client=mock_redis, tts_orchestrator=mock_orchestrator)

    # Should raise the error
    with pytest.raises(TTSAllProvidersFailedError) as exc_info:
        await service.generate_sample_for_preset(
            session=db_session,
            preset=preset,
            org_id="test_org",
        )

    assert "All providers failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_redis_none_fallback(
    db_session: AsyncSession,
    preset_factory,
):
    """Test that service works when Redis is None (not configured)."""
    preset = await preset_factory(
        org_id="test_org",
        use_case="sales",
    )

    # Mock TTS orchestrator
    mock_orchestrator = AsyncMock()
    mock_orchestrator.synthesize_for_test.return_value = TTSResponse(
        audio_bytes=b"audio data",
        latency_ms=100,
        provider="test",
        content_type="audio/mpeg",
    )

    # Redis is None
    service = PresetSampleService(redis_client=None, tts_orchestrator=mock_orchestrator)

    # Should still work without Redis
    audio_bytes = await service.generate_sample_for_preset(
        session=db_session,
        preset=preset,
        org_id="test_org",
    )

    assert audio_bytes == b"audio data"

    # TTS should still be called
    mock_orchestrator.synthesize_for_test.assert_called_once()


@pytest.fixture
async def preset_factory(db_session: AsyncSession):
    """Factory for creating test voice presets."""
    created_presets = []

    async def _create(
        org_id: str = "default",
        use_case: str = "sales",
        voice_id: str = "test_voice",
        speech_speed: float = 1.0,
        stability: float = 0.8,
        temperature: float = 0.7,
    ) -> VoicePreset:
        preset = VoicePreset(
            org_id=org_id,
            name=f"Test Preset {use_case}",
            use_case=use_case,
            voice_id=voice_id,
            speech_speed=speech_speed,
            stability=stability,
            temperature=temperature,
            description="Test description",
            is_active=True,
            sort_order=1,
        )
        db_session.add(preset)
        await db_session.commit()
        await db_session.refresh(preset)
        created_presets.append(preset)
        return preset

    yield _create

    # Cleanup
    for preset in created_presets:
        await db_session.delete(preset)
    await db_session.commit()
