from datetime import datetime
from sqlmodel import Field
from typing import Optional

from .base import TenantModel


class Call(TenantModel, table=True):
    __tablename__ = "calls"  # type: ignore

    vapi_call_id: str = Field(default="", max_length=255, index=True)
    lead_id: Optional[int] = Field(default=None, nullable=True, foreign_key="leads.id")
    agent_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="agents.id"
    )
    campaign_id: Optional[int] = Field(default=None, nullable=True)
    status: str = Field(default="pending", max_length=50)
    duration: Optional[int] = Field(default=None, nullable=True)
    recording_url: Optional[str] = Field(default=None, max_length=500, nullable=True)
    phone_number: str = Field(default="", max_length=20, index=True)
    transcript: Optional[str] = Field(default=None, nullable=True)
    ended_at: Optional[datetime] = Field(default=None, nullable=True)
