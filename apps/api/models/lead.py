from datetime import datetime
from typing import Optional

from sqlmodel import Field

from .base import TenantModel


class Lead(TenantModel, table=True):
    """Sample tenant-scoped model for RLS testing."""

    __tablename__ = "leads"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(description="Lead name")
    email: str = Field(description="Lead email")
    phone: Optional[str] = Field(default=None, description="Lead phone")
    status: str = Field(default="new", description="Lead status")
