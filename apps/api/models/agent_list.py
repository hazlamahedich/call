"""Agent management model for multi-agent organizations.

Allows admins to manage multiple agents with different voice presets.
"""

from sqlmodel import Field, SQLModel
from typing import Optional

from .base import TenantModel


class AgentProfile(TenantModel, table=True):
    """Extended agent profile for multi-agent management.

    Extends the base Agent model with additional fields for team management,
    allowing admins to assign different voice presets to different agents.
    """

    __tablename__ = "agent_profiles"  # type: ignore

    # Agent identification
    agent_id: int = Field(
        primary_key=True,
        description="Link to base Agent table",
    )
    name: str = Field(max_length=255, description="Agent display name")
    email: Optional[str] = Field(default=None, max_length=255, description="Agent email")
    phone: Optional[str] = Field(default=None, max_length=50, description="Agent phone number")

    # Role and status
    role: str = Field(
        default="agent",
        max_length=50,
        description="Role: admin, agent, manager",
    )
    status: str = Field(
        default="active",
        max_length=50,
        description="Status: active, inactive, suspended",
    )

    # Configuration
    preset_id: Optional[int] = Field(
        default=None,
        foreign_key="voice_presets.id",
        description="Assigned voice preset ID",
    )
    use_advanced_mode: bool = Field(
        default=False,
        description="Whether using custom voice settings",
    )
    speech_speed: Optional[float] = Field(
        default=1.0,
        description="Speech rate multiplier (0.5-2.0)",
    )
    stability: Optional[float] = Field(
        default=0.8,
        description="Voice stability (0.0-1.0)",
    )
    temperature: Optional[float] = Field(
        default=0.7,
        description="Voice expressiveness (0.0-1.0)",
    )

    # Metadata
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Agent description or notes",
    )
    avatar_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Profile picture URL",
    )
