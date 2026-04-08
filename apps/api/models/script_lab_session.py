from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field

from models.base import TenantModel


class ScriptLabSession(TenantModel, table=True):
    __tablename__ = "script_lab_sessions"  # type: ignore

    agent_id: int = Field(foreign_key="agents.id")
    script_id: int = Field(foreign_key="scripts.id")
    lead_id: Optional[int] = Field(default=None, foreign_key="leads.id")
    scenario_overlay: Optional[dict] = Field(default=None)
    expires_at: datetime
    status: str = Field(default="active")
    turn_count: int = Field(default=0)
