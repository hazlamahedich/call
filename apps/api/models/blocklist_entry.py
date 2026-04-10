from datetime import datetime
from sqlmodel import Field, UniqueConstraint
from typing import Optional

from .base import TenantModel


class BlocklistEntry(TenantModel, table=True):
    __tablename__ = "blocklist_entries"  # type: ignore

    phone_number: str = Field(max_length=20, index=True)
    source: str = Field(max_length=30)
    reason: Optional[str] = Field(default=None, nullable=True)
    lead_id: Optional[int] = Field(default=None, nullable=True, foreign_key="leads.id")
    auto_blocked_at: Optional[datetime] = Field(default=None, nullable=True)
    expires_at: Optional[datetime] = Field(default=None, nullable=True)
    soft_delete: bool = Field(default=False)

    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "phone_number",
            name="uq_blocklist_org_phone",
        ),
    )
