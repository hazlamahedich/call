from pydantic import BaseModel, field_validator
from pydantic.alias_generators import to_camel
from typing import Optional

ALLOWED_SAFETY_LEVELS = {"strict", "moderate", "relaxed"}
MIN_SCRIPT_CONTEXT_LENGTH = 20


class OnboardingPayload(BaseModel):
    business_goal: str
    script_context: str
    voice_id: str
    integration_type: Optional[str] = None
    safety_level: str

    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    @field_validator("business_goal")
    @classmethod
    def validate_business_goal(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("business_goal must not be empty")
        return v

    @field_validator("voice_id")
    @classmethod
    def validate_voice_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("voice_id must not be empty")
        return v

    @field_validator("safety_level")
    @classmethod
    def validate_safety_level(cls, v: str) -> str:
        if v not in ALLOWED_SAFETY_LEVELS:
            raise ValueError(f"safety_level must be one of {ALLOWED_SAFETY_LEVELS}")
        return v

    @field_validator("script_context")
    @classmethod
    def validate_script_context(cls, v: str) -> str:
        if len(v.strip()) < MIN_SCRIPT_CONTEXT_LENGTH:
            raise ValueError(
                f"script_context must be at least {MIN_SCRIPT_CONTEXT_LENGTH} characters"
            )
        return v
