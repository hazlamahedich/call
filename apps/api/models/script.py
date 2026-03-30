from sqlmodel import Field
from typing import Optional

from .base import TenantModel


class Script(TenantModel, table=True):
    __tablename__ = "scripts"  # type: ignore

    agent_id: Optional[int] = Field(default=None, foreign_key="agents.id")
    name: str = Field(default="Initial Script", max_length=255)
    content: str = Field(default="")
    version: int = Field(default=1)
    script_context: str = Field(default="")
