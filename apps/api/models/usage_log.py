import sqlalchemy
from pydantic import AliasGenerator
from pydantic.alias_generators import to_camel
from sqlmodel import Field, Column
from typing import Optional

from models.base import TenantModel


class UsageLog(TenantModel, table=True):
    __tablename__ = "usage_logs"

    resource_type: str = Field(default="call", max_length=50)
    resource_id: str = Field(default="", max_length=255)
    action: str = Field(default="call_initiated", max_length=50)
    metadata_json: Optional[dict] = Field(
        default=None,
        sa_column=Column(
            "metadata_json",
            sqlalchemy.JSON,
            nullable=True,
            server_default="'{}'::jsonb",
        ),
    )

    class Config:
        alias_generator = AliasGenerator(to_camel)
