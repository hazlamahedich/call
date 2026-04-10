from datetime import datetime
from sqlmodel import Field, Index
from typing import Optional

from .base import TenantModel


class DncCheckLog(TenantModel, table=True):
    __tablename__ = "dnc_check_logs"  # type: ignore

    phone_number: str = Field(max_length=20, index=True)
    check_type: str = Field(max_length=20)
    source: str = Field(max_length=30)
    result: str = Field(max_length=20)
    lead_id: Optional[int] = Field(default=None, nullable=True, foreign_key="leads.id")
    campaign_id: Optional[int] = Field(default=None, nullable=True)
    call_id: Optional[int] = Field(default=None, nullable=True, foreign_key="calls.id")
    response_time_ms: int = Field(default=0)
    raw_response: Optional[str] = Field(default=None, nullable=True)
    checked_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(__import__("datetime").timezone.utc)
    )

    __table_args__ = (
        Index("ix_dnc_check_logs_org_phone", "org_id", "phone_number"),
        Index("ix_dnc_check_logs_call_id", "call_id"),
    )
