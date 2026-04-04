"""Request and response schemas for agent management API endpoints."""

from pydantic import BaseModel
from typing import List, Optional


class CreateAgentRequest(BaseModel):
    """Request schema for creating a new agent."""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = "agent"
    preset_id: Optional[int] = None

    class Config:
        from_attributes = True


class UpdateAgentRequest(BaseModel):
    """Request schema for updating an agent."""

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    preset_id: Optional[int] = None

    class Config:
        from_attributes = True


class BulkUpdateAgentsRequest(BaseModel):
    """Request schema for bulk updating agents."""

    agent_ids: List[int]
    preset_id: int

    class Config:
        from_attributes = True


class AgentProfileResponse(BaseModel):
    """Response schema for a single agent profile."""

    agent_id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    status: str
    preset_id: Optional[int] = None
    preset_name: Optional[str] = None
    use_advanced_mode: bool
    speech_speed: float
    stability: float
    temperature: float
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class AgentProfileListResponse(BaseModel):
    """Response schema for listing agents."""

    agents: List[AgentProfileResponse]
    count: int
