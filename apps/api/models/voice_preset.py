from sqlmodel import Field, SQLModel
from typing import Optional

from .base import TenantModel


class VoicePreset(TenantModel, table=True):
    """Voice presets for different use cases.

    Each preset contains optimized TTS settings for a specific use case
    (sales, support, marketing). Presets are tenant-isolated and can be
    selected by users to configure their agent's voice.
    """

    __tablename__ = "voice_presets"  # type: ignore

    name: str = Field(max_length=255, description="Human-readable preset name")
    use_case: str = Field(
        max_length=50,
        description="Use case: sales, support, or marketing",
    )
    voice_id: str = Field(max_length=100, description="TTS provider voice ID")
    speech_speed: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Speech rate multiplier (0.5-2.0)",
    )
    stability: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Voice stability (0.0-1.0)",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Voice expressiveness (0.0-1.0)",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Preset description for UI",
    )
    is_active: bool = Field(
        default=True,
        description="Whether preset is available for selection",
    )
    sort_order: int = Field(
        default=0,
        description="Display order within use case",
    )
