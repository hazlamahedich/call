"""Voice preset API endpoints with tenant isolation.

All endpoints enforce tenant isolation by filtering queries based on
org_id from the JWT token. Users can only access and select presets
that belong to their organization.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.session import get_db
from middleware.auth_middleware import auth_middleware
from models.agent import Agent
from models.voice_preset import VoicePreset
from schemas.voice_presets import (
    AgentConfigResponse,
    PresetSampleErrorResponse,
    VoicePresetResponse,
    VoicePresetSchema,
    VoicePresetSelectResponse,
)
from services.preset_samples import PresetSampleService
from services.tts.orchestrator import TTSAllProvidersFailedError, TTSOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/voice-presets", response_model=VoicePresetResponse)
async def get_presets(
    use_case: str | None = None,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    """Get all voice presets for the tenant.

    Args:
        use_case: Optional filter by use case (sales, support, marketing)
        session: Database session
        token: JWT token with org_id

    Returns:
        VoicePresetResponse with list of presets
    """
    org_id = token.org_id  # CRITICAL: from JWT, never request body

    query = select(VoicePreset).where(
        VoicePreset.org_id == org_id,
        VoicePreset.is_active == True,
    )

    if use_case:
        query = query.where(VoicePreset.use_case == use_case)

    query = query.order_by(VoicePreset.sort_order)

    result = await session.execute(query)
    presets = result.scalars().all()

    return VoicePresetResponse(
        presets=[VoicePresetSchema.model_validate(p) for p in presets],
        count=len(presets),
    )


@router.get("/agent-config/current", response_model=AgentConfigResponse)
async def get_current_agent_config(
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    """Get current agent voice configuration.

    Returns the currently selected preset and voice settings for
    the tenant's agent.

    Args:
        session: Database session
        token: JWT token with org_id

    Returns:
        AgentConfigResponse with current config
    """
    org_id = token.org_id

    agent = await session.execute(
        select(Agent).where(Agent.org_id == org_id).limit(1)
    )
    agent = agent.scalar_one_or_none()

    if not agent:
        # Return default config if no agent exists
        return AgentConfigResponse(
            preset_id=None,
            speech_speed=1.0,
            stability=0.8,
            temperature=0.7,
            use_advanced_mode=False,
        )

    return AgentConfigResponse(
        preset_id=agent.preset_id,
        speech_speed=agent.speech_speed or 1.0,
        stability=agent.stability or 0.8,
        temperature=agent.temperature or 0.7,
        use_advanced_mode=agent.use_advanced_mode or False,
    )


@router.post("/agent-config/advanced", response_model=VoicePresetSelectResponse)
async def save_advanced_config(
    config: dict,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    """Save custom advanced voice configuration.

    Saves manually configured voice settings and clears any preset selection.

    Args:
        config: Dict with speech_speed, stability, temperature
        session: Database session
        token: JWT token with org_id

    Returns:
        VoicePresetSelectResponse with confirmation

    Raises:
        HTTPException: If config values are invalid
    """
    org_id = token.org_id

    # Validate config values
    speech_speed = config.get("speech_speed", 1.0)
    stability = config.get("stability", 0.8)
    temperature = config.get("temperature", 0.7)

    if not (0.5 <= speech_speed <= 2.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_SPEED",
                "message": "Speech speed must be between 0.5 and 2.0",
            },
        )

    if not (0.0 <= stability <= 1.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_STABILITY",
                "message": "Stability must be between 0.0 and 1.0",
            },
        )

    if not (0.0 <= temperature <= 1.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_TEMPERATURE",
                "message": "Temperature must be between 0.0 and 1.0",
            },
        )

    # Get or create tenant's agent
    agent = await session.execute(
        select(Agent).where(Agent.org_id == org_id).limit(1)
    )
    agent = agent.scalar_one_or_none()

    if agent:
        # Update agent with custom config
        agent.speech_speed = speech_speed
        agent.stability = stability
        agent.temperature = temperature
        agent.use_advanced_mode = True
        agent.preset_id = None  # Clear preset when using advanced mode
        await session.commit()
    else:
        # Create new agent with custom config
        agent = Agent(
            org_id=org_id,
            speech_speed=speech_speed,
            stability=stability,
            temperature=temperature,
            use_advanced_mode=True,
            preset_id=None,
        )
        session.add(agent)
        await session.commit()

    logger.info(
        "Advanced voice config saved",
        extra={
            "code": "ADVANCED_CONFIG_SAVED",
            "org_id": org_id,
            "speech_speed": speech_speed,
            "stability": stability,
            "temperature": temperature,
        },
    )

    return VoicePresetSelectResponse(
        preset_id=None,  # No preset when using advanced mode
        message="Custom voice configuration saved successfully",
    )


@router.post("/voice-presets/{preset_id}/select", response_model=VoicePresetSelectResponse)
async def select_preset(
    preset_id: int,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    """Select a voice preset for the tenant's agent.

    Copies the preset's TTS settings to the agent configuration.

    Args:
        preset_id: ID of preset to select
        session: Database session
        token: JWT token with org_id

    Returns:
        VoicePresetSelectResponse with confirmation

    Raises:
        HTTPException: If preset not found or access denied
    """
    org_id = token.org_id

    # Verify preset belongs to tenant
    preset = await session.get(VoicePreset, preset_id)
    if not preset or preset.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PRESET_NOT_FOUND",
                "message": "Voice preset not found or access denied",
            },
        )

    # Get or create tenant's agent
    agent = await session.execute(
        select(Agent).where(Agent.org_id == org_id).limit(1)
    )
    agent = agent.scalar_one_or_none()

    if agent:
        # Update agent with preset settings
        agent.preset_id = preset_id
        agent.speech_speed = preset.speech_speed
        agent.stability = preset.stability
        agent.temperature = preset.temperature
        agent.use_advanced_mode = False
        await session.commit()
    else:
        # Create new agent with preset settings
        agent = Agent(
            org_id=org_id,
            preset_id=preset_id,
            speech_speed=preset.speech_speed,
            stability=preset.stability,
            temperature=preset.temperature,
            use_advanced_mode=False,
        )
        session.add(agent)
        await session.commit()

    logger.info(
        "Voice preset selected",
        extra={
            "code": "PRESET_SELECTED",
            "preset_id": preset_id,
            "preset_name": preset.name,
            "org_id": org_id,
        },
    )

    return VoicePresetSelectResponse(
        preset_id=preset_id,
        message=f"Voice preset '{preset.name}' saved successfully",
    )


@router.get(
    "/voice-presets/{preset_id}/sample",
    responses={
        200: {"content": {"audio/mpeg": {}}},
        503: {"model": PresetSampleErrorResponse},
    },
)
async def get_preset_sample(
    preset_id: int,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    """Get audio sample for a voice preset.

    Returns cached or newly generated audio sample for the preset.
    Samples are cached for 24 hours.

    Args:
        preset_id: ID of preset
        session: Database session
        token: JWT token with org_id

    Returns:
        Audio bytes with Content-Type: audio/mpeg

    Raises:
        HTTPException: If preset not found or TTS fails
    """
    org_id = token.org_id

    # Verify preset belongs to tenant
    preset = await session.get(VoicePreset, preset_id)
    if not preset or preset.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PRESET_NOT_FOUND",
                "message": "Voice preset not found or access denied",
            },
        )

    try:
        # Import here to avoid circular dependency
        from main import get_preset_sample_service, get_tts_orchestrator

        preset_service = get_preset_sample_service()
        if not preset_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "REDIS_NOT_CONFIGURED",
                    "message": "Preset sample service not available. Please configure Redis.",
                    "retryable": False,
                },
            )

        audio_bytes = await preset_service.generate_sample_for_preset(
            session=session,
            preset=preset,
            org_id=org_id,
        )

        from fastapi.responses import Response

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'attachment; filename="preset_{preset_id}_sample.mp3"',
                "Cache-Control": "public, max-age=86400",  # 24 hours
            },
        )

    except TTSAllProvidersFailedError as e:
        logger.error(
            "Failed to generate preset sample",
            extra={
                "code": "PRESET_SAMPLE_ERROR",
                "preset_id": preset_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "SAMPLE_GENERATION_FAILED",
                "message": "Voice samples temporarily unavailable. Please try again later.",
                "retryable": True,
            },
        )
