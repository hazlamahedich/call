import json
from typing import Optional

from pydantic import BaseModel, field_validator, Field
from pydantic.alias_generators import to_camel

VALID_RESOURCE_TYPES = ("call", "sms", "agent")
VALID_ACTIONS = ("call_initiated", "call_completed", "call_failed", "sms_sent")


class UsageRecordPayload(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    resource_type: str
    resource_id: str = Field(max_length=255)
    action: str
    metadata: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            json.loads(v)
        except json.JSONDecodeError:
            raise ValueError("metadata must be a valid JSON string")
        return v

    @field_validator("resource_type")
    @classmethod
    def validate_resource_type(cls, v: str) -> str:
        if v not in VALID_RESOURCE_TYPES:
            raise ValueError(f"resource_type must be one of {VALID_RESOURCE_TYPES}")
        return v

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in VALID_ACTIONS:
            raise ValueError(f"action must be one of {VALID_ACTIONS}")
        return v


class UsageSummaryResponse(BaseModel):
    used: int
    cap: int
    percentage: float
    plan: str
    threshold: str
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
