from typing import Optional

from pydantic import BaseModel, field_validator
from pydantic.alias_generators import to_camel


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
