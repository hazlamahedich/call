from datetime import datetime
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field

from .base import TenantModel, utc_now


class TTSProviderSwitch(TenantModel, table=True):
    __tablename__ = "tts_provider_switches"  # type: ignore
    __table_args__ = (
        Index("ix_tts_provider_switches_call_id_switched_at", "call_id", "switched_at"),
    )

    call_id: Optional[int] = Field(
        default=None,
        foreign_key="calls.id",
        index=True,
        sa_column_kwargs={"ondelete": "CASCADE"},
    )
    vapi_call_id: Optional[str] = Field(default=None, max_length=255, index=True)
    from_provider: str = Field(max_length=30)
    to_provider: str = Field(max_length=30)
    reason: str = Field(max_length=100)
    consecutive_slow_count: int = Field(default=0)
    last_latency_ms: Optional[float] = Field(default=None)
    switched_at: datetime = Field(default_factory=utc_now)
