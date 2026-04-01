from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field

from .base import TenantModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VoiceEvent(TenantModel, table=True):
    __tablename__ = "voice_events"  # type: ignore

    call_id: Optional[int] = Field(default=None, foreign_key="calls.id", index=True)
    vapi_call_id: Optional[str] = Field(default=None, max_length=255, index=True)
    event_type: str = Field(max_length=50)
    speaker: Optional[str] = Field(default=None, max_length=20)
    event_metadata: Optional[str] = Field(default=None)
    received_at: datetime = Field(default_factory=_utc_now)
    vapi_event_timestamp: Optional[float] = Field(default=None)
