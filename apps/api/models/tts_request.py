from datetime import datetime
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field

from .base import TenantModel, utc_now


class TTSRequest(TenantModel, table=True):
    __tablename__ = "tts_requests"  # type: ignore
    __table_args__ = (Index("ix_tts_requests_call_id_provider", "call_id", "provider"),)

    call_id: Optional[int] = Field(
        default=None,
        foreign_key="calls.id",
        index=True,
        sa_column_kwargs={"ondelete": "CASCADE"},
    )
    vapi_call_id: Optional[str] = Field(default=None, max_length=255, index=True)
    provider: str = Field(max_length=30)
    voice_id: str = Field(default="", max_length=100)
    text_length: int = Field(default=0)
    latency_ms: Optional[float] = Field(default=None)
    status: str = Field(max_length=20)
    error_message: Optional[str] = Field(default=None)
    received_at: datetime = Field(default_factory=utc_now)
    vapi_event_timestamp: Optional[float] = Field(default=None)
