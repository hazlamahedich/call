import re

from typing import Optional

from pydantic import BaseModel, field_validator
from pydantic.alias_generators import to_camel

_E164_PATTERN = re.compile(r"^\+?[1-9]\d{1,14}$")


class TriggerCallPayload(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    lead_id: Optional[int] = None
    agent_id: Optional[int] = None
    phone_number: str
    campaign_id: Optional[int] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("phone_number must not be empty")
        if not _E164_PATTERN.match(v.strip()):
            raise ValueError("phone_number must be in E.164 format (e.g. +1234567890)")
        return v


class CallResponse(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    id: int
    vapi_call_id: str
    org_id: str
    lead_id: Optional[int] = None
    agent_id: Optional[int] = None
    campaign_id: Optional[int] = None
    status: str
    phone_number: str
    created_at: Optional[str] = None


class VapiWebhookPayload(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    message: dict
