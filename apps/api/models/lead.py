from sqlmodel import Field
from typing import Optional

from .base import TenantModel


class Lead(TenantModel, table=True):
    """Sample tenant-scoped model for RLS testing."""

    __tablename__ = "leads"  # type: ignore
    name: str = Field(description="Lead name")
    email: str = Field(description="Lead email")
    phone: Optional[str] = Field(default=None, description="Lead phone")
    status: str = Field(default="new", description="Lead status")
