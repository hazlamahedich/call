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
    preset_id: Optional[int] = Field(
        default=None,
        foreign_key="voice_presets.id",
        description="Selected voice preset ID",
    )
    use_advanced_mode: bool = Field(
        default=False,
        description="Whether user configured custom voice settings",
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
    grounding_config: Optional[dict] = Field(default=None)
    system_prompt_template: Optional[str] = Field(default=None)
    config_version: int = Field(default=1)
    knowledge_base_ids: Optional[dict] = Field(default=None)
