"""Request and response schemas for agent management API endpoints."""

from pydantic import BaseModel
from typing import List, Literal, Optional


class CreateAgentRequest(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Literal["admin", "agent", "supervisor"] = "agent"
    preset_id: Optional[int] = None

    class Config:
        from_attributes = True


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[Literal["admin", "agent", "supervisor"]] = None
    status: Optional[Literal["active", "inactive", "suspended"]] = None
    preset_id: Optional[int] = None

    class Config:
        from_attributes = True


class BulkUpdateAgentsRequest(BaseModel):
    agent_ids: List[int]
    preset_id: int

    class Config:
        from_attributes = True


class AgentProfileResponse(BaseModel):
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
    agents: List[AgentProfileResponse]
    count: int
