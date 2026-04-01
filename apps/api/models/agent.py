from sqlmodel import Field
from typing import Optional

from .base import TenantModel


class Agent(TenantModel, table=True):
    __tablename__ = "agents"  # type: ignore

    name: str = Field(default="My First Agent", max_length=255)
    voice_id: str = Field(default="", max_length=100)
    business_goal: str = Field(default="", max_length=255)
    safety_level: str = Field(default="strict", max_length=50)
    integration_type: Optional[str] = Field(default=None, max_length=100)
    onboarding_complete: bool = Field(default=False)
    tts_provider: str = Field(default="auto", max_length=30)
    tts_voice_model: str = Field(default="", max_length=100)
    fallback_tts_provider: Optional[str] = Field(default=None, max_length=30)
