from datetime import datetime
from typing import Optional

from sqlmodel import Field

from .base import TenantModel, utc_now


class TranscriptEntry(TenantModel, table=True):
    __tablename__ = "transcript_entries"  # type: ignore

    call_id: Optional[int] = Field(default=None, foreign_key="calls.id", index=True)
    vapi_call_id: Optional[str] = Field(default=None, max_length=255, index=True)
    role: str = Field(max_length=30)
    text: str = Field()
    start_time: Optional[float] = Field(default=None)
    end_time: Optional[float] = Field(default=None)
    confidence: Optional[float] = Field(default=None)
    words_json: Optional[str] = Field(default=None)
    received_at: datetime = Field(default_factory=utc_now)
    vapi_event_timestamp: Optional[float] = Field(default=None)
