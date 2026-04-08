from typing import Optional

from sqlmodel import Field

from models.base import TenantModel


class ScriptLabTurn(TenantModel, table=True):
    __tablename__ = "script_lab_turns"  # type: ignore

    session_id: int = Field(foreign_key="script_lab_sessions.id")
    turn_number: int
    role: str
    content: str
    source_attributions: Optional[list] = Field(default=None)
    grounding_confidence: Optional[float] = Field(default=None)
    low_confidence_warning: bool = Field(default=False)
