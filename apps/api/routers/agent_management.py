"""Agent management API endpoints for multi-agent organizations.

Allows admins to create, update, and manage multiple agents with different voice presets.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth_middleware import auth_middleware
from models.agent import Agent
from models.voice_preset import VoicePreset
from schemas.agent_management import (
    AgentProfileResponse,
    AgentProfileListResponse,
    CreateAgentRequest,
    UpdateAgentRequest,
    BulkUpdateAgentsRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/agents", response_model=AgentProfileListResponse)
async def list_agents(
    status_filter: str | None = None,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    """List all agents for the organization.

    Args:
        status_filter: Optional filter by status (active, inactive, suspended)
        session: Database session
        token: JWT token with org_id

    Returns:
        AgentProfileListResponse with list of agents
    """
    org_id = token.org_id

    query = select(Agent).where(Agent.org_id == org_id)

    if status_filter:
        query = query.where(Agent.status == status_filter)

    query = query.order_by(Agent.created_at.desc())

    result = await session.execute(query)
    agents = result.scalars().all()

    # Enrich with preset names
    agent_profiles = []
    for agent in agents:
        preset_name = None
        if agent.preset_id:
            preset_result = await session.execute(
                select(VoicePreset.name).where(
                    and_(
                        VoicePreset.id == agent.preset_id,
                        VoicePreset.org_id == org_id,
                    )
                )
            )
            preset_name = preset_result.scalar_one_or_none()

        agent_profiles.append({
            "agent_id": agent.id,
            "name": agent.name or f"Agent {agent.id}",
            "email": agent.email,
            "phone": agent.phone,
            "role": agent.role,
            "status": agent.status,
            "preset_id": agent.preset_id,
            "preset_name": preset_name,
            "use_advanced_mode": agent.use_advanced_mode or False,
            "speech_speed": agent.speech_speed or 1.0,
            "stability": agent.stability or 0.8,
            "temperature": agent.temperature or 0.7,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
        })

    return {
        "agents": agent_profiles,
        "count": len(agent_profiles),
    }


@router.post("/agents", response_model=AgentProfileResponse)
async def create_agent(
    agent_data: CreateAgentRequest,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    """Create a new agent for the organization.

    Args:
        agent_data: Agent creation request
        session: Database session
        token: JWT token with org_id

    Returns:
        AgentProfileResponse with created agent details

    Raises:
        HTTPException: If preset not found or validation fails
    """
    org_id = token.org_id

    # Verify preset belongs to org if provided
    if agent_data.preset_id:
        preset = await session.execute(
            select(VoicePreset).where(
                and_(
                    VoicePreset.id == agent_data.preset_id,
                    VoicePreset.org_id == org_id,
                )
            )
        )
        preset = preset.scalar_one_or_none()
        if not preset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "PRESET_NOT_FOUND",
                    "message": "Voice preset not found in your organization",
                },
            )

    # Create agent
    agent = Agent(
        org_id=org_id,
        name=agent_data.name,
        email=agent_data.email,
        phone=agent_data.phone,
        role=agent_data.role or "agent",
        status="active",
        preset_id=agent_data.preset_id,
        use_advanced_mode=False,
        speech_speed=1.0,
        stability=0.8,
        temperature=0.7,
    )

    session.add(agent)
    await session.commit()
    await session.refresh(agent)

    logger.info(
        "Agent created",
        extra={
            "code": "AGENT_CREATED",
            "org_id": org_id,
            "agent_id": agent.id,
            "name": agent.name,
        },
    )

    preset_name = None
    if agent.preset_id:
        preset_result = await session.execute(
            select(VoicePreset.name).where(VoicePreset.id == agent.preset_id)
        )
        preset_name = preset_result.scalar_one_or_none()

    return {
        "agent_id": agent.id,
        "name": agent.name,
        "email": agent.email,
        "phone": agent.phone,
        "role": agent.role,
        "status": agent.status,
        "preset_id": agent.preset_id,
        "preset_name": preset_name,
        "use_advanced_mode": agent.use_advanced_mode or False,
        "speech_speed": agent.speech_speed or 1.0,
        "stability": agent.stability or 0.8,
        "temperature": agent.temperature or 0.7,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    }


@router.put("/agents/{agent_id}", response_model=AgentProfileResponse)
async def update_agent(
    agent_id: int,
    agent_data: UpdateAgentRequest,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    """Update agent configuration.

    Args:
        agent_id: Agent ID to update
        agent_data: Update request
        session: Database session
        token: JWT token with org_id

    Returns:
        AgentProfileResponse with updated agent details

    Raises:
        HTTPException: If agent not found or preset invalid
    """
    org_id = token.org_id

    # Get agent
    result = await session.execute(
        select(Agent).where(
            and_(
                Agent.id == agent_id,
                Agent.org_id == org_id,
            )
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "AGENT_NOT_FOUND",
                "message": "Agent not found or access denied",
            },
        )

    # Verify preset if provided
    if agent_data.preset_id is not None:
        preset = await session.execute(
            select(VoicePreset).where(
                and_(
                    VoicePreset.id == agent_data.preset_id,
                    VoicePreset.org_id == org_id,
                )
            )
        )
        preset = preset.scalar_one_or_none()
        if not preset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "PRESET_NOT_FOUND",
                    "message": "Voice preset not found in your organization",
                },
            )
        agent.preset_id = agent_data.preset_id

    # Update fields
    if agent_data.name is not None:
        agent.name = agent_data.name
    if agent_data.email is not None:
        agent.email = agent_data.email
    if agent_data.phone is not None:
        agent.phone = agent_data.phone
    if agent_data.role is not None:
        agent.role = agent_data.role
    if agent_data.status is not None:
        agent.status = agent_data.status

    await session.commit()
    await session.refresh(agent)

    logger.info(
        "Agent updated",
        extra={
            "code": "AGENT_UPDATED",
            "org_id": org_id,
            "agent_id": agent.id,
        },
    )

    preset_name = None
    if agent.preset_id:
        preset_result = await session.execute(
            select(VoicePreset.name).where(VoicePreset.id == agent.preset_id)
        )
        preset_name = preset_result.scalar_one_or_none()

    return {
        "agent_id": agent.id,
        "name": agent.name,
        "email": agent.email,
        "phone": agent.phone,
        "role": agent.role,
        "status": agent.status,
        "preset_id": agent.preset_id,
        "preset_name": preset_name,
        "use_advanced_mode": agent.use_advanced_mode or False,
        "speech_speed": agent.speech_speed or 1.0,
        "stability": agent.stability or 0.8,
        "temperature": agent.temperature or 0.7,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    }


@router.post("/agents/bulk-update")
async def bulk_update_agents(
    bulk_data: BulkUpdateAgentsRequest,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    """Bulk update agents with the same preset.

    Allows admin to quickly assign the same voice preset to multiple agents.

    Args:
        bulk_data: Bulk update request with agent_ids and preset_id
        session: Database session
        token: JWT token with org_id

    Returns:
        Confirmation message with count of updated agents

    Raises:
        HTTPException: If preset not found
    """
    org_id = token.org_id

    # Verify preset
    preset = await session.execute(
        select(VoicePreset).where(
            and_(
                VoicePreset.id == bulk_data.preset_id,
                VoicePreset.org_id == org_id,
            )
        )
    )
    preset = preset.scalar_one_or_none()

    if not preset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "PRESET_NOT_FOUND",
                "message": "Voice preset not found in your organization",
            },
        )

    # Update all specified agents
    updated_count = 0
    for agent_id in bulk_data.agent_ids:
        result = await session.execute(
            select(Agent).where(
                and_(
                    Agent.id == agent_id,
                    Agent.org_id == org_id,
                )
            )
        )
        agent = result.scalar_one_or_none()

        if agent:
            agent.preset_id = bulk_data.preset_id
            agent.use_advanced_mode = False
            updated_count += 1

    await session.commit()

    logger.info(
        "Bulk agent update",
        extra={
            "code": "BULK_AGENT_UPDATE",
            "org_id": org_id,
            "preset_id": bulk_data.preset_id,
            "updated_count": updated_count,
        },
    )

    return {
        "message": f"Updated {updated_count} agents with preset '{preset.name}'",
        "updated_count": updated_count,
        "preset_id": bulk_data.preset_id,
        "preset_name": preset.name,
    }


@router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: int,
    session: AsyncSession = Depends(get_db),
    token=Depends(auth_middleware),
):
    """Delete an agent.

    Args:
        agent_id: Agent ID to delete
        session: Database session
        token: JWT token with org_id

    Returns:
        Confirmation message

    Raises:
        HTTPException: If agent not found
    """
    org_id = token.org_id

    # Get agent
    result = await session.execute(
        select(Agent).where(
            and_(
                Agent.id == agent_id,
                Agent.org_id == org_id,
            )
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "AGENT_NOT_FOUND",
                "message": "Agent not found or access denied",
            },
        )

    # Soft delete by setting status
    agent.status = "deleted"
    await session.commit()

    logger.info(
        "Agent deleted",
        extra={
            "code": "AGENT_DELETED",
            "org_id": org_id,
            "agent_id": agent.id,
        },
    )

    return {
        "message": "Agent deleted successfully",
        "agent_id": agent_id,
    }
