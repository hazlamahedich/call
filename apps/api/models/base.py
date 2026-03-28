from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import text


class TenantModel(SQLModel):
    """
    Base class for all tenant-scoped models.

    CRITICAL: org_id is auto-populated from session context on insert.
    The session must have app.current_org_id set via set_tenant_context().
    """

    org_id: str = Field(default=None, index=True, description="Tenant organization ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    soft_delete: bool = Field(default=False)
    id: Optional[int] = Field(default=None, primary_key=True)

    class Config:
        table: bool = False
