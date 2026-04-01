from datetime import datetime, timezone
from typing import Literal, Optional

from sqlmodel import Field, SQLModel
from pydantic import AliasGenerator


from pydantic.alias_generators import to_camel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


TTSProviderName = Literal["elevenlabs", "cartesia"]
TTSRequestStatus = Literal["success", "timeout", "error", "all_failed"]
TTSSwitchReason = Literal[
    "latency_threshold_exceeded",
    "provider_error",
    "recovery_healthy",
    "all_providers_failed",
]


class TenantModel(SQLModel):
    """
    Base class for all tenant-scoped models.

    CRITICAL: org_id is auto-populated from session context on insert.
    The session must have app.current_org_id set via set_tenant_context().
    """

    org_id: Optional[str] = Field(
        default=None, index=True, description="Tenant organization ID"
    )
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    soft_delete: bool = Field(default=False)
    id: Optional[int] = Field(default=None, primary_key=True)

    class Config:
        table: bool = False
        alias_generator = AliasGenerator(to_camel)
