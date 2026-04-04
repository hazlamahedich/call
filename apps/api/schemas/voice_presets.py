"""Request and response schemas for voice preset API endpoints."""

from pydantic import BaseModel
from typing import List, Optional


class VoicePresetSchema(BaseModel):
    """Voice preset model for API responses."""

    id: int
    name: str
    use_case: str
    voice_id: str
    speech_speed: float
    stability: float
    temperature: float
    description: str
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


class VoicePresetResponse(BaseModel):
    """Response schema for GET /voice-presets endpoint."""

    presets: List[VoicePresetSchema]
    count: int


class VoicePresetSelectResponse(BaseModel):
    """Response schema for POST /voice-presets/{preset_id}/select endpoint."""

    preset_id: int
    message: str


class PresetSampleErrorResponse(BaseModel):
    """Error response schema for preset sample endpoint."""

    code: str
    message: str
    retryable: bool = False


class AgentConfigResponse(BaseModel):
    """Response schema for GET /agent-config/current endpoint."""

    preset_id: Optional[int] = None
    speech_speed: float
    stability: float
    temperature: float
    use_advanced_mode: bool
