from pydantic import AliasGenerator
from pydantic.alias_generators import to_camel
from sqlmodel import Field

from models.base import TenantModel


class UsageLog(TenantModel, table=True):
    __tablename__ = "usage_logs"

    resource_type: str = Field(default="call", max_length=50)
    resource_id: str = Field(default="", max_length=255)
    action: str = Field(default="call_initiated", max_length=50)
    metadata_json: str = Field(default="{}", max_length=2000)

    class Config:
        alias_generator = AliasGenerator(to_camel)
